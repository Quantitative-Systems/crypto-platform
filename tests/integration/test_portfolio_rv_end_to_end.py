"""
End-to-End Integration Test: Relative Value Alpha Factory + Generic Capital Allocator.
Connects the econometric RelativeValueEngine output directly into the GenericCapitalAllocator.
Verifies that:
1. RV candidates evaluated on real market data are classified with empirical research verdicts.
2. Uncointegrated / negative-edge RV strategies fail qualification and are rejected by the capital allocator.
3. Only verified, forward-healthy directional alpha (SOL Set 2) receives positive allocation.
4. Capital Firewall enforces fail-closed zero live capital.
"""

import pytest
from market_data.binance_fetcher import BinanceFetcher
from research.discovery_lab.relative_value_engine import (
    RelativeValueEngine,
    RelativeValueResearchReport,
)
from portfolio_engine.capital_allocator import (
    GenericCapitalAllocator,
    AlphaSlotInput,
    PortfolioAllocationReport,
)


def test_portfolio_rv_end_to_end_integration():
    # 1. Fetch real historical candles for BTC, ETH, and SOL
    btc_candles = BinanceFetcher.fetch_real_candles("BTC/USDT", "1d", limit=1000)
    eth_candles = BinanceFetcher.fetch_real_candles("ETH/USDT", "1d", limit=1000)
    sol_candles = BinanceFetcher.fetch_real_candles("SOL/USDT", "1d", limit=1000)

    assert len(btc_candles) > 500
    assert len(eth_candles) > 500
    assert len(sol_candles) > 500

    # 2. Run Relative Value Engine across the pairs
    rv_engine = RelativeValueEngine()
    
    rep_btc_eth = rv_engine.evaluate_pair("BTC/USDT", "ETH/USDT", "BTC/ETH", btc_candles, eth_candles, "1d")
    rep_sol_eth = rv_engine.evaluate_pair("SOL/USDT", "ETH/USDT", "SOL/ETH", sol_candles, eth_candles, "1d")
    rep_sol_btc = rv_engine.evaluate_pair("SOL/USDT", "BTC/USDT", "SOL/BTC", sol_candles, btc_candles, "1d")

    rv_reports = [rep_btc_eth, rep_sol_eth, rep_sol_btc]
    
    # Verify econometric outputs exist and no pair falsely qualifies without cointegration
    for r in rv_reports:
        assert r.cointegration.hedge_ratio_beta > 0.0
        assert r.cointegration.half_life_bars > 0.0
        # If not cointegrated, research verdict must reflect falsification/fragility
        if not r.cointegration.is_engle_granger_cointegrated:
            assert r.research_verdict in (
                "FALSIFIED_NO_COINTEGRATION",
                "FRAGILE_SLOW_MEAN_REVERSION",
                "FRAGILE_MARGINAL_EDGE",
            )

    # 3. Construct AlphaSlotInput instances from empirical RV results
    rv_slots = []
    for r in rv_reports:
        # Determine lifecycle tier based on empirical research verdict
        if r.research_verdict == "QUALIFIED_RESEARCH_CANDIDATE":
            tier = "HISTORICAL_ROBUST"
        else:
            tier = "FALSIFIED"

        rv_slots.append(
            AlphaSlotInput(
                strategy_id=f"RV_{r.pair_name.replace('/', '_')}_1D",
                symbol=r.pair_name,
                timeframe=r.timeframe,
                expected_net_edge_r=r.full_sample.mean_expectancy_r,
                uncertainty_penalty=0.25,
                volatility_annual_pct=50.0,
                max_drawdown_pct=r.full_sample.max_drawdown_r,
                capacity_limit_usd=500_000.0,
                execution_quality_score=0.90,
                lifecycle_tier=tier,
                degradation_flag=(tier == "FALSIFIED"),
            )
        )

    # 4. Add verified SOL Set 2 directional alpha slot
    sol_directional_slot = AlphaSlotInput(
        strategy_id="SOL_SET2_BREAKOUT_FAMILY07",
        symbol="SOL/USDT",
        timeframe="15m",
        expected_net_edge_r=0.611,
        uncertainty_penalty=0.150,
        volatility_annual_pct=65.0,
        max_drawdown_pct=4.73,
        capacity_limit_usd=250_000.0,
        execution_quality_score=0.95,
        lifecycle_tier="FORWARD_HEALTHY",
        degradation_flag=False,
    )

    all_slots = [sol_directional_slot] + rv_slots

    # 5. Feed into GenericCapitalAllocator
    allocator = GenericCapitalAllocator()
    alloc_report: PortfolioAllocationReport = allocator.allocate_portfolio(
        alpha_slots=all_slots,
        portfolio_equity_usd=100_000.0,
        current_drawdown_pct=0.0,
    )

    # 6. Verify institutional invariants
    # Only SOL directional should be allocated
    assert alloc_report.allocated_strategies_count == 1
    assert alloc_report.rejected_strategies_count == 3

    sol_alloc = alloc_report.allocations["SOL_SET2_BREAKOUT_FAMILY07"]
    assert sol_alloc.is_allocated is True
    assert sol_alloc.recommended_risk_pct > 0.0
    assert sol_alloc.recommended_risk_pct <= 1.50
    assert sol_alloc.recommended_notional_usd > 0.0

    # All RV slots must have $0 allocation and documented rejections
    for rv_slot in rv_slots:
        rv_alloc = alloc_report.allocations[rv_slot.strategy_id]
        assert rv_alloc.is_allocated is False
        assert rv_alloc.recommended_risk_pct == 0.0
        assert rv_alloc.recommended_notional_usd == 0.0
        assert len(rv_alloc.rejection_reasons) > 0

    # Portfolio heat and firewall limits
    assert alloc_report.total_allocated_heat_pct <= 3.00
    assert alloc_report.is_capital_firewall_locked is True
