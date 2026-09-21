"""
Integration Tests for Product 04: 24-Baseline Matrix & A/B Trailing Experiment
"""

import os
import shutil
import pytest
from market_intelligence.primitives import Candle
from research.experiments.matrix_runner import MatrixRunner, ASSETS
from research.experiments.trailing_ab_experiment import TrailingABExperiment
from research.replayer.timeframe_aligner import CANONICAL_TIMEFRAME_SETS
from research.exporters.artifact_exporter import ArtifactExporter


def generate_candles(count: int, start_ts: int = 1000, step_ms: int = 60000, base_price: float = 100.0):
    candles = []
    p = base_price
    for i in range(count):
        delta = 2.0 if i % 2 == 0 else -1.0
        p += delta
        candles.append(Candle(
            timestamp=start_ts + (i * step_ms),
            open=p - delta,
            high=p + 3.0,
            low=p - 3.0,
            close=p,
            volume=50.0 + i
        ))
    return candles


@pytest.fixture
def temp_results_dir(tmp_path):
    out_dir = str(tmp_path / "research_results")
    yield out_dir
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)


def test_24_baseline_matrix_and_trailing_ab_integration(temp_results_dir):
    exporter = ArtifactExporter(output_dir=temp_results_dir)
    matrix_runner = MatrixRunner(exporter=exporter)
    trailing_ab = TrailingABExperiment(exporter=exporter)

    # Build multi-timeframe dataset fixture for BTC, ETH, SOL
    dataset: dict = {}
    timeframes = ["1M", "1W", "1D", "4H", "1H", "15M"]

    for asset in ASSETS:
        base_p = 50000.0 if asset == "BTC" else (3000.0 if asset == "ETH" else 150.0)
        dataset[asset] = {}
        for tf in timeframes:
            dataset[asset][tf] = generate_candles(30, start_ts=0, step_ms=3600000, base_price=base_p)

    # 1. Run 24-Baseline Matrix
    matrix_results = matrix_runner.run_matrix(
        dataset_by_asset_tf=dataset,
        initial_balance=10000.0,
        enable_mtf_trailing=True
    )

    # Assert matrix execution completed across streams
    assert len(matrix_results) > 0

    # 2. Run Trailing A/B Experiment on BTC SET_4
    btc_4h = dataset["BTC"]["4H"]
    btc_1h = dataset["BTC"]["1H"]
    btc_15m = dataset["BTC"]["15M"]

    ab_report = trailing_ab.run_comparison(
        asset="BTC",
        timeframe_set_id="SET_4",
        htf_candles=btc_4h,
        mtf_candles=btc_1h,
        ltf_candles=btc_15m,
        initial_balance=10000.0
    )

    assert "baseline_a_no_trail" in ab_report
    assert "baseline_b_with_trail" in ab_report
    assert "deltas" in ab_report

    # 3. Assert artifacts were created in results directory
    exported_files = [f for f in os.listdir(temp_results_dir) if f.endswith(".json")]
    assert len(exported_files) > 0
