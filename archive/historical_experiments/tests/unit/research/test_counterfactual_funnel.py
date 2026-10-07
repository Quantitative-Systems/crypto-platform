"""
Unit tests for CounterfactualFunnelEngine.
"""

import pytest
from research.analytics.counterfactual_funnel_engine import (
    CounterfactualFunnelEngine,
    GateEfficacyVerdict
)


def test_simulate_counterfactual_trade_adverse_loss():
    # Long trade where low triggers stop loss first
    res = CounterfactualFunnelEngine.simulate_counterfactual_trade(
        entry_price=100.0,
        is_long=True,
        subsequent_highs=[101.0, 102.0],
        subsequent_lows=[98.5, 99.0],  # 98.5 hits stop (100 * 0.99 = 99.0)
        target_rr=4.0,
        stop_dist_pct=0.01
    )
    assert res["outcome"] == "LOSS"
    assert res["realized_r"] == -1.0


def test_simulate_counterfactual_trade_target_win():
    # Long trade where price reaches 4R target without hitting stop
    res = CounterfactualFunnelEngine.simulate_counterfactual_trade(
        entry_price=100.0,
        is_long=True,
        subsequent_highs=[102.0, 104.5],  # 104.5 hits 4R target (100 * (1 + 0.04) = 104.0)
        subsequent_lows=[99.5, 100.0],   # Never breaches stop (99.0)
        target_rr=4.0,
        stop_dist_pct=0.01
    )
    assert res["outcome"] == "WIN"
    assert res["realized_r"] == 4.0


def test_evaluate_gate_counterfactually_protective_filter():
    # 20 setups where 18 are losses (filter correctly saves capital)
    setups = []
    for i in range(20):
        if i < 18:
            # Loss path
            setups.append({
                "entry_price": 100.0,
                "direction": "LONG",
                "future_highs": [100.2],
                "future_lows": [98.0],
                "stop_dist_pct": 0.01
            })
        else:
            # Win path
            setups.append({
                "entry_price": 100.0,
                "direction": "LONG",
                "future_highs": [105.0],
                "future_lows": [99.5],
                "stop_dist_pct": 0.01
            })

    result = CounterfactualFunnelEngine.evaluate_gate_counterfactually(
        gate_name="REJECT_INVALID_ANCHOR_GEOMETRY",
        rejected_setups=setups,
        target_rr=4.0
    )
    assert result.total_rejections_audited == 20
    assert result.counterfactual_losses == 18
    assert result.counterfactual_wins == 2
    assert result.capital_saved_r == 18.0
    assert result.alpha_forfeited_r == 8.0
    assert result.net_economic_value_r == 10.0
    assert result.verdict == GateEfficacyVerdict.PROTECTIVE_RISK_FILTER
