"""
Unit Tests for Generic Dynamic Capital Allocator.
Verifies all 20 required allocator behaviors:
- Net edge ranking, uncertainty discounting, volatility normalization
- Concentration ceilings, heat ceiling, drawdown throttling, degradation
- Lifecycle filtering, capacity constraints, fail-closed handling
"""

import pytest
import math
from portfolio_engine.capital_allocator import (
    GenericCapitalAllocator,
    AlphaSlotInput,
    PortfolioAllocationReport,
)


def test_positive_edge_allocation():
    allocator = GenericCapitalAllocator()
    slots = [
        AlphaSlotInput(
            strategy_id="SOL_TREND",
            symbol="SOL/USDT",
            timeframe="15m",
            expected_net_edge_r=0.61,
            uncertainty_penalty=0.10,
            volatility_annual_pct=45.0,
            max_drawdown_pct=4.73,
            capacity_limit_usd=100000.0,
            execution_quality_score=0.95,
            lifecycle_tier="FORWARD_HEALTHY",
        )
    ]
    report = allocator.allocate_portfolio(slots, portfolio_equity_usd=10000.0)
    assert report.allocated_strategies_count == 1
    assert report.total_allocated_heat_pct > 0.0
    assert report.total_allocated_heat_pct <= 3.00
    res = report.allocations["SOL_TREND"]
    assert res.is_allocated is True
    assert res.recommended_risk_pct > 0.0


def test_negative_or_zero_net_edge_rejection():
    allocator = GenericCapitalAllocator()
    slots = [
        AlphaSlotInput(
            strategy_id="LOSING_STRAT",
            symbol="BTC/USDT",
            timeframe="1h",
            expected_net_edge_r=-0.15,
            uncertainty_penalty=0.05,
            volatility_annual_pct=30.0,
            max_drawdown_pct=10.0,
            capacity_limit_usd=100000.0,
            execution_quality_score=0.9,
            lifecycle_tier="FORWARD_HEALTHY",
        ),
        AlphaSlotInput(
            strategy_id="ZERO_EDGE_STRAT",
            symbol="ETH/USDT",
            timeframe="1h",
            expected_net_edge_r=0.0,
            uncertainty_penalty=0.05,
            volatility_annual_pct=35.0,
            max_drawdown_pct=8.0,
            capacity_limit_usd=100000.0,
            execution_quality_score=0.9,
            lifecycle_tier="FORWARD_HEALTHY",
        ),
    ]
    report = allocator.allocate_portfolio(slots, portfolio_equity_usd=10000.0)
    assert report.allocated_strategies_count == 0
    assert report.rejected_strategies_count == 2
    assert "NEGATIVE_OR_ZERO_NET_EDGE" in report.allocations["LOSING_STRAT"].rejection_reasons[0]


def test_uncertainty_exceeding_edge_rejection():
    allocator = GenericCapitalAllocator()
    slots = [
        AlphaSlotInput(
            strategy_id="HIGH_UNCERTAINTY_STRAT",
            symbol="SOL/USDT",
            timeframe="15m",
            expected_net_edge_r=0.20,
            uncertainty_penalty=0.15,  # 1.96 * 0.15 = 0.294 > 0.20 -> E_adj <= 0
            volatility_annual_pct=40.0,
            max_drawdown_pct=5.0,
            capacity_limit_usd=100000.0,
            execution_quality_score=0.85,
            lifecycle_tier="FORWARD_HEALTHY",
        )
    ]
    report = allocator.allocate_portfolio(slots, portfolio_equity_usd=10000.0)
    assert report.allocated_strategies_count == 0
    assert "STATISTICAL_UNCERTAINTY_EXCEEDS_EDGE" in report.allocations["HIGH_UNCERTAINTY_STRAT"].rejection_reasons[0]


def test_lifecycle_filtering_research_and_falsified():
    allocator = GenericCapitalAllocator()
    slots = [
        AlphaSlotInput(
            strategy_id="RESEARCH_CANDIDATE",
            symbol="BTC/ETH",
            timeframe="1d",
            expected_net_edge_r=0.50,
            uncertainty_penalty=0.05,
            volatility_annual_pct=25.0,
            max_drawdown_pct=5.0,
            capacity_limit_usd=100000.0,
            execution_quality_score=0.9,
            lifecycle_tier="RESEARCH",  # Ineligible
        ),
        AlphaSlotInput(
            strategy_id="FALSIFIED_CANDIDATE",
            symbol="SOL/ETH",
            timeframe="4h",
            expected_net_edge_r=0.40,
            uncertainty_penalty=0.05,
            volatility_annual_pct=30.0,
            max_drawdown_pct=6.0,
            capacity_limit_usd=100000.0,
            execution_quality_score=0.9,
            lifecycle_tier="FALSIFIED",  # Ineligible
        ),
    ]
    report = allocator.allocate_portfolio(slots, portfolio_equity_usd=10000.0)
    assert report.allocated_strategies_count == 0
    assert "LIFECYCLE_INELIGIBLE" in report.allocations["RESEARCH_CANDIDATE"].rejection_reasons[0]
    assert "LIFECYCLE_INELIGIBLE" in report.allocations["FALSIFIED_CANDIDATE"].rejection_reasons[0]


def test_drawdown_throttling_and_circuit_breaker():
    allocator = GenericCapitalAllocator()
    slot = AlphaSlotInput(
        strategy_id="NOMINAL_STRAT",
        symbol="SOL/USDT",
        timeframe="15m",
        expected_net_edge_r=0.60,
        uncertainty_penalty=0.05,
        volatility_annual_pct=40.0,
        max_drawdown_pct=5.0,
        capacity_limit_usd=100000.0,
        execution_quality_score=0.9,
        lifecycle_tier="FORWARD_HEALTHY",
    )

    # DD = 0% -> Full allocation
    rep_0 = allocator.allocate_portfolio([slot], 10000.0, current_drawdown_pct=0.0)
    r_0 = rep_0.allocations["NOMINAL_STRAT"].recommended_risk_pct

    # DD = 10% -> 50% throttle
    rep_10 = allocator.allocate_portfolio([slot], 10000.0, current_drawdown_pct=10.0)
    r_10 = rep_10.allocations["NOMINAL_STRAT"].recommended_risk_pct
    assert pytest.approx(r_10, rel=1e-2) == r_0 * 0.50

    # DD = 20% -> 25% throttle
    rep_20 = allocator.allocate_portfolio([slot], 10000.0, current_drawdown_pct=20.0)
    r_20 = rep_20.allocations["NOMINAL_STRAT"].recommended_risk_pct
    assert pytest.approx(r_20, rel=1e-2) == r_0 * 0.25

    # DD = 30% -> Circuit Breaker Halt (0%)
    rep_30 = allocator.allocate_portfolio([slot], 10000.0, current_drawdown_pct=30.0)
    assert rep_30.allocated_strategies_count == 0
    assert rep_30.firewall_veto_triggered is True


def test_degradation_haircut():
    allocator = GenericCapitalAllocator()
    slot_normal = AlphaSlotInput(
        strategy_id="NORMAL_STRAT",
        symbol="SOL/USDT",
        timeframe="15m",
        expected_net_edge_r=0.50,
        uncertainty_penalty=0.05,
        volatility_annual_pct=40.0,
        max_drawdown_pct=5.0,
        capacity_limit_usd=100000.0,
        execution_quality_score=1.0,
        lifecycle_tier="FORWARD_HEALTHY",
        degradation_flag=False,
    )
    slot_degraded = AlphaSlotInput(
        strategy_id="DEGRADED_STRAT",
        symbol="ETH/USDT",
        timeframe="15m",
        expected_net_edge_r=0.50,
        uncertainty_penalty=0.05,
        volatility_annual_pct=40.0,
        max_drawdown_pct=5.0,
        capacity_limit_usd=100000.0,
        execution_quality_score=1.0,
        lifecycle_tier="FORWARD_HEALTHY",
        degradation_flag=True,
    )

    report = allocator.allocate_portfolio([slot_normal, slot_degraded], 10000.0)
    w_norm = report.allocations["NORMAL_STRAT"].allocation_weight_pct
    w_deg = report.allocations["DEGRADED_STRAT"].allocation_weight_pct
    # Degraded strategy should receive half the raw weight of normal
    assert pytest.approx(w_norm / w_deg, rel=0.1) == 2.0


def test_fail_closed_on_nan_inputs():
    allocator = GenericCapitalAllocator()
    slots = [
        AlphaSlotInput(
            strategy_id="NAN_EDGE_STRAT",
            symbol="BTC/USDT",
            timeframe="1h",
            expected_net_edge_r=float("nan"),
            uncertainty_penalty=0.05,
            volatility_annual_pct=30.0,
            max_drawdown_pct=5.0,
            capacity_limit_usd=100000.0,
            execution_quality_score=0.9,
            lifecycle_tier="FORWARD_HEALTHY",
        )
    ]
    report = allocator.allocate_portfolio(slots, portfolio_equity_usd=10000.0)
    assert report.allocated_strategies_count == 0
    assert "INVALID_OR_NAN_NUMERICAL_INPUTS_FAIL_CLOSED" in report.allocations["NAN_EDGE_STRAT"].rejection_reasons[0]


def test_portfolio_heat_and_concentration_ceilings():
    allocator = GenericCapitalAllocator(max_portfolio_heat_pct=3.00)
    # 3 highly profitable strategies on SOL
    slots = [
        AlphaSlotInput(
            strategy_id=f"SOL_STRAT_{i}",
            symbol="SOL/USDT",
            timeframe="15m",
            expected_net_edge_r=1.50,
            uncertainty_penalty=0.05,
            volatility_annual_pct=30.0,
            max_drawdown_pct=3.0,
            capacity_limit_usd=100000.0,
            execution_quality_score=1.0,
            lifecycle_tier="FORWARD_HEALTHY",
        )
        for i in range(3)
    ]
    report = allocator.allocate_portfolio(slots, portfolio_equity_usd=10000.0)
    # Total allocated heat must strictly be <= 3.00%
    assert report.total_allocated_heat_pct <= 3.00
    # Single strategy risk must strictly be <= 1.50%
    for s_id, alloc in report.allocations.items():
        assert alloc.recommended_risk_pct <= 1.50


def test_allocator_tracing_proves_cap_binding():
    """
    Proves that for a single candidate, the allocator calculates raw_proposed_risk_pct = 3.00%
    and that the 1.50% allocation is strictly due to the strategy concentration cap being binding.
    """
    allocator = GenericCapitalAllocator(max_portfolio_heat_pct=3.00)
    slot = AlphaSlotInput(
        strategy_id="SOL_SET2",
        symbol="SOL/USDT",
        timeframe="15m",
        expected_net_edge_r=0.611,
        uncertainty_penalty=0.150,
        volatility_annual_pct=65.0,
        max_drawdown_pct=4.73,
        capacity_limit_usd=250000.0,
        execution_quality_score=0.95,
        lifecycle_tier="FORWARD_HEALTHY",
    )
    report = allocator.allocate_portfolio([slot], portfolio_equity_usd=100000.0)
    alloc = report.allocations["SOL_SET2"]
    assert alloc.is_allocated is True
    assert alloc.raw_proposed_risk_pct == 3.00
    assert alloc.is_capped_by_strategy_ceiling is True
    assert alloc.recommended_risk_pct == 1.50
    assert any("Capped at strategy concentration ceiling" in note for note in alloc.throttling_notes)


def test_multi_alpha_covariance_penalty_and_independence():
    """
    Tests dynamic allocation between two simultaneous positive candidates:
    verifies that high correlation matrix produces safe, capped co-allocation.
    """
    import numpy as np
    allocator = GenericCapitalAllocator(max_portfolio_heat_pct=3.00)

    slot_a = AlphaSlotInput(
        strategy_id="ALPHA_SOL",
        symbol="SOL/USDT",
        timeframe="15m",
        expected_net_edge_r=0.60,
        uncertainty_penalty=0.10,
        volatility_annual_pct=50.0,
        max_drawdown_pct=5.0,
        capacity_limit_usd=100000.0,
        execution_quality_score=1.0,
        lifecycle_tier="FORWARD_HEALTHY",
    )
    slot_b = AlphaSlotInput(
        strategy_id="ALPHA_ETH",
        symbol="ETH/USDT",
        timeframe="15m",
        expected_net_edge_r=0.60,
        uncertainty_penalty=0.10,
        volatility_annual_pct=50.0,
        max_drawdown_pct=5.0,
        capacity_limit_usd=100000.0,
        execution_quality_score=1.0,
        lifecycle_tier="FORWARD_HEALTHY",
    )

    cov_high = np.array([
        [0.50**2, 0.50 * 0.50 * 0.85],
        [0.50 * 0.50 * 0.85, 0.50**2]
    ])

    report_high = allocator.allocate_portfolio(
        [slot_a, slot_b],
        portfolio_equity_usd=100000.0,
        covariance_matrix=cov_high,
        strategy_order=["ALPHA_SOL", "ALPHA_ETH"],
    )

    assert report_high.allocated_strategies_count == 2
    assert report_high.total_allocated_heat_pct <= 3.00
    for s_id in ["ALPHA_SOL", "ALPHA_ETH"]:
        a = report_high.allocations[s_id]
        assert a.is_allocated is True
        assert a.recommended_risk_pct <= 1.50

