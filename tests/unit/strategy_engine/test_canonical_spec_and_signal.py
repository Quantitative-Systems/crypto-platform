"""
Unit tests for CanonicalStrategySpec and CanonicalSignalEngine.
"""

import pytest
from datetime import datetime, timezone
from market_intelligence.primitives import Candle
from platform_core.canonical_strategy_spec import (
    CanonicalStrategySpec,
    create_fam07_spec,
    StrategyLifecycleState,
)
from strategy_engine.canonical_signal_engine import CanonicalSignalEngine


def test_canonical_strategy_spec_serialization():
    spec = create_fam07_spec(
        symbol="SOLUSDT",
        timeframe_set=2,
        lifecycle_state=StrategyLifecycleState.QUALIFIED_ROBUST,
    )
    assert spec.strategy_id == "FAM-07-MTFCONT_SOLUSDT_Set2"
    assert spec.family_id == "FAM-07-MTFCONT"
    assert spec.parameters["tp_r"] == 2.5
    assert spec.parameters["ema_len"] == 21

    # Round-trip JSON test
    json_str = spec.to_json()
    reconstructed = CanonicalStrategySpec.from_json(json_str)

    assert reconstructed.strategy_id == spec.strategy_id
    assert reconstructed.family_id == spec.family_id
    assert reconstructed.lifecycle_state == StrategyLifecycleState.QUALIFIED_ROBUST
    assert reconstructed.parameters == spec.parameters
    assert reconstructed.rules == spec.rules
    assert reconstructed.validate() is True


def test_canonical_signal_engine_generation():
    spec = create_fam07_spec("SOLUSDT", 2)
    engine = CanonicalSignalEngine(spec)

    # Generate synthetic candle series where HTF is bullish, MTF is bullish, and LTF breaks out
    def make_candle(ts, close, high=None, low=None):
        h = high if high is not None else close + 1.0
        l = low if low is not None else close - 1.0
        return Candle(
            timestamp=ts,
            open=close,
            high=h,
            low=l,
            close=close,
            volume=1000.0,
        )

    # Generate synthetic candle series ending at evaluation time T_eval
    T_eval = 1700000000000
    # 40 HTF candles (1W) preceding T_eval steadily ascending
    htf_candles = [make_candle(T_eval - (40 - i) * 604800000, 90.0 + i * 2.0) for i in range(40)]
    # 40 MTF candles (1D) preceding T_eval steadily ascending
    mtf_candles = [make_candle(T_eval - (40 - i) * 86400000, 95.0 + i * 1.0) for i in range(40)]
    # 60 LTF candles (4H) ending at T_eval steadily ascending
    ltf_candles = [make_candle(T_eval - (60 - i) * 14400000, 100.0 + i * 0.5) for i in range(59)]
    # Final candle breaks out sharply above Donchian channel
    ltf_candles.append(make_candle(T_eval, 135.0, high=136.0, low=134.0))

    signal = engine.generate_signal_at_bar(ltf_candles, mtf_candles, htf_candles, bar_idx=-1)

    assert signal is not None
    assert signal.action == "BUY"
    assert signal.symbol == "SOLUSDT"
    assert signal.strategy_id == "FAM-07-MTFCONT_SOLUSDT_Set2"
    assert signal.entry_price == ltf_candles[-1].close
    assert signal.stop_loss < signal.entry_price
    assert signal.take_profit > signal.entry_price
    assert signal.tp_r == 2.5
