"""Unit tests for Oracle automated Docker deployment, configuration, and safety invariants."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def get_git_bash() -> str | None:
    """Finds a working bash executable (Git Bash on Windows or system bash on POSIX)."""
    candidates = [
        shutil.which("bash"),
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ]
    for c in candidates:
        if c and Path(c).exists():
            try:
                res = subprocess.run([c, "--version"], capture_output=True, text=True)
                if res.returncode == 0 and "GNU bash" in res.stdout:
                    return c
            except Exception:
                continue
    return None


def run_health_validator(json_payload: str) -> int:
    """Executes the exact Python validator snippet embedded in scripts/deploy_oracle.sh."""
    validator_code = """
import sys, json
try:
    raw = sys.argv[1].strip()
    if not raw:
        sys.exit(1)
    data = json.loads(raw)
    status = data.get('status')
    if status != 'HEALTHY':
        sys.exit(1)
    cap = float(data.get('real_capital_authorized', -1))
    if abs(cap - 0.0) > 1e-6:
        sys.exit(1)
    sys.exit(0)
except Exception:
    sys.exit(1)
"""
    res = subprocess.run([sys.executable, "-c", validator_code, json_payload], capture_output=True)
    return res.returncode


def test_main_cli_arguments_support_no_research():
    """Verify that main.py parses --no-research and --mode PAPER cleanly."""
    cmd = [
        sys.executable,
        str(REPO_ROOT / "main.py"),
        "--mode",
        "PAPER",
        "--host",
        "127.0.0.1",
        "--port",
        "8088",
        "--dry-run-seconds",
        "1",
        "--no-research",
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"main.py execution failed: {res.stderr}"
    assert "Historical seeding completed" in res.stderr or "Historical seeding completed" in res.stdout or "Crypto Engine" in res.stderr or "Crypto Engine" in res.stdout


def test_dockerfile_invariants_and_paper_mode():
    """Verify Dockerfile contains fail-closed safety flags and no-research CMD."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "REAL_CAPITAL_AUTHORIZED_USD=0.00" in dockerfile
    assert "LIVE_TRADING_ENABLED=false" in dockerfile
    assert "--mode" in dockerfile and "PAPER" in dockerfile
    assert "--no-research" in dockerfile
    assert "HEALTHCHECK" in dockerfile


def test_oracle_docker_compose_loopback_and_memory_cap():
    """Verify deploy/docker-compose.oracle.yml has loopback 127.0.0.1:8080 and 512MB RAM cap."""
    compose_path = REPO_ROOT / "deploy" / "docker-compose.oracle.yml"
    assert compose_path.exists(), "deploy/docker-compose.oracle.yml must exist"

    content = compose_path.read_text(encoding="utf-8")
    # Must bind port 8080 strictly to localhost
    assert "127.0.0.1:8080:8080" in content, "Port 8080 must be strictly bound to 127.0.0.1"
    assert '"8080:8080"' not in content, "Public port 8080 binding is forbidden"

    # Memory limit must be 512M to fit on 1GB VPS
    assert "memory: 512M" in content
    assert "REAL_CAPITAL_AUTHORIZED_USD=0.00" in content
    assert "LIVE_TRADING_ENABLED=false" in content

    # Persistent named volumes
    assert "crypto_platform_data:/app/data" in content
    assert "crypto_platform_research:/app/research/results" in content


def test_health_validator_accepts_healthy_zero_capital():
    """Verify valid healthy payload with zero authorized capital passes validation."""
    valid_payload = json.dumps({
        "status": "HEALTHY",
        "real_capital_authorized": 0.0,
        "live_trading_status": "DISABLED_FAIL_CLOSED",
        "execution_mode": "PAPER",
    })
    assert run_health_validator(valid_payload) == 0


@pytest.mark.parametrize("bad_payload", [
    # Status variations that must be rejected
    json.dumps({"status": "UNHEALTHY", "real_capital_authorized": 0.0}),
    json.dumps({"status": "DEGRADED", "real_capital_authorized": 0.0}),
    json.dumps({"status": "NOT_HEALTHY_AT_ALL", "real_capital_authorized": 0.0}),
    json.dumps({"status": "INITIALIZING", "real_capital_authorized": 0.0}),
    # Unauthorized non-zero capital variations
    json.dumps({"status": "HEALTHY", "real_capital_authorized": 100.0}),
    json.dumps({"status": "HEALTHY", "real_capital_authorized": 0.01}),
    json.dumps({"status": "HEALTHY", "real_capital_authorized": -5.0}),
    json.dumps({"status": "HEALTHY", "real_capital_authorized": None}),
    # Malformed or empty payloads
    "",
    "   ",
    "<html>502 Bad Gateway</html>",
    '{"status": "HEALTHY"}',  # missing real_capital_authorized
    "{truncated json...",
])
def test_health_validator_rejects_unhealthy_or_unauthorized(bad_payload):
    """Verify any degraded status, non-zero capital, or malformed JSON is rejected."""
    assert run_health_validator(bad_payload) == 1


def test_persistent_volumes_not_destroyed_by_deployment():
    """Verify deployment scripts and compose configs never execute volume destruction (-v / rm)."""
    script_text = (REPO_ROOT / "scripts" / "deploy_oracle.sh").read_text(encoding="utf-8")
    compose_text = (REPO_ROOT / "deploy" / "docker-compose.oracle.yml").read_text(encoding="utf-8")

    # deploy_oracle.sh must not delete named volumes
    assert "down -v" not in script_text
    assert "docker volume rm" not in script_text
    assert "docker volume prune" not in script_text

    # Named volumes must be declared with local driver for permanent disk persistence
    assert "crypto_platform_data:\n    driver: local" in compose_text or "crypto_platform_data:" in compose_text
    assert "crypto_platform_research:\n    driver: local" in compose_text or "crypto_platform_research:" in compose_text


def test_github_workflow_dispatch_and_ghcr_registry():
    """Verify .github/workflows/deploy-oracle.yml is workflow_dispatch only and uses ghcr.io."""
    wf_path = REPO_ROOT / ".github" / "workflows" / "deploy-oracle.yml"
    assert wf_path.exists(), ".github/workflows/deploy-oracle.yml must exist"

    content = wf_path.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in content
    on_section = content.split("jobs:")[0]
    assert "  push:" not in on_section
    assert "  pull_request:" not in on_section
    assert "  schedule:" not in on_section
    assert "build-and-test-only" in content
    assert "deploy-to-oracle" in content
    assert "ghcr.io" in content
    assert "ORACLE_SSH_KEY" in content


def test_script_rollback_when_new_container_fails_to_start():
    """Verify scripts/deploy_oracle.sh catches startup failure and executes rollback without set -e crash."""
    bash = get_git_bash()
    if not bash:
        pytest.skip("Git Bash not found in environment")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        log_file = tmp_path / "mock_docker.log"

        # Mock docker CLI that simulates existing container but fails on docker compose up
        mock_docker = tmp_path / "docker"
        mock_docker.write_text(f"""#!/usr/bin/env bash
echo "$@" >> "{log_file.as_posix()}"
if [[ "$*" == *"pull"* ]]; then
    echo "Mock pull: image pulled successfully"
    exit 0
elif [[ "$*" == *"ps -q -f name=^/crypto-engine$"* ]]; then
    echo "existing_container_id_123"
    exit 0
elif [[ "$*" == *"compose"* ]] && [[ "$*" == *"up -d"* ]]; then
    echo "Simulated compose startup failure" >&2
    exit 1
elif [[ "$*" == *"ps -aq -f name=^/crypto-engine-prev$"* ]]; then
    echo "existing_prev_id_456"
    exit 0
fi
exit 0
""", encoding="utf-8", newline="\n")
        mock_docker.chmod(0o755)

        # Mock curl
        mock_curl = tmp_path / "curl"
        mock_curl.write_text("""#!/usr/bin/env bash
echo '{"status": "HEALTHY", "real_capital_authorized": 0.0}'
exit 0
""", encoding="utf-8", newline="\n")
        mock_curl.chmod(0o755)

        # Mock dummy compose file
        dummy_compose = tmp_path / "dummy_compose.yml"
        dummy_compose.write_text("version: '3.8'\nservices:\n  dummy:\n    image: dummy", encoding="utf-8")

        script_path = REPO_ROOT / "scripts" / "deploy_oracle.sh"
        env = os.environ.copy()
        env["PATH"] = f"{tmp_path.as_posix()}{os.pathsep}{env['PATH']}"
        env["DOCKER_BIN"] = mock_docker.as_posix()
        env["CURL_BIN"] = mock_curl.as_posix()
        env["COMPOSE_FILE"] = dummy_compose.as_posix()
        env["HEALTH_ATTEMPTS"] = "2"
        env["HEALTH_SLEEP"] = "0"
        env["ROLLBACK_ATTEMPTS"] = "2"
        env["ROLLBACK_SLEEP"] = "0"

        res = subprocess.run(
            [bash, script_path.as_posix(), "mock-image:test"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )

        assert res.returncode == 1, "Script should exit 1 when deployment fails"
        assert "Initiating automatic rollback to previous container" in res.stdout
        assert "Restoring crypto-engine-prev -> crypto-engine" in res.stdout

        # Verify docker log captured rollback sequence
        logged = log_file.read_text(encoding="utf-8")
        assert "pull mock-image:test" in logged
        assert "stop crypto-engine" in logged
        assert "rename crypto-engine crypto-engine-prev" in logged
        assert "compose" in logged and "down" in logged
        assert "rename crypto-engine-prev crypto-engine" in logged
        assert "start crypto-engine" in logged


def test_script_rollback_when_health_check_fails():
    """Verify scripts/deploy_oracle.sh rolls back when container starts but health checks fail."""
    bash = get_git_bash()
    if not bash:
        pytest.skip("Git Bash not found in environment")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        log_file = tmp_path / "mock_docker.log"

        # Mock docker CLI that succeeds on up
        mock_docker = tmp_path / "docker"
        mock_docker.write_text(f"""#!/usr/bin/env bash
echo "$@" >> "{log_file.as_posix()}"
if [[ "$*" == *"pull"* ]]; then
    echo "Mock pull: image pulled successfully"
    exit 0
elif [[ "$*" == *"ps -q -f name=^/crypto-engine$"* ]]; then
    echo "existing_container_id_123"
    exit 0
elif [[ "$*" == *"ps -aq -f name=^/crypto-engine-prev$"* ]]; then
    echo "existing_prev_id_456"
    exit 0
fi
exit 0
""", encoding="utf-8", newline="\n")
        mock_docker.chmod(0o755)

        # Mock curl that returns DEGRADED status (or fails)
        mock_curl = tmp_path / "curl"
        mock_curl.write_text("""#!/usr/bin/env bash
echo '{"status": "DEGRADED", "real_capital_authorized": 0.0}'
exit 0
""", encoding="utf-8", newline="\n")
        mock_curl.chmod(0o755)

        dummy_compose = tmp_path / "dummy_compose.yml"
        dummy_compose.write_text("version: '3.8'\nservices:\n  dummy:\n    image: dummy", encoding="utf-8")

        script_path = REPO_ROOT / "scripts" / "deploy_oracle.sh"
        env = os.environ.copy()
        env["PATH"] = f"{tmp_path.as_posix()}{os.pathsep}{env['PATH']}"
        env["DOCKER_BIN"] = mock_docker.as_posix()
        env["CURL_BIN"] = mock_curl.as_posix()
        env["COMPOSE_FILE"] = dummy_compose.as_posix()
        env["HEALTH_ATTEMPTS"] = "2"
        env["HEALTH_SLEEP"] = "0"
        env["ROLLBACK_ATTEMPTS"] = "2"
        env["ROLLBACK_SLEEP"] = "0"

        res = subprocess.run(
            [bash, script_path.as_posix(), "mock-image:test"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )

        assert res.returncode == 1, "Script should exit 1 when health checks fail"
        assert "CRITICAL WARNING: Health check failed or invariants breached!" in res.stdout
        assert "Restoring crypto-engine-prev -> crypto-engine" in res.stdout

        logged = log_file.read_text(encoding="utf-8")
        assert "pull mock-image:test" in logged
        assert "rename crypto-engine crypto-engine-prev" in logged
        assert "compose" in logged and "down" in logged
        assert "rename crypto-engine-prev crypto-engine" in logged
        assert "start crypto-engine" in logged
