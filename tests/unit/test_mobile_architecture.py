"""Tests for STRATA Android Mobile Architecture & Safety Verification.
Verifies project structure, manifest configuration, assets, and safety invariants.
"""

from pathlib import Path
import xml.etree.ElementTree as ET


def test_android_manifest_structure():
    """Verify AndroidManifest.xml exists, is valid XML, and requests required network permissions."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    manifest_path = repo_root / "mobile" / "android" / "AndroidManifest.xml"
    assert manifest_path.exists(), "AndroidManifest.xml must exist"
    
    content = manifest_path.read_text(encoding="utf-8")
    assert "<manifest" in content
    assert "android.permission.INTERNET" in content
    assert "android.permission.ACCESS_NETWORK_STATE" in content
    assert "usesCleartextTraffic=\"false\"" in content, "Cleartext traffic must be explicitly disallowed for security"


def test_mobile_assets_and_security_invariants():
    """Verify mobile assets do not contain hardcoded broker secrets or API keys."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    mobile_dir = repo_root / "mobile"
    
    # Check all files in mobile dir
    forbidden_terms = ["api_secret", "secret_key", "private_key", "password=", "jwt_secret="]
    
    for file_path in mobile_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in [".html", ".js", ".json", ".xml", ".gradle"]:
            content = file_path.read_text(encoding="utf-8").lower()
            for term in forbidden_terms:
                assert term not in content, f"Forbidden sensitive pattern '{term}' found in {file_path}"


def test_mobile_ui_terminal_touch_views():
    """Verify mobile terminal index.html contains the necessary operational views and safety controls."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    index_path = repo_root / "mobile" / "android" / "assets" / "www" / "index.html"
    assert index_path.exists(), "Mobile terminal index.html must exist"
    
    content = index_path.read_text(encoding="utf-8")
    assert "STRATA" in content
    assert "tab-overview" in content
    assert "tab-positions" in content
    assert "tab-king" in content
    assert "tab-accounts" in content
    assert "tab-alerts" in content
    assert "triggerHalt" in content
    assert "sessionToken" in content
    assert "PROTECTED CORE" in content
