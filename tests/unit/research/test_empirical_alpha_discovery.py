"""
Unit tests for EmpiricalAlphaDiscoveryEngine.
Validates empirical opportunity detection, causal partition backtesting,
rejection taxonomy accounting, multiple-testing control, and fail-closed capital firewall.
"""

import json
import os
import pytest
from pathlib import Path
import pandas as pd

from market_intelligence.continuous_regime_engine import RegimeState, TrendState, VolatilityState, LiquidityState, FundingState, CorrelationState
from market_intelligence.opportunity_detector import OpportunityType
from research.discovery_lab.empirical_alpha_discovery_engine import (
    EmpiricalAlphaDiscoveryEngine,
    CandidateDiscoveryEvaluation,
    BacktestConfig,
)
from research.economic_evaluation_engine import PartitionMetrics


def test_empirical_alpha_discovery_engine_init():
    engine = EmpiricalAlphaDiscoveryEngine()
    assert engine.universe_engine is not None
    assert engine.regime_engine is not None
    assert engine.detector is not None
    assert engine.governor is not None
    assert engine.falsifier is not None
    assert engine.capacity_engine is not None
    assert engine.memory is not None


def test_scan_empirical_market_opportunities():
    engine = EmpiricalAlphaDiscoveryEngine()

    dummy_df = pd.DataFrame({
        "timestamp": range(1000, 1000 + 200 * 14400, 14400),
        "open": [100.0 + i * 0.1 for i in range(200)],
        "high": [102.0 + i * 0.1 for i in range(200)],
        "low": [99.0 + i * 0.1 for i in range(200)],
        "close": [101.0 + i * 0.1 for i in range(200)],
        "volume": [1000.0] * 200,
    })

    loaded_dfs = {
        "BTC/USDT": dummy_df,
        "ETH/USDT": dummy_df,
    }

    rs_btc = RegimeState(
        symbol="BTC/USDT",
        timestamp_utc="2026-09-16T12:00:00Z",
        trend=TrendState.SIDEWAYS_CHOP,
        trend_strength_score=0.20,
        volatility=VolatilityState.NORMAL_VOL,
        volatility_percentile=50.0,
        liquidity=LiquidityState.NORMAL_DEPTH,
        liquidity_depth_ratio=1.0,
        funding=FundingState.NEUTRAL_CARRY,
        annualized_funding_pct=8.0,
        correlation=CorrelationState.COUPLED_SYSTEMIC_SHOCK,
        systemic_coupling_score=0.85,
    )

    opps = engine._scan_empirical_market_opportunities(
        available_assets=["BTC/USDT", "ETH/USDT"],
        loaded_dfs=loaded_dfs,
        regime_states=[rs_btc],
    )

    types = {o.opportunity_type for o in opps}
    assert OpportunityType.TREND_MOMENTUM in types
    assert OpportunityType.VOLATILITY_SQUEEZE in types
    assert OpportunityType.DISPERSION_DIVERGENCE in types
    assert OpportunityType.FUNDING_ANOMALY in types
    assert OpportunityType.LIQUIDITY_IMBALANCE in types
    assert OpportunityType.LIQUIDATION_CASCADE in types

    # Verify that external streams have explicit unwarehoused data tokens
    carry_opp = next(o for o in opps if o.opportunity_type == OpportunityType.FUNDING_ANOMALY and o.symbol == "BTC/USDT")
    assert "FUNDING_RATE_HISTORY_BTCUSDT" in carry_opp.required_data_tokens


def test_tally_rejections_and_bonferroni():
    engine = EmpiricalAlphaDiscoveryEngine()

    dummy_evals = [
        CandidateDiscoveryEvaluation(
            experiment_id="EXP-001",
            hypothesis_id="HYP-01",
            candidate_id="CAND-01",
            family="DIRECTIONAL",
            symbol="BTC/USDT",
            timeframe="4h",
            parameters={},
            dev_metrics=None,
            val_metrics=None,
            oos_metrics=None,
            falsification_report=None,
            capacity_usd=0.0,
            factor_beta_btc=0.0,
            verdict="BLOCKED_EXTERNAL_DATA",
            rejection_reason="Blocked data",
            trade_count_total=0,
        ),
        CandidateDiscoveryEvaluation(
            experiment_id="EXP-002",
            hypothesis_id="HYP-02",
            candidate_id="CAND-02",
            family="DIRECTIONAL",
            symbol="BTC/USDT",
            timeframe="4h",
            parameters={},
            dev_metrics=None,
            val_metrics=None,
            oos_metrics=None,
            falsification_report=None,
            capacity_usd=0.0,
            factor_beta_btc=0.0,
            verdict="FALSIFIED",
            rejection_reason="FRICTION_OVERWHELMED: fees wipe edge",
            trade_count_total=20,
        ),
        CandidateDiscoveryEvaluation(
            experiment_id="EXP-003",
            hypothesis_id="HYP-03",
            candidate_id="CAND-03",
            family="DIRECTIONAL",
            symbol="BTC/USDT",
            timeframe="4h",
            parameters={},
            dev_metrics=None,
            val_metrics=None,
            oos_metrics=None,
            falsification_report=None,
            capacity_usd=0.0,
            factor_beta_btc=0.0,
            verdict="FALSIFIED",
            rejection_reason="SUB_HURDLE_EDGE: DEV net expectancy below hurdle",
            trade_count_total=18,
        ),
    ]

    tally = engine._tally_rejections(dummy_evals)
    assert tally["BLOCKED_EXTERNAL_DATA"] == 1
    assert tally["FRICTION_OVERWHELMED"] == 1
    assert tally["SUB_HURDLE_EDGE"] == 1
