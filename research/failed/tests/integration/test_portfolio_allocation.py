"""
Integration Tests for Multi-Alpha Portfolio Capital Allocation.
Verifies dynamic allocation across directional alpha slots (SOL Set 2) and relative-value alpha slots.
Ensures capital firewall compliance, heat ceilings, concentration constraints, and lifecycle filtering.
"""

import pytest
import numpy as np
from portfolio_engine.capital_allocator import (
    GenericCapitalAllocator,
    AlphaSlotInput,
    AlphaAllocationResult,
    PortfolioAllocationReport,
)
from portfolio_engine.portfolio_intelligence import (
    PortfolioIntelligenceEngine,
    PortfolioAllocationDecision,
)
from risk_engine.portfolio_risk_firewall import PortfolioRiskFirewall


def test_multi_alpha_allocation_directional_and_rv():
    """
    Validates capital allocation when presenting:
    1. SOL Set 2 (FORWARD_HEALTHY, net edge +0.611R)
    2. BTC/ETH RV (FALSIFIED, negative net edge)
    3. SOL/ETH RV (RESEARCH, negative net edge)
    4. SOL/BTC RV (FALSIFIED, negative net edge)
    Only the qualified directional alpha should receive non-zero allocation.
    """
    allocator = GenericCapitalAllocator()

    candidates = [
        AlphaSlotInput(
            strategy_id="alpha_slot_01_sol_directional",
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
        ),
        AlphaSlotInput(
            strategy_id="alpha_slot_02_btc_eth_rv",
            symbol="BTC/ETH",
            timeframe="4h",
            expected_net_edge_r=-0.450,
            uncertainty_penalty=0.220,
            volatility_annual_pct=45.0,
            max_drawdown_pct=18.5,
            capacity_limit_usd=500_000.0,
            execution_quality_score=0.85,
            lifecycle_tier="FALSIFIED",
            degradation_flag=True,
        ),
        AlphaSlotInput(
            strategy_id="alpha_slot_03_sol_eth_rv",
            symbol="SOL/ETH",
            timeframe="4h",
            expected_net_edge_r=-0.620,
            uncertainty_penalty=0.310,
            volatility_annual_pct=70.0,
            max_drawdown_pct=22.4,
            capacity_limit_usd=200_000.0,
            execution_quality_score=0.80,
            lifecycle_tier="RESEARCH",
            degradation_flag=True,
        ),
        AlphaSlotInput(
            strategy_id="alpha_slot_04_sol_btc_rv",
            symbol="SOL/BTC",
            timeframe="4h",
            expected_net_edge_r=-0.510,
            uncertainty_penalty=0.280,
            volatility_annual_pct=68.0,
            max_drawdown_pct=20.1,
            capacity_limit_usd=200_000.0,
            execution_quality_score=0.82,
            lifecycle_tier="FALSIFIED",
            degradation_flag=True,
        ),
    ]

    report: PortfolioAllocationReport = allocator.allocate_portfolio(
        alpha_slots=candidates,
        portfolio_equity_usd=100_000.0,
        current_drawdown_pct=0.0,
    )

    # Assertions
    assert report.allocated_strategies_count == 1
    assert report.rejected_strategies_count == 3

    # Allocated slot checks
    sol_alloc = report.allocations["alpha_slot_01_sol_directional"]
    assert sol_alloc.is_allocated is True
    assert sol_alloc.recommended_risk_pct > 0.0
    assert sol_alloc.recommended_risk_pct <= 1.50  # Single strategy ceiling
    assert sol_alloc.recommended_notional_usd > 0.0

    # Zero allocation for RV candidates
    for rv_id in ["alpha_slot_02_btc_eth_rv", "alpha_slot_03_sol_eth_rv", "alpha_slot_04_sol_btc_rv"]:
        rv_alloc = report.allocations[rv_id]
        assert rv_alloc.is_allocated is False
        assert rv_alloc.recommended_risk_pct == 0.0
        assert rv_alloc.recommended_notional_usd == 0.0
        assert len(rv_alloc.rejection_reasons) > 0

    # Verify total heat constraint
    assert report.total_allocated_heat_pct <= 3.00


def test_portfolio_intelligence_and_allocator_coordination():
    """
    Verifies that PortfolioIntelligenceEngine trade-level risk assessment
    aligns with GenericCapitalAllocator portfolio heat budgets.
    """
    allocator = GenericCapitalAllocator()
    candidate = AlphaSlotInput(
        strategy_id="sol_directional",
        symbol="SOL/USDT",
        timeframe="15m",
        expected_net_edge_r=0.611,
        uncertainty_penalty=0.150,
        volatility_annual_pct=65.0,
        max_drawdown_pct=4.73,
        capacity_limit_usd=250_000.0,
        execution_quality_score=0.95,
        lifecycle_tier="FORWARD_HEALTHY",
    )

    account_equity = 100_000.0
    alloc_report = allocator.allocate_portfolio([candidate], portfolio_equity_usd=account_equity)
    sol_alloc = alloc_report.allocations["sol_directional"]

    # Convert allocator recommended risk to trade evaluation
    open_positions = []
    trade_eval = PortfolioIntelligenceEngine.evaluate_new_trade(
        candidate_symbol="SOLUSDT",
        candidate_direction="LONG",
        current_open_positions=open_positions,
        account_equity=account_equity,
        current_drawdown_pct=0.0,
    )

    assert trade_eval.decision in (
        PortfolioAllocationDecision.APPROVED_FULL_SIZE,
        PortfolioAllocationDecision.APPROVED_SCALED_SIZE,
    )
    assert trade_eval.recommended_risk_pct <= 3.00
    assert sol_alloc.recommended_risk_pct <= PortfolioIntelligenceEngine.MAX_PORTFOLIO_HEAT_PCT
