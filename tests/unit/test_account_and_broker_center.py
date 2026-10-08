"""Unit tests for Account Center, Suitability Engine, and Broker Center."""
import pytest
from accounts.account_manager import (
    AccountConfig,
    AccountEnvironment,
    AccountManager,
    BrokerVenue,
)
from accounts.suitability_engine import (
    AccountSuitabilityEngine,
    TradingStyle,
)
from broker.broker_center import BrokerCenter


def test_account_manager_multi_account_and_tenant_filtering():
    mgr = AccountManager()

    # Default system accounts
    accounts = mgr.list_accounts()
    assert len(accounts) >= 3

    # Register tenant-specific custom account
    custom_acc = AccountConfig(
        account_id="ACC_TENANT_BYBIT_01",
        name="Bybit Swing Account",
        venue=BrokerVenue.BYBIT,
        environment=AccountEnvironment.PAPER,
        initial_equity_usd=25000.0,
        tenant_id="tenant_abc",
    )
    mgr.register_account(custom_acc)

    # Tenant ABC view shows their account + system default accounts
    abc_accounts = mgr.list_accounts(tenant_id="tenant_abc")
    ids = [a["account_id"] for a in abc_accounts]
    assert "ACC_TENANT_BYBIT_01" in ids
    assert "ACC_PAPER_PRIMARY" in ids

    # Tenant XYZ view DOES NOT show Tenant ABC's account
    xyz_accounts = mgr.list_accounts(tenant_id="tenant_xyz")
    xyz_ids = [a["account_id"] for a in xyz_accounts]
    assert "ACC_TENANT_BYBIT_01" not in xyz_ids
    assert "ACC_PAPER_PRIMARY" in xyz_ids


def test_account_suitability_engine_verdict():
    # 1. Valid Swing setup with $5,000 equity
    verdict = AccountSuitabilityEngine.evaluate_suitability(
        account_equity_usd=5000.0,
        available_margin_usd=4000.0,
        style=TradingStyle.SWING,
        user_max_risk_pct=0.0075,  # 0.75%
    )
    assert verdict.is_suitable is True
    assert verdict.trading_style == TradingStyle.SWING
    assert "STRATA_KING_ENGINE" in verdict.eligible_strategies
    assert verdict.recommended_risk_pct == 0.0075
    assert verdict.max_exposure_usd == 150.0  # 3% of $5,000

    # 2. Insufficient equity for Scalping
    bad_verdict = AccountSuitabilityEngine.evaluate_suitability(
        account_equity_usd=300.0,
        available_margin_usd=300.0,
        style=TradingStyle.SCALPING,  # Requires min $1,000
    )
    assert bad_verdict.is_suitable is False
    assert any("below minimum for SCALPING" in r for r in bad_verdict.rejection_reasons)

    # 3. User attempts > 1.0% risk -> capped at 1.0% frozen limit
    capped_verdict = AccountSuitabilityEngine.evaluate_suitability(
        account_equity_usd=10000.0,
        available_margin_usd=8000.0,
        style=TradingStyle.AUTONOMOUS,
        user_max_risk_pct=0.03,  # Attempting 3%
    )
    assert capped_verdict.recommended_risk_pct == 0.01  # Hard-capped at 1.0%!
    assert any("capped at 1.0%" in c.lower() for c in capped_verdict.constraints)


def test_broker_center_venue_discovery_and_capabilities():
    center = BrokerCenter()
    venues = center.list_venues()
    assert len(venues) == 3

    venue_names = [v.venue for v in venues]
    assert "BINANCE" in venue_names
    assert "BYBIT" in venue_names
    assert "METATRADER_5" in venue_names

    # Check Binance capabilities
    binance = next(v for v in venues if v.venue == "BINANCE")
    assert binance.is_connected is True
    assert binance.capabilities.supports_limit_orders is True
    assert binance.capabilities.supports_testnet is True
