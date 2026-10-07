"""
Unit tests for Daily Multi-Set Decision Record Engine (Level 1 to 8 Decision Hierarchy).
"""

import pytest
from production.decision_record_engine import DecisionRecordEngine, PlatformDecisionVerdict


def test_decision_engine_level_1_data_latency_rejection():
    engine = DecisionRecordEngine(account_capital=1000.0)
    stale_signal = [{
        "strategy_id": "FAM-07-MTFCONT_SOLUSDT_Set2",
        "symbol": "SOL/USDT",
        "direction": "LONG",
        "set": 2,
        "entry_price": 140.0,
        "sl_price": 130.0,
        "gross_alpha_r": 0.28,
        "data_latency_sec": 45.0,  # > 30s threshold
        "market_spread_pct": 0.0002,
    }]
    
    result = engine.evaluate_daily_decisions(stale_signal, current_open_positions=[])
    evals = result["evaluations"]
    assert len(evals) == 1
    assert evals[0]["verdict"] == PlatformDecisionVerdict.NO_TRADE
    assert evals[0]["data_trust_passed"] is False
    assert "latency > 30s" in evals[0]["reason"]


def test_decision_engine_level_2_market_spread_rejection():
    engine = DecisionRecordEngine(account_capital=1000.0)
    wide_spread_signal = [{
        "strategy_id": "FAM-07-MTFCONT_SOLUSDT_Set2",
        "symbol": "SOL/USDT",
        "direction": "LONG",
        "set": 2,
        "entry_price": 140.0,
        "sl_price": 130.0,
        "gross_alpha_r": 0.28,
        "data_latency_sec": 2.0,
        "market_spread_pct": 0.0025,  # 0.25% > 0.15% threshold
    }]
    
    result = engine.evaluate_daily_decisions(wide_spread_signal, current_open_positions=[])
    evals = result["evaluations"]
    assert len(evals) == 1
    assert evals[0]["verdict"] == PlatformDecisionVerdict.NO_TRADE
    assert evals[0]["market_tradable_passed"] is False
    assert "Market spread exceeds" in evals[0]["reason"]


def test_decision_engine_level_4_net_edge_rejection():
    engine = DecisionRecordEngine(account_capital=1000.0)
    weak_signal = [{
        "strategy_id": "WEAK-SCALP_BTCUSDT_Set6",
        "symbol": "BTC/USDT",
        "direction": "LONG",
        "set": 6,
        "entry_price": 60000.0,
        "sl_price": 59900.0,  # 0.167% stop distance
        "gross_alpha_r": 0.06,  # Weak gross edge easily erased by friction
        "data_latency_sec": 1.0,
        "market_spread_pct": 0.0001,
    }]
    
    result = engine.evaluate_daily_decisions(weak_signal, current_open_positions=[])
    evals = result["evaluations"]
    assert len(evals) == 1
    assert evals[0]["verdict"] == PlatformDecisionVerdict.NO_TRADE
    assert evals[0]["net_edge_passed"] is False
    assert "viability threshold" in evals[0]["reason"]


def test_decision_engine_level_5_capital_feasibility():
    # Account capital $10 is too small for $60k BTC with tight stop
    engine = DecisionRecordEngine(account_capital=10.0)
    signal = [{
        "strategy_id": "FAM-07-MTFCONT_BTCUSDT_Set2",
        "symbol": "BTC/USDT",
        "direction": "LONG",
        "set": 2,
        "entry_price": 65000.0,
        "sl_price": 63000.0,
        "gross_alpha_r": 0.28,
        "data_latency_sec": 2.0,
        "market_spread_pct": 0.0001,
    }]
    
    result = engine.evaluate_daily_decisions(signal, current_open_positions=[])
    evals = result["evaluations"]
    assert len(evals) == 1
    assert evals[0]["verdict"] == PlatformDecisionVerdict.NO_TRADE
    assert evals[0]["capital_feasible"] is False
    assert "Capital feasibility failed" in evals[0]["reason"]


def test_decision_engine_approved_trade():
    engine = DecisionRecordEngine(account_capital=1000.0)
    valid_signal = [{
        "strategy_id": "FAM-07-MTFCONT_SOLUSDT_Set2",
        "symbol": "SOL/USDT",
        "direction": "LONG",
        "set": 2,
        "entry_price": 140.0,
        "sl_price": 130.0,
        "gross_alpha_r": 0.28,
        "data_latency_sec": 2.0,
        "market_spread_pct": 0.0002,
    }]
    
    result = engine.evaluate_daily_decisions(valid_signal, current_open_positions=[])
    evals = result["evaluations"]
    assert len(evals) == 1
    assert evals[0]["verdict"] == PlatformDecisionVerdict.TRADE
    assert evals[0]["data_trust_passed"] is True
    assert evals[0]["market_tradable_passed"] is True
    assert evals[0]["net_edge_passed"] is True
    assert evals[0]["capital_feasible"] is True
    assert evals[0]["portfolio_approved"] is True
    assert evals[0]["allocated_risk_pct"] > 0.0
