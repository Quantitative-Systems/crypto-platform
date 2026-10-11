"""
STRATA — Canonical Versioned Market State Event Contract & Sequence Guard.

Defines the authoritative event schema broadcast over WebSockets to Web and Android
clients upon closed-candle state finalization.

Guarantees:
- Strict Causality: Only published from validated closed candles. Zero lookahead.
- Deduplication & Sequencing: Sequence IDs and closed-candle timestamp ordering.
- Parity & Multi-Scale Transparency: Includes 7-timeframe details, active set affiliations,
  and production eligibility flags.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class MarketEventType(str, Enum):
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    MARKET_STATE_UPDATE = "MARKET_STATE_UPDATE"
    CANDLE_CLOSED = "CANDLE_CLOSED"
    HEARTBEAT = "HEARTBEAT"
    DISCONNECT_WARNING = "DISCONNECT_WARNING"


@dataclass
class MarketStateEvent:
    event_type: str  # e.g., "STATE_SNAPSHOT", "MARKET_STATE_UPDATE"
    sequence_id: int
    state_version: Union[int, str]
    timestamp_utc: str
    asset: str
    timeframe: str
    closed_candle_ts: int
    is_closed_candle: bool
    current_price: float
    structure: str  # BULLISH / BEARISH / RANGE
    phase: str  # PULLBACK / CONTINUATION
    key_zone: str  # DISCOUNT / PREMIUM / EQUILIBRIUM
    support_level: float
    resistance_level: float
    premium_discount: str
    confidence_score: float
    alignment: str  # FULLY_ALIGNED / HTF_MTF_ALIGNED / etc.
    active_sets: List[str]  # e.g. ["SET_2", "SET_3", "SET_4"]
    production_eligible: bool
    data_freshness_ms: int
    feed_health: str = "DATA_HEALTHY"
    source: str = "CANONICAL_ENGINE"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MarketStateEvent:
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> MarketStateEvent:
        return cls.from_dict(json.loads(json_str))


class EventSequenceGuard:
    """
    Enforces strict scoped sequence ordering and duplicate suppression across assets and timeframes.

    Ordering Scope:
    Each stream is keyed explicitly by (asset, timeframe).
    This ensures that independent streams (e.g. BTC 15M vs BTC 1H or BTC 1H vs ETH 1H)
    maintain their own independent sequence counters and closed-candle timestamps without
    falsely suppressing interleaved events or legitimate equal timestamps across distinct streams.

    Rejects:
    1. Events derived from unclosed or partial candles (is_closed_candle == False).
    2. Closed candle timestamps <= last_closed_candle_ts for the same (asset, timeframe) stream.
    3. Sequence IDs <= last_sequence_id for the same (asset, timeframe) stream.
    """

    def __init__(self):
        # Stream key: (asset, timeframe) -> last_closed_candle_ts
        self._last_candle_ts: Dict[Tuple[str, str], int] = {}
        # Stream key: (asset, timeframe) -> last_sequence_id
        self._last_sequence: Dict[Tuple[str, str], int] = {}
        self.duplicate_count: int = 0
        self.out_of_order_count: int = 0

    def stream_key(self, event: MarketStateEvent) -> Tuple[str, str]:
        return (event.asset.upper(), event.timeframe.upper())

    def validate_event(self, event: MarketStateEvent) -> Tuple[bool, Optional[str]]:
        if not event.is_closed_candle:
            return False, "REJECTED: Event must be derived from a validated closed candle."

        key = self.stream_key(event)
        last_ts = self._last_candle_ts.get(key, -1)

        if last_ts >= 0 and event.closed_candle_ts < last_ts:
            self.out_of_order_count += 1
            return False, f"REJECTED_OUT_OF_ORDER: closed_ts {event.closed_candle_ts} < last_seen {last_ts} for stream {key}."

        if last_ts >= 0 and event.closed_candle_ts == last_ts:
            self.duplicate_count += 1
            return False, f"REJECTED_DUPLICATE: Event for stream {key} at ts {event.closed_candle_ts} already processed."

        # Monotonic sequence check for this stream
        last_seq = self._last_sequence.get(key, -1)
        if last_seq >= 0 and event.sequence_id <= last_seq:
            if event.sequence_id == last_seq:
                self.duplicate_count += 1
                return False, f"REJECTED_DUPLICATE: sequence_id {event.sequence_id} == last_sequence {last_seq} for stream {key}."
            self.out_of_order_count += 1
            return False, f"REJECTED_SEQUENCE_INVERSION: sequence_id {event.sequence_id} < last_sequence {last_seq} for stream {key}."

        # Accept and update stream high water marks
        self._last_candle_ts[key] = event.closed_candle_ts
        self._last_sequence[key] = event.sequence_id
        return True, None

    def reset(self) -> None:
        self._last_candle_ts.clear()
        self._last_sequence.clear()
        self.duplicate_count = 0
        self.out_of_order_count = 0
