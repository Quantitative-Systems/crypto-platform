"""Unit tests for PlatformSettings and environment configuration."""
import os
import pytest

from crypto_platform.config.settings import PlatformSettings


def test_platform_settings_defaults():
    settings = PlatformSettings()
    assert settings.environment == "PAPER"
    assert settings.tenant_id == "tenant_default"
    assert settings.live_capital_usd == 0.0
    assert settings.max_position_concentration == 0.35
    settings.validate()


def test_platform_settings_live_capital_lock():
    settings = PlatformSettings(live_capital_usd=500.0)
    with pytest.raises(RuntimeError) as exc_info:
        settings.validate()
    assert "FATAL SECURITY VIOLATION: Live capital is configured" in str(exc_info.value)
    assert "locked at $0.00" in str(exc_info.value)


def test_platform_settings_live_mode_lock():
    settings = PlatformSettings(environment="LIVE")
    with pytest.raises(RuntimeError) as exc_info:
        settings.validate()
    assert "Operating mode LIVE is strictly disabled by platform governance" in str(exc_info.value)


def test_platform_settings_invalid_env():
    settings = PlatformSettings(environment="TESTING_FORBIDDEN")
    with pytest.raises(ValueError) as exc_info:
        settings.validate()
    assert "Must be PAPER, DEMO, or LIVE" in str(exc_info.value)


def test_platform_settings_load_from_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "PLATFORM_ENV=DEMO\n"
        "PLATFORM_TENANT_ID=t_custom\n"
        "INITIAL_EQUITY=75000.0\n"
        "BINANCE_TESTNET=true\n"
        "MAX_POSITION_CONCENTRATION=0.25\n"
    )
    # Ensure LIVE_CAPITAL_USD is clean
    monkeypatch.delenv("LIVE_CAPITAL_USD", raising=False)
    monkeypatch.delenv("PLATFORM_ENV", raising=False)

    settings = PlatformSettings.load_from_env(str(env_file))
    assert settings.environment == "DEMO"
    assert settings.tenant_id == "t_custom"
    assert settings.initial_equity == 75000.0
    assert settings.binance_testnet is True
    assert settings.max_position_concentration == 0.25
    assert settings.live_capital_usd == 0.0
