"""Tests for Crypto Platform Android Mobile Architecture & Safety Verification.
Verifies project structure, manifest configuration, assets, native wrapper, and safety invariants.
"""

from pathlib import Path
import xml.etree.ElementTree as ET


def test_android_manifest_structure():
    """Verify AndroidManifest.xml exists, is valid XML, requests required permissions, and uses Crypto Platform branding."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    manifest_path = repo_root / "mobile" / "android" / "AndroidManifest.xml"
    assert manifest_path.exists(), "AndroidManifest.xml must exist"
    
    content = manifest_path.read_text(encoding="utf-8")
    assert "<manifest" in content
    assert "package=\"io.cryptoplatform.app\"" in content
    assert "android:label=\"Crypto Platform\"" in content
    assert "android.permission.INTERNET" in content
    assert "android.permission.ACCESS_NETWORK_STATE" in content
    assert "android.permission.VIBRATE" in content
    assert "usesCleartextTraffic=\"false\"" in content, "Cleartext traffic must be explicitly disallowed for security"

    # XML validation
    root = ET.fromstring(content)
    assert root.tag == "manifest"


def test_mobile_assets_and_security_invariants():
    """Verify mobile assets do not contain hardcoded broker secrets or API keys."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    mobile_dir = repo_root / "mobile"
    
    forbidden_terms = ["api_secret", "secret_key", "private_key", "password=", "jwt_secret="]
    
    for file_path in mobile_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in [".html", ".js", ".json", ".xml", ".gradle", ".java"]:
            content = file_path.read_text(encoding="utf-8").lower()
            for term in forbidden_terms:
                assert term not in content, f"Forbidden sensitive pattern '{term}' found in {file_path}"


def test_mobile_ui_terminal_touch_views():
    """Verify mobile terminal index.html contains all 9 required functional screens, safety controls, and correct terminology."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    index_path = repo_root / "mobile" / "android" / "assets" / "www" / "index.html"
    assert index_path.exists(), "Mobile terminal index.html must exist"
    
    content = index_path.read_text(encoding="utf-8")
    
    # 1. New Product Identity
    assert "Crypto Platform" in content
    assert "STRATA" not in content, "Legacy STRATA marketing branding must be removed from user-facing mobile client"
    assert "Shadow Monarch" not in content, "Legacy anime/cyberpunk branding must be removed"
    
    # 2. Required 9+ Functional Screens
    required_screens = [
        "screen-home",
        "screen-markets",
        "screen-market-detail",
        "screen-strategies",
        "screen-research",
        "screen-backtest",
        "screen-forward",
        "screen-trading",
        "screen-risk",
        "screen-performance",
        "screen-monitoring",
        "screen-account"
    ]
    for screen in required_screens:
        assert screen in content, f"Required screen '{screen}' missing from mobile terminal"

    # 3. Seven-Timeframe Model
    for tf in ["1M", "1W", "1D", "4H", "1H", "15M", "3M"]:
        assert tf in content, f"Timeframe '{tf}' missing from 7-timeframe matrix in mobile client"

    # 4. Invariants & Capital Safety
    assert "$0.00" in content, "Real capital authorized must display $0.00 locked"
    assert "LOCKED" in content
    assert "handleEmergencyStop" in content, "Emergency stop handler must be present"
    assert "btn-emergency-stop" in content, "Emergency stop button must be present"
    assert "Target Floor" in content or "target" in content.lower()
    assert "Portfolio Heat" in content
    assert "Single-Trade Risk" in content


def test_android_native_java_wrapper():
    """Verify Android native wrapper classes exist with appropriate security and JavascriptBridge."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    src_dir = repo_root / "mobile" / "android" / "app" / "src" / "main" / "java" / "io" / "cryptoplatform" / "app"
    
    main_activity = src_dir / "MainActivity.java"
    bridge = src_dir / "WebAppInterface.java"
    
    assert main_activity.exists(), "MainActivity.java must exist"
    assert bridge.exists(), "WebAppInterface.java must exist"
    
    activity_code = main_activity.read_text(encoding="utf-8")
    assert "AndroidBridge" in activity_code
    assert "setAllowFileAccess(false)" in activity_code
    
    bridge_code = bridge.read_text(encoding="utf-8")
    assert "emergencyHalt" in bridge_code
    assert "isLiveTradingLocked" in bridge_code
