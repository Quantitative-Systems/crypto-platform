"""Unit Tests for CascadingFractalCoordinator."""
import numpy as np
import pytest

from market_model.cascading_fractal_coordinator import (
    CascadingFractalCoordinator,
    MacroPhaseBaton,
)


@pytest.fixture
def mock_multi_tf_data():
    """Generates synthetic multi-timeframe series for 1M, 1w, 1d, 4h, 1h, 15m, 3m."""
    np.random.seed(42)

    def gen_series(n_bars: int, base_px: float, step_ms: int, trend: float = 0.0):
        ts = np.array([1_600_000_000_000 + i * step_ms for i in range(n_bars)], dtype=np.int64)
        close_ts = ts + step_ms - 1
        opens = np.zeros(n_bars)
        highs = np.zeros(n_bars)
        lows = np.zeros(n_bars)
        closes = np.zeros(n_bars)
        volumes = np.ones(n_bars) * 1000.0

        px = base_px
        for i in range(n_bars):
            px += trend + np.sin(i / 5.0) * (base_px * 0.01)
            op = px
            hi = px + base_px * 0.02
            lo = px - base_px * 0.02
            cl = px + base_px * 0.005
            opens[i] = op
            highs[i] = hi
            lows[i] = lo
            closes[i] = cl

        return {
            "o": opens,
            "h": highs,
            "l": lows,
            "c": closes,
            "v": volumes,
            "ts": ts,
            "close_ts": close_ts,
        }

    # 1M: 30 bars, 1w: 100 bars, 1d: 300 bars, 4h: 500 bars, 1h: 1000 bars, 15m: 2000 bars, 3m: 3000 bars
    return {
        "1M": gen_series(30, 20_000.0, 30 * 86400 * 1000, trend=500.0),
        "1w": gen_series(100, 20_000.0, 7 * 86400 * 1000, trend=100.0),
        "1d": gen_series(300, 20_000.0, 86400 * 1000, trend=20.0),
        "4h": gen_series(500, 20_000.0, 14400 * 1000, trend=5.0),
        "1h": gen_series(1000, 20_000.0, 3600 * 1000, trend=1.0),
        "15m": gen_series(2000, 20_000.0, 900 * 1000, trend=0.2),
        "3m": gen_series(3000, 20_000.0, 180 * 1000, trend=0.05),
    }


def test_coordinator_initialization():
    coordinator = CascadingFractalCoordinator(
        min_target_r=4.0,
        risk_per_trade_pct=0.01,
        account_equity_usd=100_000.0,
    )
    assert coordinator.min_target_r == 4.0
    assert coordinator.risk_per_trade_pct == 0.01
    assert coordinator.account_equity_usd == 100_000.0
    assert "1M" in coordinator.generators
    assert "15m" in coordinator.generators


def test_macro_baton_evaluation(mock_multi_tf_data):
    coordinator = CascadingFractalCoordinator()
    current_ts = int(mock_multi_tf_data["1d"]["ts"][-1])

    baton, demand_tgt, supply_tgt = coordinator.evaluate_macro_baton(
        symbol="BTCUSDT",
        current_ts=current_ts,
        all_data=mock_multi_tf_data,
    )

    assert isinstance(baton, MacroPhaseBaton)
    if baton != MacroPhaseBaton.NEUTRAL_CONSOLIDATION:
        assert demand_tgt is not None
        assert supply_tgt is not None
        assert supply_tgt > demand_tgt


def test_cascading_candidate_generation(mock_multi_tf_data):
    coordinator = CascadingFractalCoordinator(min_target_r=4.0)

    # Scan Set 2 (1w -> 1d -> 4h)
    cands_set2, trailing_set2 = coordinator.scan_cascading_candidates(
        symbol="BTCUSDT",
        target_set="SET_2",
        all_data=mock_multi_tf_data,
    )

    assert isinstance(cands_set2, list)
    assert isinstance(trailing_set2, dict)

    for cand in cands_set2:
        assert cand["target_r"] >= 4.0 - 1e-4
        assert cand["position_size_usd"] > 0
        assert cand["risk_dist"] > 0
        assert cand["reward_dist"] > 0
        if cand["direction"] == 1:
            assert cand["stop_price"] < cand["entry_price"] < cand["target_price"]
        else:
            assert cand["stop_price"] > cand["entry_price"] > cand["target_price"]
