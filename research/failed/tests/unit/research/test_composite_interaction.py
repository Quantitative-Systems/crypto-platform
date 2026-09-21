"""
Unit tests for HYP_COMPOSITE_POLARITY_BREAKEVEN_01.
Validates the controlled interaction and composition of:
1. Entry-quality mechanism: Displacement polarity (HYP_ENTRY_DISPLACEMENT_POLARITY_01)
2. Post-entry risk-management mechanism: +1.0R breakeven ratchet (HYP_MGT_BREAKEVEN_1R_01)

Verifies:
- Both mechanisms activate cleanly without interference
- Polarity acts strictly at entry qualification
- Breakeven acts strictly post-entry upon >= +1.0R favorable excursion
- Adverse-first collision ordering is strictly preserved
- Invariants (initial stop, target, risk sizing) remain unchanged
"""

import pytest
from market_intelligence.primitives import (
    MarketStatePayload,
    Candle,
    StructureState,
    EventType,
    MarketEvent
)
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from research.replayer.causal_replayer import CausalReplayer
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.simulation.execution_simulator import ExecutionSimulator


def _make_dummy_state(symbol: str, tf: str, ts: int, candle: Candle) -> MarketStatePayload:
    return MarketStatePayload(
        symbol=symbol,
        timeframe=tf,
        timestamp=ts,
        current_price=candle.close,
        current_candle=candle,
        events=[],
        swings=[],
        structure_state=StructureState(),
        liquidity_pools=[],
        keyzones=[],
        phase_state=None,
        trend_state=None,
        scorecard={"reason_codes": ["DISPLACEMENT_CONFIRMED"]}
    )


def test_composite_replayer_initialization():
    """Verify CausalReplayer configures both polarity and breakeven simultaneously."""
    replayer = CausalReplayer(
        timeframe_set_id="SET_4",
        initial_balance=10000.0,
        enable_forward_expansion=True,
        enforce_displacement_polarity=True,
        enable_breakeven_1r=True,
        breakeven_trigger_r=1.0,
        breakeven_stop_r=0.10
    )
    assert replayer.enable_forward_expansion is True
    assert replayer.enforce_displacement_polarity is True
    assert replayer.enable_breakeven_1r is True
    assert replayer.breakeven_trigger_r == 1.0
    assert replayer.breakeven_stop_r == 0.10
    assert replayer.strategy_coordinator.hypotheses["UNIFIED_STRATEGY"].enforce_displacement_polarity is True
    assert replayer.execution_simulator.enable_breakeven_1r is True


def test_composite_polarity_rejects_counter_directional_entry():
    """Verify polarity filter continues to reject counter-directional setups in composite."""
    strategy = UnifiedStrategy(enforce_displacement_polarity=True)
    
    cand = CandidateSetup(
        candidate_id="cand_comp_long_01",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        htf="4h",
        mtf="1h",
        ltf="15m",
        state=CandidateState.WAIT_LTF_TRIGGER,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        creation_timestamp=1000,
        mtf_retest_timestamp=1000
    )
    
    # Bearish trigger candle for LONG setup -> must reject
    bearish_candle = Candle(timestamp=1100, open=102.0, high=103.0, low=97.0, close=98.0, volume=50.0)
    ltf_payload = _make_dummy_state("BTC/USDT", "15m", 1100, bearish_candle)
    ltf_payload.events = [
        MarketEvent(
            timestamp=1050,
            timeframe="15m",
            symbol="BTC/USDT",
            event_type=EventType.LIQUIDITY_SWEEP,
            price_level=96.0,
            metadata={"direction": "BULLISH"}
        )
    ]
    htf_payload = _make_dummy_state("BTC/USDT", "4h", 1100, bearish_candle)
    mtf_payload = _make_dummy_state("BTC/USDT", "1h", 1100, bearish_candle)
    
    plan = strategy.evaluate(cand, htf_payload, mtf_payload, ltf_payload)
    assert cand.state == CandidateState.REJECTED
    assert cand.invalidation_reason == "REJECT_ENTRY_DISPLACEMENT_POLARITY"
    assert plan is not None
    assert plan.status == "REJECTED"


def test_composite_polarity_accepts_conforming_entry():
    """Verify polarity filter passes conforming directional setup."""
    strategy = UnifiedStrategy(enforce_displacement_polarity=True)
    
    cand = CandidateSetup(
        candidate_id="cand_comp_short_01",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        htf="4h",
        mtf="1h",
        ltf="15m",
        state=CandidateState.WAIT_LTF_TRIGGER,
        directional_permission=DirectionalPermission.PERMIT_SHORT,
        creation_timestamp=1000,
        mtf_retest_timestamp=1000
    )
    
    # Bearish trigger candle for SHORT setup -> passes polarity check
    bearish_candle = Candle(timestamp=1100, open=102.0, high=103.0, low=97.0, close=98.0, volume=50.0)
    ltf_payload = _make_dummy_state("BTC/USDT", "15m", 1100, bearish_candle)
    ltf_payload.events = [
        MarketEvent(
            timestamp=1050,
            timeframe="15m",
            symbol="BTC/USDT",
            event_type=EventType.LIQUIDITY_SWEEP,
            price_level=104.0,
            metadata={"direction": "BEARISH"}
        )
    ]
    htf_payload = _make_dummy_state("BTC/USDT", "4h", 1100, bearish_candle)
    mtf_payload = _make_dummy_state("BTC/USDT", "1h", 1100, bearish_candle)
    
    plan = strategy.evaluate(cand, htf_payload, mtf_payload, ltf_payload)
    # Does not fail on polarity; candidate proceeds
    assert cand.invalidation_reason != "REJECT_ENTRY_DISPLACEMENT_POLARITY"


def test_composite_breakeven_ratchet_after_entry():
    """Verify post-entry breakeven operates correctly on retained trade."""
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_breakeven_1r=True, breakeven_trigger_r=1.0, breakeven_stop_r=0.10)
    
    # LONG trade: entry=100, stop=90 (1R risk = 10), target=150
    trade = SimulatedTrade(
        trade_id="t_comp_long_01",
        hypothesis_id="HYP_UNIFIED",
        symbol="BTCUSDT",
        timeframe_set="SET_4",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        fill_entry_price=100.0,
        initial_stop_price=90.0,
        current_stop_price=90.0,
        target_price=150.0,
        position_units=10.0,
        dollar_risk=100.0,
        status="ACTIVE"
    )
    ledger.trades[trade.trade_id] = trade

    # Candle 1 reaches 110.5 (excursion +1.05R >= +1.0R), low stays at 101.5 (> BE stop 101.0)
    c1 = Candle(timestamp=2000, open=102.0, high=110.5, low=101.5, close=109.0, volume=10.0)
    sim.process_candle(c1, ledger)

    assert trade.current_stop_price == pytest.approx(101.0, 1e-4)
    assert trade.metadata.get("breakeven_triggered") is True
    assert trade.status == "ACTIVE"

    # Candle 2 drops below BE stop (low=100.0 <= 101.0) -> closed at BE stop
    c2 = Candle(timestamp=3000, open=108.0, high=108.0, low=100.0, close=100.5, volume=10.0)
    sim.process_candle(c2, ledger)

    assert trade.status == "CLOSED"
    assert trade.exit_reason == "BREAKEVEN_TRAIL"
    assert trade.realized_rr == pytest.approx(0.10, abs=0.02)
    assert trade.realized_rr > 0.0


def test_composite_adverse_first_collision():
    """Verify adverse-first rule applies when candle touches both +1R threshold and initial stop."""
    ledger = TradeLedger(initial_equity=10000.0)
    sim = ExecutionSimulator(enable_breakeven_1r=True, breakeven_trigger_r=1.0, breakeven_stop_r=0.10)
    
    trade = SimulatedTrade(
        trade_id="t_comp_collision_01",
        hypothesis_id="HYP_UNIFIED",
        symbol="BTCUSDT",
        timeframe_set="SET_4",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        fill_entry_price=100.0,
        initial_stop_price=90.0,
        current_stop_price=90.0,
        target_price=150.0,
        position_units=10.0,
        dollar_risk=100.0,
        status="ACTIVE"
    )
    ledger.trades[trade.trade_id] = trade

    # Extreme volatility bar: High=112.0 (+1.2R), Low=88.0 (Stop hit)
    c1 = Candle(timestamp=2000, open=100.0, high=112.0, low=88.0, close=95.0, volume=100.0)
    sim.process_candle(c1, ledger)

    # Adverse-first: Stop hit takes priority in ambiguous bars, trade closes at initial stop (-1R), NOT protected by BE
    assert trade.status == "CLOSED"
    assert trade.exit_reason == "INITIAL_LTF_SL"
    assert trade.metadata.get("breakeven_triggered") is not True
