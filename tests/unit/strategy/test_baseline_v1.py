"""Unit tests for BaselineStrategyHypothesisV1."""
import numpy as np

from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    StructuralBreak,
    StructuralBreakType,
    StructureSnapshot,
    SwingPoint,
    TrendDirection,
    ZonesSnapshot,
)
from strategy.base import CandidateSignal, StrategyHypothesis
from strategy.baseline_v1 import BaselineStrategyHypothesisV1


def test_baseline_strategy_hypothesis_v1_evaluation():
    strategy = BaselineStrategyHypothesisV1(
        timeframe_set_id="SET_3",
        htf_label="1D",
        mtf_label="4H",
        ltf_label="1H",
        hypothesis_type="CONTINUATION",
        min_target_r=4.0,
    )

    # 1. Test HTF Evaluation
    htf_bullish = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1000,
        timeframe="1D",
        close_price=60000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BULLISH),
    )
    dir_bias = strategy.evaluate_htf(htf_bullish)
    assert dir_bias == 1

    htf_bearish = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1000,
        timeframe="1D",
        close_price=60000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BEARISH),
    )
    dir_bias = strategy.evaluate_htf(htf_bearish)
    assert dir_bias == -1

    # 2. Test MTF Validation
    mtf_discount = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=2000,
        timeframe="4H",
        close_price=58000.0,
        zones=ZonesSnapshot(premium_discount_zone="DISCOUNT"),
    )
    assert strategy.validate_mtf(mtf_discount, direction=1) is True
    assert strategy.validate_mtf(mtf_discount, direction=-1) is False

    # 3. Test LTF Confirmation
    ltf_state = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=3000,
        timeframe="1H",
        close_price=58500.0,
        structure=StructureSnapshot(
            last_minor_low=SwingPoint(timestamp_ms=2500, price=58000.0, is_high=False),
            recent_breaks=[
                StructuralBreak(
                    timestamp_ms=2900,
                    break_type=StructuralBreakType.BOS_BULLISH,
                    trigger_price=58400.0,
                    broken_swing_price=58300.0,
                )
            ],
        ),
    )
    confirmed, sl, tp = strategy.confirm_ltf_entry(ltf_state, direction=1)
    assert confirmed is True
    assert sl is not None and sl < 58500.0
    assert tp is not None and tp > 58500.0
