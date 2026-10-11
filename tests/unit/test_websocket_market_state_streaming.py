"""Unit tests for Market State WebSocket Streaming and Event Contract.

Tests:
1. MarketStateEvent serialization, deserialization, and schema validation.
2. EventSequenceGuard causal closed-candle validation, monotonicity, duplicate and out-of-order rejection.
3. REST endpoints for /api/markets/{symbol}/five-set-ladder and parity-audit.
4. WebSocket handshake, initial STATE_SNAPSHOT, ping/pong heartbeat, resync, and broadcast.
"""
import json
import pytest
from datetime import datetime, timezone
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from market_data.realtime.event_contract import (
    MarketStateEvent,
    MarketEventType,
    EventSequenceGuard,
)
from execution.autonomous_supervisor import AutonomousTradingSupervisor
from web.server import PhaseRWebServer


@pytest.fixture
def supervisor():
    return AutonomousTradingSupervisor(symbols=["BTCUSDT"])


@pytest.fixture
def server(supervisor):
    return PhaseRWebServer(supervisor=supervisor)


def test_market_state_event_serialization():
    event = MarketStateEvent(
        event_type=MarketEventType.STATE_SNAPSHOT.value,
        sequence_id=1,
        state_version="2.2.0",
        timestamp_utc="2026-10-10T12:00:00Z",
        asset="BTCUSDT",
        timeframe="4H",
        closed_candle_ts=1791550800000,
        is_closed_candle=True,
        current_price=64120.50,
        structure="BULLISH",
        phase="PULLBACK",
        key_zone="DISCOUNT",
        support_level=62500.0,
        resistance_level=65000.0,
        premium_discount="DISCOUNT",
        confidence_score=0.85,
        alignment="FULLY_ALIGNED",
        active_sets=["SET_2"],
        production_eligible=True,
        data_freshness_ms=120,
        metadata={"set_name": "SET_2"},
    )

    d = event.to_dict()
    assert d["event_type"] == "STATE_SNAPSHOT"
    assert d["asset"] == "BTCUSDT"
    assert d["is_closed_candle"] is True

    json_str = event.to_json()
    roundtrip = MarketStateEvent.from_json(json_str)
    assert roundtrip.asset == "BTCUSDT"
    assert roundtrip.sequence_id == 1
    assert roundtrip.production_eligible is True
    assert roundtrip.confidence_score == 0.85


def test_event_sequence_guard_causality_and_ordering():
    guard = EventSequenceGuard()

    # 1. Reject unclosed / partial candles
    unclosed_event = MarketStateEvent(
        event_type=MarketEventType.CANDLE_CLOSED.value,
        sequence_id=1,
        state_version="2.2.0",
        timestamp_utc="2026-10-10T12:00:00Z",
        asset="BTCUSDT",
        timeframe="1H",
        closed_candle_ts=1791550800000,
        is_closed_candle=False,  # Partial candle!
        current_price=64120.50,
        structure="BULLISH",
        phase="CONTINUATION",
        key_zone="DISCOUNT",
        support_level=63000.0,
        resistance_level=65000.0,
        premium_discount="DISCOUNT",
        confidence_score=0.70,
        alignment="FULLY_ALIGNED",
        active_sets=["SET_3"],
        production_eligible=True,
        data_freshness_ms=50,
    )
    accepted, reason = guard.validate_event(unclosed_event)
    assert accepted is False
    assert "validated closed candle" in reason

    # 2. Accept initial valid closed event
    evt1 = MarketStateEvent(
        event_type=MarketEventType.CANDLE_CLOSED.value,
        sequence_id=1,
        state_version="2.2.0",
        timestamp_utc="2026-10-10T12:00:00Z",
        asset="BTCUSDT",
        timeframe="1H",
        closed_candle_ts=1791550800000,
        is_closed_candle=True,
        current_price=64120.50,
        structure="BULLISH",
        phase="CONTINUATION",
        key_zone="DISCOUNT",
        support_level=63000.0,
        resistance_level=65000.0,
        premium_discount="DISCOUNT",
        confidence_score=0.70,
        alignment="FULLY_ALIGNED",
        active_sets=["SET_3"],
        production_eligible=True,
        data_freshness_ms=50,
    )
    accepted, reason = guard.validate_event(evt1)
    assert accepted is True
    assert reason is None

    # 3. Reject duplicate sequence ID / timestamp
    accepted_dup, reason_dup = guard.validate_event(evt1)
    assert accepted_dup is False
    assert "REJECTED_DUPLICATE" in reason_dup
    assert guard.duplicate_count >= 1

    # 4. Reject out-of-order sequence ID (older timestamp)
    evt_old = MarketStateEvent(
        event_type=MarketEventType.CANDLE_CLOSED.value,
        sequence_id=0,
        state_version="2.2.0",
        timestamp_utc="2026-10-10T11:00:00Z",
        asset="BTCUSDT",
        timeframe="1H",
        closed_candle_ts=1791547200000,
        is_closed_candle=True,
        current_price=63900.00,
        structure="BULLISH",
        phase="CONTINUATION",
        key_zone="DISCOUNT",
        support_level=63000.0,
        resistance_level=65000.0,
        premium_discount="DISCOUNT",
        confidence_score=0.70,
        alignment="FULLY_ALIGNED",
        active_sets=["SET_3"],
        production_eligible=True,
        data_freshness_ms=50,
    )
    accepted_old, reason_old = guard.validate_event(evt_old)
    assert accepted_old is False
    assert "REJECTED_OUT_OF_ORDER" in reason_old
    assert guard.out_of_order_count >= 1

    # 5. Accept monotonically increasing sequence ID & timestamp
    evt2 = MarketStateEvent(
        event_type=MarketEventType.CANDLE_CLOSED.value,
        sequence_id=2,
        state_version="2.2.0",
        timestamp_utc="2026-10-10T13:00:00Z",
        asset="BTCUSDT",
        timeframe="1H",
        closed_candle_ts=1791554400000,
        is_closed_candle=True,
        current_price=64400.00,
        structure="BULLISH",
        phase="CONTINUATION",
        key_zone="DISCOUNT",
        support_level=63200.0,
        resistance_level=65500.0,
        premium_discount="DISCOUNT",
        confidence_score=0.72,
        alignment="FULLY_ALIGNED",
        active_sets=["SET_3"],
        production_eligible=True,
        data_freshness_ms=30,
    )
    accepted2, reason2 = guard.validate_event(evt2)
    assert accepted2 is True


@pytest.mark.asyncio
async def test_rest_five_set_endpoints(server):
    async with TestClient(TestServer(server.app)) as client:
        # 1. Five-set ladder endpoint
        resp = await client.get("/api/markets/BTCUSDT/five-set-ladder")
        assert resp.status == 200
        ladder = await resp.json()
        assert ladder["symbol"] == "BTCUSDT"
        assert len(ladder["sets"]) == 5
        assert "SET_1" in ladder["sets"]
        assert "SET_5" in ladder["sets"]

        # 2. Parity audit endpoint
        resp_parity = await client.get("/api/markets/BTCUSDT/parity-audit")
        assert resp_parity.status == 200
        parity = await resp_parity.json()
        assert parity["symbol"] == "BTCUSDT"
        assert parity["verified"] is True
        assert parity["sets_count"] == 5
        assert parity["timeframes_count"] == 7


@pytest.mark.asyncio
async def test_websocket_market_state_stream(server):
    async with TestClient(TestServer(server.app)) as client:
        ws = await client.ws_connect("/ws/market-state")
        assert not ws.closed

        # 1. Verify initial state snapshot received
        msg = await ws.receive_json()
        assert msg["event_type"] == "STATE_SNAPSHOT"
        assert msg["asset"] == "UNIVERSE"
        assert msg["state_version"] == "2.2.0"
        meta = msg["metadata"]
        assert "markets" in meta
        assert "BTCUSDT" in meta["markets"]
        btc_info = meta["markets"]["BTCUSDT"]
        assert btc_info["parity"]["verified"] is True
        assert len(btc_info["ladder"]["sets"]) == 5

        # 2. Ping-pong heartbeat
        await ws.send_json({"action": "ping"})
        pong_msg = await ws.receive_json()
        assert pong_msg["action"] == "pong"

        # 3. Broadcast real-time event from server
        realtime_event = MarketStateEvent(
            event_type=MarketEventType.MARKET_STATE_UPDATE.value,
            sequence_id=1,
            state_version="2.2.0",
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            asset="BTCUSDT",
            timeframe="15M",
            closed_candle_ts=int(datetime.now(timezone.utc).timestamp() * 1000),
            is_closed_candle=True,
            current_price=64250.00,
            structure="BULLISH",
            phase="CONTINUATION",
            key_zone="DISCOUNT",
            support_level=63800.0,
            resistance_level=64800.0,
            premium_discount="DISCOUNT",
            confidence_score=0.88,
            alignment="FULLY_ALIGNED",
            active_sets=["SET_4"],
            production_eligible=True,
            data_freshness_ms=45,
        )
        await server.broadcast_market_event(realtime_event)

        broadcast_msg = await ws.receive_json()
        assert broadcast_msg["event_type"] == "MARKET_STATE_UPDATE"
        assert broadcast_msg["asset"] == "BTCUSDT"
        assert broadcast_msg["sequence_id"] == 1
        assert broadcast_msg["confidence_score"] == 0.88

        # 4. Request snapshot resync
        await ws.send_json({"action": "request_resync"})
        resync_msg = await ws.receive_json()
        assert resync_msg["event_type"] == "STATE_SNAPSHOT"

        await ws.close()


def test_event_sequence_guard_adversarial_multistream_ordering():
    guard = EventSequenceGuard()

    # 1. BTCUSDT 1H event at ts=1000, seq=1
    btc_1h_1 = MarketStateEvent(
        event_type=MarketEventType.CANDLE_CLOSED.value,
        sequence_id=1,
        state_version="2.2.0",
        timestamp_utc="2026-10-10T12:00:00Z",
        asset="BTCUSDT",
        timeframe="1H",
        closed_candle_ts=1000,
        is_closed_candle=True,
        current_price=64000.0,
        structure="BULLISH",
        phase="CONTINUATION",
        key_zone="DISCOUNT",
        support_level=63000.0,
        resistance_level=65000.0,
        premium_discount="DISCOUNT",
        confidence_score=0.75,
        alignment="FULLY_ALIGNED",
        active_sets=["SET_3"],
        production_eligible=True,
        data_freshness_ms=20,
    )
    ok, err = guard.validate_event(btc_1h_1)
    assert ok is True
    assert err is None

    # 2. Interleaved BTCUSDT 15M event at ts=900, seq=1 (earlier timestamp than 1H, different timeframe)
    # Must NOT be falsely rejected by 1H's ts=1000!
    btc_15m_1 = MarketStateEvent(
        event_type=MarketEventType.CANDLE_CLOSED.value,
        sequence_id=1,
        state_version="2.2.0",
        timestamp_utc="2026-10-10T12:15:00Z",
        asset="BTCUSDT",
        timeframe="15M",
        closed_candle_ts=900,
        is_closed_candle=True,
        current_price=64050.0,
        structure="BULLISH",
        phase="CONTINUATION",
        key_zone="DISCOUNT",
        support_level=63500.0,
        resistance_level=64500.0,
        premium_discount="DISCOUNT",
        confidence_score=0.80,
        alignment="FULLY_ALIGNED",
        active_sets=["SET_4"],
        production_eligible=True,
        data_freshness_ms=15,
    )
    ok, err = guard.validate_event(btc_15m_1)
    assert ok is True, f"15M should not be suppressed by 1H: {err}"

    # 3. Interleaved ETHUSDT 1H event with IDENTICAL timestamp=1000, seq=1
    # Distinct asset stream must NOT be rejected as duplicate of BTC!
    eth_1h_1 = MarketStateEvent(
        event_type=MarketEventType.CANDLE_CLOSED.value,
        sequence_id=1,
        state_version="2.2.0",
        timestamp_utc="2026-10-10T12:00:00Z",
        asset="ETHUSDT",
        timeframe="1H",
        closed_candle_ts=1000,
        is_closed_candle=True,
        current_price=3400.0,
        structure="BULLISH",
        phase="PULLBACK",
        key_zone="EQUILIBRIUM",
        support_level=3300.0,
        resistance_level=3500.0,
        premium_discount="EQUILIBRIUM",
        confidence_score=0.70,
        alignment="HTF_MTF_ALIGNED",
        active_sets=["SET_3"],
        production_eligible=True,
        data_freshness_ms=25,
    )
    ok, err = guard.validate_event(eth_1h_1)
    assert ok is True, f"ETH 1H with identical timestamp must not be suppressed: {err}"

    # 4. Duplicate delivery on BTCUSDT 1H (same stream, same ts=1000)
    ok, err = guard.validate_event(btc_1h_1)
    assert ok is False
    assert "REJECTED_DUPLICATE" in err

    # 5. Out-of-order delivery on BTCUSDT 1H (same stream, older ts=950)
    btc_1h_old = MarketStateEvent(
        event_type=MarketEventType.CANDLE_CLOSED.value,
        sequence_id=2,
        state_version="2.2.0",
        timestamp_utc="2026-10-10T11:30:00Z",
        asset="BTCUSDT",
        timeframe="1H",
        closed_candle_ts=950,
        is_closed_candle=True,
        current_price=63900.0,
        structure="BULLISH",
        phase="CONTINUATION",
        key_zone="DISCOUNT",
        support_level=63000.0,
        resistance_level=65000.0,
        premium_discount="DISCOUNT",
        confidence_score=0.72,
        alignment="FULLY_ALIGNED",
        active_sets=["SET_3"],
        production_eligible=True,
        data_freshness_ms=30,
    )
    ok, err = guard.validate_event(btc_1h_old)
    assert ok is False
    assert "REJECTED_OUT_OF_ORDER" in err

    # 6. Monotonic advance on BTCUSDT 1H (ts=2000, seq=2)
    btc_1h_2 = MarketStateEvent(
        event_type=MarketEventType.CANDLE_CLOSED.value,
        sequence_id=2,
        state_version="2.2.0",
        timestamp_utc="2026-10-10T13:00:00Z",
        asset="BTCUSDT",
        timeframe="1H",
        closed_candle_ts=2000,
        is_closed_candle=True,
        current_price=64500.0,
        structure="BULLISH",
        phase="CONTINUATION",
        key_zone="PREMIUM",
        support_level=63500.0,
        resistance_level=65500.0,
        premium_discount="PREMIUM",
        confidence_score=0.82,
        alignment="FULLY_ALIGNED",
        active_sets=["SET_3"],
        production_eligible=True,
        data_freshness_ms=20,
    )
    ok, err = guard.validate_event(btc_1h_2)
    assert ok is True


@pytest.mark.asyncio
async def test_end_to_end_live_data_candle_to_websocket(server, supervisor):
    """
    Traces and certifies the complete runtime path:
    Candle Ingestion -> Closed-Candle Validation -> Market-State Engine ->
    Event Publication -> WebSocket Server -> Connected Client
    """
    from market_data.realtime.candle_engine import CandleRecord
    import time

    async with TestClient(TestServer(server.app)) as client:
        ws = await client.ws_connect("/ws/market-state")
        assert not ws.closed

        # Discard initial snapshot
        init_snap = await ws.receive_json()
        assert init_snap["event_type"] == "STATE_SNAPSHOT"

        # Construct and feed a validated closed candle into the supervisor
        now_ms = int(time.time() * 1000)
        closed_candle = CandleRecord(
            symbol="BTCUSDT",
            timeframe="1H",
            open_ts=now_ms - 3600000,
            close_ts=now_ms,
            open=63500.0,
            high=64200.0,
            low=63400.0,
            close=64100.0,
            volume=150.0,
            is_closed=True,
            source="WS_VALIDATED",
            ingestion_ts=now_ms,
        )

        # Trigger authoritative closed-candle processing
        supervisor._on_closed_candle_formed(closed_candle)

        # Connected client must receive authoritative MARKET_STATE_UPDATE
        msg = await ws.receive_json()
        assert msg["event_type"] == "MARKET_STATE_UPDATE"
        assert msg["asset"] == "BTCUSDT"
        assert msg["timeframe"] == "1H"
        assert msg["closed_candle_ts"] == now_ms
        assert msg["is_closed_candle"] is True
        assert msg["current_price"] == 64100.0
        assert msg["phase"] in ["CONTINUATION", "PULLBACK"]
        assert "SET_3" in msg["active_sets"]

        await ws.close()
