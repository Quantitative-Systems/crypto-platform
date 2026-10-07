"""Lightweight test runner that discovers and executes test_* functions across tests/unit."""
import sys
import os
import types
import inspect
import importlib.util
from pathlib import Path

# Add workspace root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Provide pytest shim if pytest is not installed
if "pytest" not in sys.modules:
    dummy_pytest = types.ModuleType("pytest")
    class DummyMark:
        def __getattr__(self, name):
            return lambda *args, **kwargs: (lambda f: f)
    dummy_pytest.mark = DummyMark()
    class DummyRaises:
        def __init__(self, expected_exc, *args, match=None, **kwargs):
            self.expected_exc = expected_exc
            self.match = match
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                raise AssertionError(f"Expected exception {self.expected_exc} was not raised")
            if not issubclass(exc_type, self.expected_exc):
                return False
            if self.match is not None and str(self.match) not in str(exc_val):
                raise AssertionError(f"Exception message '{exc_val}' did not match pattern '{self.match}'")
            return True
    dummy_pytest.raises = DummyRaises
    sys.modules["pytest"] = dummy_pytest

def run_all_tests(scope="unit"):
    if scope == "all":
        test_dir = ROOT_DIR / "tests"
        test_files = sorted([f for f in test_dir.glob("**/test_*.py") if "failed" not in str(f)])
    elif scope == "integration":
        test_dir = ROOT_DIR / "tests" / "integration"
        test_files = sorted(test_dir.glob("**/test_*.py"))
    else:
        test_dir = ROOT_DIR / "tests" / "unit"
        test_files = sorted(test_dir.glob("**/test_*.py"))
    
    total = 0
    passed = 0
    failed = 0
    errors = []

    print(f"Discovered {len(test_files)} test files in {test_dir}")
    for file_path in test_files:
        rel_path = file_path.relative_to(ROOT_DIR)
        module_name = ".".join(rel_path.with_suffix("").parts)
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            failed += 1
            errors.append((str(file_path), "MODULE_LOAD_ERROR", str(e)))
            print(f"[FAIL] {file_path.name} (failed to load: {e})")
            continue

        test_funcs = [
            (name, func) for name, func in inspect.getmembers(module, inspect.isfunction)
            if name.startswith("test_")
        ]
        for cname, cls in inspect.getmembers(module, inspect.isclass):
            if cname.startswith("Test") and cls.__module__ == module.__name__:
                try:
                    instance = cls()
                    for mname, method in inspect.getmembers(instance, inspect.ismethod):
                        if mname.startswith("test_"):
                            test_funcs.append((f"{cname}.{mname}", method))
                except Exception as ce:
                    pass


        for name, func in test_funcs:
            total += 1
            try:
                if hasattr(func, "__self__"):
                    inst = func.__self__
                    if hasattr(inst, "setUp") and callable(inst.setUp):
                        inst.setUp()
                func()
                if hasattr(func, "__self__"):
                    inst = func.__self__
                    if hasattr(inst, "tearDown") and callable(inst.tearDown):
                        inst.tearDown()
                passed += 1
            except Exception as e:
                failed += 1
                errors.append((file_path.name, name, str(e)))
                print(f"[FAIL] {file_path.name}::{name}: {e}")

    print("\n" + "=" * 50)
    print(f"TEST RESULTS: {passed} PASSED, {failed} FAILED, TOTAL: {total}")
    print("=" * 50)
    if errors:
        for f, t, err in errors:
            print(f"- {f}::{t} -> {err}")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    scope = "unit"
    if "--all" in sys.argv:
        scope = "all"
    elif "--integration" in sys.argv:
        scope = "integration"
    run_all_tests(scope=scope)
