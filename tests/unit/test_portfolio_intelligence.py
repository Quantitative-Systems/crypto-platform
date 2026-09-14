"""
Unit tests for Portfolio Intelligence Engine.
"""

import pytest
from portfolio_engine.portfolio_intelligence import (
    PortfolioIntelligenceEngine,
    PortfolioAllocationDecision,
)


def test_drawdown_risk_scaling_multiplier():
    assert PortfolioIntelligenceEngine.get_drawdown_risk_multiplier(2.0) == 1.00
    assert PortfolioIntelligenceEngine.get_drawdown_risk_multiplier(10.0) == 0.50
    assert PortfolioIntelligenceEngine.get_drawdown_risk_multiplier(20.0) == 0.25
    assert PortfolioIntelligenceEngine.get_drawdown_risk_multiplier(30.0) == 0.00


def test_correlated_concentration_discount():
    # Holding 2 open long positions (SOL and ETH)
    open_positions = [
        {"symbol": "SOLUSDT", "direction": "LONG", "risk_usd": 6.0},
        {"symbol": "ETHUSDT", "direction": "LONG", "risk_usd": 6.0},
    ]
    # New candidate signal: BTC long
    eval_res = PortfolioIntelligenceEngine.evaluate_new_trade(
        candidate_symbol="BTCUSDT",
        candidate_direction="LONG",
        current_open_positions=open_positions,
        account_equity=1000.0,
        current_drawdown_pct=0.0,
    )
    # Because SOL and ETH are already correlated longs, discount sizing by 50%
    assert eval_res.decision == PortfolioAllocationDecision.APPROVED_SCALED_SIZE
    assert eval_res.allocation_multiplier == 0.50
    assert eval_res.recommended_risk_pct == 0.30  # 50% of 0.60%


def test_circuit_breaker_drawdown_halt():
    eval_res = PortfolioIntelligenceEngine.evaluate_new_trade(
        candidate_symbol="SOLUSDT",
        candidate_direction="LONG",
        current_open_positions=[],
        account_equity=1000.0,
        current_drawdown_pct=26.5,  # > 25.0%
    )
    assert eval_res.decision == PortfolioAllocationDecision.REJECTED_DRAWDOWN_HALT
    assert eval_res.recommended_risk_pct == 0.0
