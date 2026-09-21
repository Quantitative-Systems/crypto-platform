"""
Unit tests for Capital Feasibility & Survivability Engine.
"""

import pytest
from capital_intelligence.feasibility_engine import (
    CapitalFeasibilityEngine,
    FeasibilityVerdict,
    FeasibilityEvaluation,
)


def test_feasibility_small_account_distortion():
    # $10 account trading BTCUSDT futures
    eval_res = CapitalFeasibilityEngine.evaluate_feasibility(
        account_capital=10.0,
        symbol="BTCUSDT",
        entry_price=45000.0,
        stop_distance_usd=1890.0,  # 4.2% SL
        venue="USDM_FUTURES",
        target_risk_pct=0.006,  # $0.06 target
    )
    assert eval_res.account_capital == 10.0
    assert eval_res.target_risk_usd == 0.06
    # Executable qty must be at least min lot 0.001 BTC
    assert eval_res.executable_qty >= 0.001
    assert eval_res.executable_notional >= 45.0
    # Realized risk = 0.001 * 1890 = $1.89 (18.9% of $10)
    assert eval_res.actual_risk_usd >= 1.89
    assert eval_res.actual_risk_pct >= 18.0
    # Distortion ratio > 30x
    assert eval_res.risk_distortion_ratio > 30.0
    assert eval_res.verdict in (FeasibilityVerdict.HIGH_RISK_DISTORTED, FeasibilityVerdict.NOT_FEASIBLE)


def test_feasibility_institutional_clean_execution():
    # $1,000 account trading SOLUSDT futures
    eval_res = CapitalFeasibilityEngine.evaluate_feasibility(
        account_capital=1000.0,
        symbol="SOLUSDT",
        entry_price=100.0,
        stop_distance_usd=3.50,  # 3.5% SL
        venue="USDM_FUTURES",
        target_risk_pct=0.006,  # $6.00 target
    )
    assert eval_res.account_capital == 1000.0
    assert eval_res.target_risk_usd == 6.0
    # Theoretical qty = 6.0 / 3.5 = 1.714 SOL
    # Executable notional ~$172 (well above $5 min notional)
    assert eval_res.executable_notional > 5.0
    # Risk distortion should be ~1.0x (clean execution)
    assert 0.95 <= eval_res.risk_distortion_ratio <= 1.05
    assert eval_res.required_leverage < 1.0
    assert eval_res.verdict == FeasibilityVerdict.EXECUTABLE


def test_gamblers_ruin_prob():
    # High risk (20% per trade) should have high ruin prob
    ruin_high_risk = CapitalFeasibilityEngine.calculate_gamblers_ruin_prob(
        win_rate=0.40, payoff_ratio=2.0, risk_pct_per_trade=20.0
    )
    # Low risk (0.60% per trade) should have near zero ruin prob
    ruin_low_risk = CapitalFeasibilityEngine.calculate_gamblers_ruin_prob(
        win_rate=0.40, payoff_ratio=2.0, risk_pct_per_trade=0.60
    )
    assert ruin_high_risk > 0.50
    assert ruin_low_risk < 0.01
