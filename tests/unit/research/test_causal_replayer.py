"""
Unit Tests for Product 04: Causal Replayer
"""

import pytest
from market_intelligence.primitives import Candle
from research.replayer.causal_replayer import CausalReplayer


def generate_candle_series(count: int, start_ts: int = 1000, step_ms: int = 60000, base_price: float = 100.0):
    candles = []
    p = base_price
    for i in range(count):
        # Create zigzag price action
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


def test_replayer_runs_without_exceptions_on_synthetic_data():
    replayer = CausalReplayer(timeframe_set_id="SET_4", initial_balance=10000.0)

    # 4H, 1H, 15M synthetic streams
    htf_candles = generate_candle_series(20, start_ts=0, step_ms=4 * 3600 * 1000, base_price=50000.0)
    mtf_candles = generate_candle_series(40, start_ts=0, step_ms=3600 * 1000, base_price=50000.0)
    ltf_candles = generate_candle_series(100, start_ts=0, step_ms=15 * 60 * 1000, base_price=50000.0)

    result = replayer.run(
        symbol="BTCUSDT",
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles,
        min_lookback_bars=10
    )

    assert "metrics" in result
    assert "exit_attribution" in result
    assert "failure_modes" in result
    assert "closed_trades" in result
    assert "equity_curve" in result
    assert len(result["equity_curve"]) >= 1
