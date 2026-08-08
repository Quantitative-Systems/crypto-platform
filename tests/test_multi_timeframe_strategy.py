import unittest

from market_intelligence.primitives import (
    Candle,
    EngineMetadata,
    EventType,
    KeyZone,
    MarketEvent,
    MarketPhase,
    MarketStatePayload,
    PhaseState,
    StructureState,
    TrendDirection,
    TrendState,
    TrendStrength,
    ValuationState,
    ValidationScorecard,
    ZoneType,
    ZoneState,
)
from strategy.htf_bias import HTFBiasEngine
from strategy.ltf_trigger import LTFTriggerEngine
from strategy.mtf_setup import MTFSetupEngine
from strategy.orchestrator import StrategyOrchestrator
from strategy.strategy_a_pullback import StrategyAPullbackEngine
from strategy.strategy_b_continuation import StrategyBContinuationEngine


class TestMultiTimeframeStrategy(unittest.TestCase):
    def _build_payload(self, *, trend, phase, current_price, keyzones=None, last_event=None):
        candle = Candle(timestamp=1, open=current_price, high=current_price + 1, low=current_price - 1, close=current_price, volume=1000.0)
        structure_state = StructureState(
            external_trend_seq="HH-HL" if trend == TrendDirection.BULLISH else "LH-LL",
            internal_trend_seq="HH-HL" if trend == TrendDirection.BULLISH else "LH-LL",
            external_trend=trend,
            internal_trend=trend,
            protected_high=None,
            protected_low=None,
        )
        trend_state = TrendState(
            direction=trend,
            strength=TrendStrength.STRONG_BULLISH if trend == TrendDirection.BULLISH else TrendStrength.STRONG_BEARISH,
            confidence=0.8,
            reasoning="trend",
            latest_high_label=None,
            latest_low_label=None,
            timestamp=1,
            timeframe="1D",
            external_trend=trend,
            internal_trend=trend,
            trend_strength=0.85,
            trend_age_bars=1,
            is_aligned=True,
        )
        phase_state = PhaseState(current_phase=phase, expected_next_phase=MarketPhase.CONTINUATION, bars_in_phase=1)
        valuation_state = ValuationState(
            range_high=current_price + 10,
            range_low=current_price - 10,
            equilibrium=current_price,
            premium_boundary=current_price + 1,
            discount_boundary=current_price - 1,
            current_distance_from_eq=0.0,
        )
        scorecard = ValidationScorecard(
            structure_score=80.0,
            liquidity_score=80.0,
            zone_score=80.0,
            trend_score=80.0,
            phase_score=80.0,
            validation_score=80.0,
        )
        return MarketStatePayload(
            symbol="BTC/USDT",
            timeframe="1D",
            timestamp=1,
            current_price=current_price,
            current_candle=candle,
            events=[last_event] if last_event else [],
            swings=[],
            structure_state=structure_state,
            liquidity_pools=[],
            keyzones=keyzones or [],
            phase_state=phase_state,
            trend_state=trend_state,
            valuation_state=valuation_state,
            scorecard=scorecard,
            metadata=EngineMetadata(engine_version="test", processing_time_ms=0.0, confidence=0.8),
            zone_state=ZoneState(active_keyzones=keyzones or []),
        )

    def test_pullback_strategy_alignment(self):
        htf_state = self._build_payload(
            trend=TrendDirection.BULLISH,
            phase=MarketPhase.PULLBACK,
            current_price=100.0,
            last_event=MarketEvent(timestamp=1, timeframe="1D", symbol="BTC/USDT", event_type=EventType.EXTERNAL_BOS, price_level=99.0, metadata={"direction": "BULLISH"}),
        )
        mtf_state = self._build_payload(
            trend=TrendDirection.BULLISH,
            phase=MarketPhase.CONTINUATION,
            current_price=100.0,
            keyzones=[KeyZone(zone_type=ZoneType.BULLISH_FVG, direction=TrendDirection.BULLISH, high=101.0, low=99.0, timeframe="1D", creation_time=1, is_mitigated=False, strength_score=0.9)],
            last_event=MarketEvent(timestamp=1, timeframe="1D", symbol="BTC/USDT", event_type=EventType.EXTERNAL_BOS, price_level=98.0, metadata={"direction": "BULLISH"}),
        )

        htf_res = HTFBiasEngine.evaluate_bias(htf_state)
        self.assertTrue(htf_res.is_valid)

        strat_res = StrategyAPullbackEngine.evaluate_pullback_setup(htf_state, mtf_state)
        self.assertTrue(strat_res.is_valid_setup)
        self.assertIsNotNone(strat_res.mtf_keyzone)

    def test_continuation_strategy_with_ltf_trigger(self):
        htf_state = self._build_payload(
            trend=TrendDirection.BULLISH,
            phase=MarketPhase.CONTINUATION,
            current_price=100.0,
            last_event=MarketEvent(timestamp=1, timeframe="1D", symbol="BTC/USDT", event_type=EventType.EXTERNAL_BOS, price_level=95.0, metadata={"direction": "BULLISH"}),
        )
        mtf_state = self._build_payload(
            trend=TrendDirection.BULLISH,
            phase=MarketPhase.CONTINUATION,
            current_price=96.0,
            keyzones=[KeyZone(zone_type=ZoneType.DEMAND_OB, direction=TrendDirection.BULLISH, high=97.0, low=95.0, timeframe="1D", creation_time=1, is_mitigated=False, strength_score=0.95)],
            last_event=MarketEvent(timestamp=1, timeframe="1D", symbol="BTC/USDT", event_type=EventType.EXTERNAL_BOS, price_level=94.0, metadata={"direction": "BULLISH"}),
        )
        ltf_candle = Candle(timestamp=2, open=95.5, high=96.2, low=95.0, close=96.1, volume=5000.0)

        strat_res = StrategyBContinuationEngine.evaluate_continuation_setup(htf_state, mtf_state)
        self.assertTrue(strat_res.is_valid_setup)

        mtf_setup = MTFSetupEngine.evaluate_setup(htf_state.trend_state.direction, mtf_state)
        self.assertTrue(mtf_setup.is_aligned)

        ltf_res = LTFTriggerEngine.evaluate_entry(htf_state, ltf_candle, mtf_setup, TrendDirection.BULLISH)
        self.assertTrue(ltf_res.is_triggered)

    def test_orchestrator_approves_trade_plan(self):
        htf_state = self._build_payload(
            trend=TrendDirection.BULLISH,
            phase=MarketPhase.PULLBACK,
            current_price=100.0,
            last_event=MarketEvent(timestamp=1, timeframe="1D", symbol="BTC/USDT", event_type=EventType.EXTERNAL_BOS, price_level=98.0, metadata={"direction": "BULLISH"}),
        )
        mtf_state = self._build_payload(
            trend=TrendDirection.BULLISH,
            phase=MarketPhase.CONTINUATION,
            current_price=100.0,
            keyzones=[KeyZone(zone_type=ZoneType.BULLISH_FVG, direction=TrendDirection.BULLISH, high=101.0, low=100.0, timeframe="1D", creation_time=1, is_mitigated=False, strength_score=0.9)],
            last_event=MarketEvent(timestamp=1, timeframe="1D", symbol="BTC/USDT", event_type=EventType.EXTERNAL_BOS, price_level=98.0, metadata={"direction": "BULLISH"}),
        )
        ltf_state = self._build_payload(
            trend=TrendDirection.BULLISH,
            phase=MarketPhase.CONTINUATION,
            current_price=100.0,
            keyzones=[KeyZone(zone_type=ZoneType.BULLISH_FVG, direction=TrendDirection.BULLISH, high=101.0, low=100.0, timeframe="1D", creation_time=1, is_mitigated=False, strength_score=0.9)],
        )
        latest_candle = Candle(timestamp=2, open=99.0, high=101.0, low=98.7, close=100.8, volume=5000.0)

        plan = StrategyOrchestrator.process_pipeline(
            htf_state=htf_state,
            mtf_state=mtf_state,
            ltf_state=ltf_state,
            latest_candle=latest_candle,
            account_balance=1000.0,
            risk_pct=0.01,
            min_confluence_score=60.0,
        )

        self.assertEqual(plan.status, "APPROVED")
        self.assertEqual(plan.action, "BUY")
        self.assertGreater(plan.reward_to_risk_ratio, 4.0)


if __name__ == "__main__":
    unittest.main()
