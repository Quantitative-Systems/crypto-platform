"""
Unit Test Suite: Asset Universe Registry (Directive EABG-001).
Validates:
- 10-asset canonical universe initialization
- Objective quantitative eligibility hurdles
- Separation of Research Universe from Trading Universe (Asset Universe != Trading Universe)
- Zero live capital production gating
- Canonical JSON export integrity
"""

import pytest
from platform_core.asset_universe_registry import (
    AssetUniverseRegistry,
    AssetMetadata,
    AssetCategory,
    AssetGovernanceStatus,
    SurvivorshipStatus,
    UniverseEligibilityHurdles,
)


@pytest.fixture
def registry():
    return AssetUniverseRegistry()


def test_canonical_10_universe_count_and_assets(registry):
    all_assets = registry.list_all_assets()
    assert len(all_assets) == 10

    symbols = {a.symbol for a in all_assets}
    expected = {
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
        "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "LINK/USDT", "LTC/USDT",
    }
    assert symbols == expected


def test_verified_baseline_vs_research_candidates(registry):
    btc = registry.get_asset("BTC/USDT")
    eth = registry.get_asset("ETH/USDT")
    sol = registry.get_asset("SOL/USDT")

    assert btc.governance_status == AssetGovernanceStatus.CERTIFIED_BENCHMARK
    assert eth.governance_status == AssetGovernanceStatus.CERTIFIED_BENCHMARK
    assert sol.governance_status == AssetGovernanceStatus.CERTIFIED_BENCHMARK
    assert btc.data_quality_certified is True

    # New 7 assets must be research candidates only
    doge = registry.get_asset("DOGE/USDT")
    bnb = registry.get_asset("BNB/USDT")
    link = registry.get_asset("LINK/USDT")

    assert doge.governance_status == AssetGovernanceStatus.RESEARCH_CANDIDATE
    assert bnb.governance_status == AssetGovernanceStatus.RESEARCH_CANDIDATE
    assert link.governance_status == AssetGovernanceStatus.RESEARCH_CANDIDATE
    assert doge.production_eligibility is False


def test_asset_universe_not_equal_to_trading_universe(registry):
    """
    Directive EABG-001: Asset Universe != Trading Universe.
    All 10 assets are eligible for research; zero are eligible for live trading.
    """
    research_assets = registry.list_research_universe()
    trading_assets = registry.list_trading_universe()

    assert len(research_assets) == 10
    assert len(trading_assets) == 0  # Fail-closed zero live capital invariant


def test_objective_eligibility_evaluation(registry):
    # Standard compliant asset
    btc = registry.get_asset("BTC/USDT")
    is_eligible, reasons = registry.evaluate_eligibility(btc)
    assert is_eligible is True
    assert len(reasons) == 0

    # Failing asset: low volume and high spread
    illiquid_coin = AssetMetadata(
        symbol="SHITCOIN/USDT",
        base_asset="SHITCOIN",
        quote_asset="USDT",
        category=AssetCategory.MEME_SPECULATION,
        economic_role="Failing test asset",
        market_cap_rank=350,
        median_daily_volume_usd=100_000.0,  # Below $50M
        historical_depth_days=60,           # Below 730d
        primary_venues=["Binance"],         # Below 2 venues
        spot_available=True,
        perp_available=False,               # No perp
        options_available=False,
        min_order_qty=1.0,
        min_notional_usd=5.0,
        tick_size=0.01,
        step_size=1.0,
        typical_spread_bps=85.0,            # Above 12 bps
        listing_date_utc="2024-01-01T00:00:00Z",
    )

    is_eligible, reasons = registry.evaluate_eligibility(illiquid_coin)
    assert is_eligible is False
    assert len(reasons) >= 4


def test_registry_export_json(registry):
    payload = registry.export_registry_json()
    assert payload["total_assets_registered"] == 10
    assert payload["research_universe_count"] == 10
    assert payload["trading_universe_count"] == 0
    assert payload["capital_allocation_rule"] == "$0.00_FAIL_CLOSED"
    assert "BTC/USDT" in payload["assets"]
