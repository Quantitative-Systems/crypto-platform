"""Unit tests for Edge Discovery Engine, Benchmark Lab, Null Hypothesis Lab, and EQS."""
import pytest
import numpy as np
from research.discovery.benchmark_lab import BenchmarkLab
from research.discovery.null_hypothesis_lab import NullHypothesisLab
from research.discovery.edge_quality_scorer import EdgeQualityScorer
from research.discovery.edge_discovery_engine import EdgeDiscoveryEngine


def test_benchmark_lab_buy_and_hold():
    lab = BenchmarkLab()
    closes = np.array([100.0, 105.0, 110.0, 120.0])
    ts = np.array([1000, 2000, 3000, 4000])
    res = lab.run_benchmark_0_buy_and_hold("BTCUSDT", "1d", closes, ts)
    assert res.benchmark_id == "BM_0"
    assert res.total_r > 0
    assert res.win_rate == 1.0


def test_benchmark_lab_trend_breakout():
    lab = BenchmarkLab()
    # 50 bars with clear upward trend
    c = np.linspace(100, 200, 60)
    o = c - 1.0
    h = c + 2.0
    l = c - 2.0
    ts = np.arange(1000, 1000 + 60 * 1000, 1000)
    data = {"o": o, "h": h, "l": l, "c": c, "ts": ts}
    res = lab.run_benchmark_4_trend_breakout("BTCUSDT", "1h", data, window=10)
    assert res.benchmark_id == "BM_4"
    assert res.total_trades >= 0


def test_edge_quality_scorer():
    metrics_full = {
        "expectancy_r": 0.35,
        "total_trades": 120,
        "max_drawdown_r": 8.5,
        "cvar_95_r": -1.05,
        "exp_r_ex_top2": 0.28,
        "top2_concentration_pct": 25.0,
    }
    metrics_dev = {"expectancy_r": 0.32}
    metrics_val = {"expectancy_r": 0.30}
    metrics_oos = {"expectancy_r": 0.38}
    asset_transfer = {"BTC": 0.35, "ETH": 0.25, "SOL": 0.40}
    scale_transfer = {"SET_2": 0.35, "SET_3": 0.30, "SET_4": 0.20}
    cost_2x = {"expectancy_r": 0.25}

    eqs = EdgeQualityScorer.score_candidate(
        candidate_id="TEST_CANDIDATE_01",
        metrics_full=metrics_full,
        metrics_dev=metrics_dev,
        metrics_val=metrics_val,
        metrics_oos=metrics_oos,
        asset_transfer_results=asset_transfer,
        scale_transfer_results=scale_transfer,
        cost_stress_2x=cost_2x,
        null_test_p_value=0.005,
    )

    assert eqs.total_score >= 80.0
    assert eqs.classification == "STRONG_EDGE"
    assert eqs.expectancy_score > 0
    assert eqs.concentration_score == 10.0


def test_edge_discovery_engine_initialization():
    engine = EdgeDiscoveryEngine()
    assert engine.benchmark_lab is not None
    assert engine.null_lab is not None
    assert engine.scorer is not None
