"""Unit tests for Phase R Execution Adapters and Fatal Safety Barrier."""
import pytest
from execution.adapters.execution_adapters import (
    FatalSafetyError,
    LiveAdapter,
    OrderIntent,
    PaperAdapter,
    ShadowAdapter,
)


def test_shadow_adapter_simulates_realistic_fills():
    adapter = ShadowAdapter(taker_fee_bps=10.0, slippage_bps=4.0, spread_bps=1.5)
    intent = OrderIntent(
        intent_id="INT_TEST_001",
        decision_id="DEC_001",
        symbol="BTCUSDT",
        direction=1,
        entry_price=60000.0,
        initial_stop_price=59000.0,
        target_price=64000.0,
        planned_r=4.0,
        risk_usd=1000.0,
        size_units=1.0,
        created_at_ts=1700000000000,
    )

    fill = adapter.submit_order(intent)
    assert fill.intent_id == "INT_TEST_001"
    assert fill.symbol == "BTCUSDT"
    assert not fill.is_live
    # Long fill must experience adverse slippage & spread crossing
    assert fill.fill_price > 60000.0
    assert fill.fee_usd > 0.0


def test_live_adapter_strictly_fails_closed():
    adapter = LiveAdapter()
    intent = OrderIntent(
        intent_id="INT_TEST_002",
        decision_id="DEC_002",
        symbol="ETHUSDT",
        direction=-1,
        entry_price=3000.0,
        initial_stop_price=3100.0,
        target_price=2600.0,
        planned_r=4.0,
        risk_usd=1000.0,
        size_units=10.0,
        created_at_ts=1700000000000,
    )

    with pytest.raises(FatalSafetyError, match="FATAL SECURITY VIOLATION"):
        adapter.submit_order(intent)

    with pytest.raises(FatalSafetyError, match="FATAL SECURITY VIOLATION"):
        adapter.close_position("ETHUSDT", 2800.0, "TAKE_PROFIT")
