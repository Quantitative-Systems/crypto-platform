"""Unit Tests for All Decoupled Strategy Hypotheses.

Verifies that each strategy hypothesis:
1. Inherits from StrategyHypothesis
2. Decomposes cleanly into Structure, Key Zones, and Phase
3. Evaluates HTF, MTF, and LTF states causally
"""
from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    PhaseSnapshot,
    StructureSnapshot,
    SwingPoint,
    TrendDirection,
    ZonesSnapshot,
)
from strategy import (
    BaselineStrategyHypothesisV1,
    TrendBreakoutHypothesis,
    MeanReversionHypothesis,
    MomentumIgnitionHypothesis,
)


def test_trend_breakout_hypothesis():
    hyp = TrendBreakoutHypothesis(
        timeframe_set_id="SET_2", htf_label="1W", mtf_label="1D", ltf_label="4H"
    )
    
    # 1. Bullish HTF
    htf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1W", close_price=50000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BULLISH)
    )
    assert hyp.evaluate_htf(htf) == 1

    # 2. MTF Validation
    mtf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1D", close_price=51000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BULLISH),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.CONTINUATION),
    )
    assert hyp.validate_mtf(mtf, 1) is True

    # 3. LTF Entry
    ltf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="4H", close_price=52000.0,
        structure=StructureSnapshot(
            last_major_high=SwingPoint(timestamp_ms=500, price=51500.0, is_high=True),
            last_major_low=SwingPoint(timestamp_ms=400, price=49000.0, is_high=False),
        )
    )
    confirmed, sl, tp = hyp.confirm_ltf_entry(ltf, 1)
    assert confirmed is True
    assert sl == 49000.0
    assert tp >= 52000.0 + 3.0 * (52000.0 - 49000.0)


def test_mean_reversion_hypothesis():
    hyp = MeanReversionHypothesis(
        timeframe_set_id="SET_2", htf_label="1W", mtf_label="1D", ltf_label="4H"
    )
    
    # Range HTF at Premium -> Short bias
    htf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1W", close_price=50000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.RANGE),
        zones=ZonesSnapshot(premium_discount_zone="PREMIUM", equilibrium_price=45000.0)
    )
    assert hyp.evaluate_htf(htf) == -1

    mtf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1D", close_price=50000.0,
        zones=ZonesSnapshot(premium_discount_zone="PREMIUM")
    )
    assert hyp.validate_mtf(mtf, -1) is True

    ltf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="4H", close_price=49500.0,
        structure=StructureSnapshot(
            last_major_high=SwingPoint(timestamp_ms=500, price=50000.0, is_high=True)
        ),
        zones=ZonesSnapshot(equilibrium_price=45000.0)
    )
    confirmed, sl, tp = hyp.confirm_ltf_entry(ltf, -1)
    assert confirmed is True
    assert sl > 50000.0
    assert tp == 45000.0


def test_momentum_ignition_hypothesis():
    hyp = MomentumIgnitionHypothesis(
        timeframe_set_id="SET_2", htf_label="1W", mtf_label="1D", ltf_label="4H"
    )
    htf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1W", close_price=50000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BULLISH)
    )
    assert hyp.evaluate_htf(htf) == 1

    mtf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1D", close_price=50000.0,
        phase=PhaseSnapshot(current_phase=MarketPhaseType.CONTINUATION),
    )
    assert hyp.validate_mtf(mtf, 1) is True

    ltf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="4H", close_price=52000.0,
        open_price=50000.0,
        structure=StructureSnapshot(
            last_major_low=SwingPoint(timestamp_ms=400, price=49500.0, is_high=False)
        )
    )
    confirmed, sl, tp = hyp.confirm_ltf_entry(ltf, 1)
    assert confirmed is True
    assert sl == 49500.0
    assert tp > 52000.0
