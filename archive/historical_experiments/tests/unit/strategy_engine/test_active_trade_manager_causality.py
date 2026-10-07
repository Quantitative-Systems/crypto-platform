import pytest
from unittest.mock import MagicMock
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from strategy_engine.contracts.trade_plan import TradePlanPayload, DirectionalPermission
from strategy_engine.contracts.strategy_state import PositionState
from market_intelligence.primitives import MarketStatePayload, Candle

@pytest.fixture
def manager():
    return ActiveTradeManager(enable_mtf_trailing=True, enable_profit_lock=False)

@pytest.fixture
def sample_plan():
    plan = TradePlanPayload(
        trade_plan_id="test_trade",
        hypothesis_id="H1",
        symbol="BTCUSDT",
        directional_permission=DirectionalPermission.PERMIT_LONG.value,
        setup_timestamp=1000,
        entry_price=50000.0,
        stop_invalidation_price=48000.0,
        target_price=54000.0,
        raw_rr=2.0,
        status="ENTERED"
    )
    plan.metadata = {}
    return plan

def test_adverse_mtf_choch_causal_filtering(manager, sample_plan):
    """
    Test that a stale MTF CHOCH (occurred before setup) does NOT exit the trade,
    but a new adverse MTF CHOCH (occurred after setup) DOES exit the trade.
    """
    manager.register_trade("test_trade", sample_plan)
    
    # 1. Stale CHOCH Scenario (timestamp < setup_timestamp)
    stale_event = MagicMock()
    stale_event.event_type = "CHOCH"
    stale_event.direction = "BEARISH"
    stale_event.timestamp = 900  # Before setup_timestamp (1000)
    
    mtf_payload_stale = MagicMock()
    mtf_payload_stale.structure_state.events = [stale_event]
    del mtf_payload_stale.structure_state.protected_low
    del mtf_payload_stale.structure_state.protected_high
    
    ltf_payload = MagicMock()
    ltf_payload.current_candle = MagicMock(spec=Candle)
    ltf_payload.current_candle.high = 51000.0
    ltf_payload.current_candle.low = 49000.0
    ltf_payload.current_price = 50000.0
    ltf_payload.timestamp = 1100
    
    exited = manager.evaluate(MagicMock(), mtf_payload_stale, ltf_payload)
    
    assert len(exited) == 0
    assert "test_trade" in manager.active_trades
    assert sample_plan.position_status == PositionState.ACTIVE_POSITION.value
    
    # 2. Fresh Adverse CHOCH Scenario (timestamp > setup_timestamp)
    fresh_event = MagicMock()
    fresh_event.event_type = "CHOCH"
    fresh_event.direction = "BEARISH"
    fresh_event.timestamp = 1050  # After setup_timestamp (1000)
    
    mtf_payload_fresh = MagicMock()
    mtf_payload_fresh.structure_state.events = [fresh_event]
    del mtf_payload_fresh.structure_state.protected_low
    del mtf_payload_fresh.structure_state.protected_high
    mtf_payload_fresh.timestamp = 1100
    
    exited = manager.evaluate(MagicMock(), mtf_payload_fresh, ltf_payload)
    
    assert len(exited) == 1
    assert "test_trade" not in manager.active_trades
    assert exited[0].position_status == PositionState.MTF_TRAIL_EXIT.value
    assert exited[0].exit_timestamp == mtf_payload_fresh.timestamp

def test_tp_sl_evaluation_uses_intrabar_extremes(manager, sample_plan):
    """
    Test that the ActiveTradeManager evaluates TP/SL using intrabar high/low,
    rather than candle close (current_price).
    """
    manager.register_trade("test_trade", sample_plan)
    
    mtf_payload = MagicMock()
    mtf_payload.structure_state.events = []
    mtf_payload.events = []
    del mtf_payload.structure_state.protected_low
    del mtf_payload.structure_state.protected_high
    
    ltf_payload = MagicMock()
    ltf_payload.current_candle = MagicMock(spec=Candle)
    ltf_payload.current_candle.high = 54000.0  # Hits TP
    ltf_payload.current_candle.low = 50000.0
    ltf_payload.current_price = 52000.0  # Does NOT hit TP
    ltf_payload.timestamp = 1200
    
    exited = manager.evaluate(MagicMock(), mtf_payload, ltf_payload)
    
    # The trade should exit due to the high hitting TP, even though close did not.
    assert len(exited) == 1
    assert "test_trade" not in manager.active_trades
    assert exited[0].position_status == PositionState.TP_EXIT.value

    # Reset and test SL
    sample_plan.position_status = PositionState.ACTIVE_POSITION.value
    manager.register_trade("test_trade_sl", sample_plan)
    
    ltf_payload.current_candle.high = 52000.0
    ltf_payload.current_candle.low = 47500.0  # Hits SL (48000)
    ltf_payload.current_price = 49000.0  # Does NOT hit SL
    
    exited = manager.evaluate(MagicMock(), mtf_payload, ltf_payload)
    
    assert len(exited) == 1
    assert "test_trade_sl" not in manager.active_trades
    assert exited[0].position_status == PositionState.LTF_SL_EXIT.value
