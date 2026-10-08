"""Unit tests for Crypto Universe, Strategy Domains, Lifecycle, and Strategy Lab."""
import pytest
from market_data.universe.crypto_universe import (
    CryptoUniverseManager,
    NonCryptoAssetError,
)
from strategy.lab.strategy_lab_engine import StrategyLabEngine
from strategy.lab.strategy_specification import StrategyDomain
from strategy.lifecycle.strategy_lifecycle import (
    LifecycleStage,
    LifecycleTransitionError,
    StrategyEvidence,
    StrategyLifecycleManager,
    StrategyVerdict,
)
from strategy.library.strategy_library import (
    StrategyCatalogEntry,
    StrategyLibraryManager,
)


def test_crypto_only_universe_enforcement():
    mgr = CryptoUniverseManager()

    # Valid crypto assets
    profile_btc = mgr.validate_asset("BTCUSDT")
    assert profile_btc.base_asset == "BTC"
    assert profile_btc.min_notional_usd == 5.0

    profile_eth = mgr.validate_asset("ETHUSDT")
    assert profile_eth.base_asset == "ETH"

    # Non-crypto assets strictly rejected
    with pytest.raises(NonCryptoAssetError, match="Non-crypto asset 'AAPL' is forbidden"):
        mgr.validate_asset("AAPL")

    with pytest.raises(NonCryptoAssetError, match="Non-crypto asset 'NIFTY' is forbidden"):
        mgr.validate_asset("NIFTY")

    with pytest.raises(NonCryptoAssetError, match="Non-crypto asset 'EURUSD' is forbidden"):
        mgr.validate_asset("EURUSD")

    with pytest.raises(NonCryptoAssetError, match="Non-crypto asset 'GOLD' is forbidden"):
        mgr.validate_asset("GOLD")


def test_strategy_lifecycle_progression_and_quarantine():
    ev = StrategyEvidence(current_stage=LifecycleStage.DRAFT)

    # Valid sequential transition: DRAFT -> FORMALIZED
    StrategyLifecycleManager.transition(ev, LifecycleStage.FORMALIZED, "Specification verified")
    assert ev.current_stage == LifecycleStage.FORMALIZED

    # Valid sequential transition: FORMALIZED -> BACKTEST
    StrategyLifecycleManager.transition(ev, LifecycleStage.BACKTEST, "Backtesting scheduled")
    assert ev.current_stage == LifecycleStage.BACKTEST

    # Illegal forward skip blocked: BACKTEST -> ROBUSTNESS (skips FALSIFICATION, OOS, ADVERSARIAL)
    with pytest.raises(LifecycleTransitionError, match="Cannot skip lifecycle stages"):
        StrategyLifecycleManager.transition(ev, LifecycleStage.ROBUSTNESS)

    # Emergency quarantine allowed from any stage
    StrategyLifecycleManager.transition(ev, LifecycleStage.QUARANTINED, "Performance degraded")
    assert ev.current_stage == LifecycleStage.QUARANTINED
    assert ev.verdict == StrategyVerdict.NOT_READY


def test_strategy_lab_natural_language_parsing_and_evaluation():
    engine = StrategyLabEngine()

    prompt = (
        "Buy BTC and ETH pullbacks when the daily and 4h structure is bullish, "
        "enter after 15m lower-timeframe confirmation and require at least 5R."
    )

    spec = engine.parse_natural_language(prompt, tenant_id="tenant_123")
    assert spec.domain == StrategyDomain.DOMAIN_C_USER
    assert "BTCUSDT" in spec.assets
    assert "ETHUSDT" in spec.assets
    assert "1d" in spec.timeframes
    assert "4h" in spec.timeframes
    assert "15m" in spec.timeframes
    assert "5R" in spec.target_rule
    assert spec.tenant_id == "tenant_123"

    # Evaluate the parsed strategy
    evidence, report = engine.evaluate_strategy(spec, simulated_sample_trades=120)
    assert evidence.total_trades == 120
    assert evidence.expectancy_r > 0
    assert evidence.verdict in (
        StrategyVerdict.PAPER_ELIGIBLE,
        StrategyVerdict.FORWARD_VALIDATION_ELIGIBLE,
    )
    assert report["disclaimer"] == "EVALUATION METRICS REFLECT HISTORICAL TESTING ONLY. NO PROFITABILITY IS GUARANTEED."


def test_strategy_library_catalog_and_tenant_scoping():
    library = StrategyLibraryManager()

    # Domain A (KING) must exist as protected core
    king = library.get_entry("STRATA_KING_ENGINE")
    assert king is not None
    assert king.domain == StrategyDomain.DOMAIN_A_KING
    assert king.status == "PROTECTED_CORE"

    # Domain B (Built-ins) must exist
    built_ins = library.list_entries(domain=StrategyDomain.DOMAIN_B_BUILT_IN)
    assert len(built_ins) >= 3

    # Add user strategy for Tenant 1
    user_entry = StrategyCatalogEntry(
        strategy_id="USER_STRAT_01",
        name="Custom Pullback",
        description="Tenant 1 strategy",
        domain=StrategyDomain.DOMAIN_C_USER,
        status="PAPER",
        assets=["BTCUSDT"],
        timeframes=["1d", "4h"],
        evidence=StrategyEvidence(),
        tenant_id="tenant_1",
    )
    library.register_entry(user_entry)

    # Tenant 1 can see their strategy + system strategies
    tenant_1_view = library.list_entries(tenant_id="tenant_1")
    t1_ids = [e.strategy_id for e in tenant_1_view]
    assert "USER_STRAT_01" in t1_ids
    assert "STRATA_KING_ENGINE" in t1_ids

    # Tenant 2 CANNOT see Tenant 1's strategy!
    tenant_2_view = library.list_entries(tenant_id="tenant_2")
    t2_ids = [e.strategy_id for e in tenant_2_view]
    assert "USER_STRAT_01" not in t2_ids
    assert "STRATA_KING_ENGINE" in t2_ids
