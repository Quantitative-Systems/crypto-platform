"""STRATA — Fractal Event Graph and Canonical Structural Event Contracts.

Version: 1.0.0-strata-phase1
Implements:
1. Versioned event contracts for swings, BOS, CHoCH, Order Blocks, FVGs, Sweeps, and Dealing Ranges.
2. Strict Causal Invariants:
   - `event_time`: When the market phenomenon occurred (e.g. extremum pivot candle).
   - `available_time`: When the event was confirmed and became causally visible to algorithms (strictly >= event_time).
3. Cross-Timeframe Relationships:
   - Shared canonical event identity across overlapping timeframe sets.
   - Hierarchical parent-child linking (HTF Context -> MTF Setup -> LTF Entry).
4. Duplicate Exposure Prevention:
   - Identifies candidate trades that share the same root market event, preventing double-counting portfolio risk.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np


class EventType(str, Enum):
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"
    BOS_BULLISH = "BOS_BULLISH"
    BOS_BEARISH = "BOS_BEARISH"
    CHOCH_BULLISH = "CHOCH_BULLISH"
    CHOCH_BEARISH = "CHOCH_BEARISH"
    ORDER_BLOCK_DEMAND = "ORDER_BLOCK_DEMAND"
    ORDER_BLOCK_SUPPLY = "ORDER_BLOCK_SUPPLY"
    FVG_BULLISH = "FVG_BULLISH"
    FVG_BEARISH = "FVG_BEARISH"
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
    DEALING_RANGE_SHIFT = "DEALING_RANGE_SHIFT"


class InvalidationCondition(str, Enum):
    CLOSE_BEYOND_OB = "CLOSE_BEYOND_OB"
    FVG_COMPLETELY_FILLED = "FVG_COMPLETELY_FILLED"
    OPPOSITE_STRUCTURAL_BREAK = "OPPOSITE_STRUCTURAL_BREAK"
    RANGE_EXPANSION_NEW_EXTREMUM = "RANGE_EXPANSION_NEW_EXTREMUM"
    TIME_EXPIRED = "TIME_EXPIRED"


@dataclass
class CanonicalFractalEvent:
    """Master immutable event contract for all market-structure phenomena."""
    event_id: str
    event_type: EventType
    symbol: str
    timeframe: str
    direction: int  # +1 Bullish, -1 Bearish, 0 Neutral
    
    # Causal Temporal Coordinates (Milliseconds UTC)
    event_time: int          # Timestamp of the physical price candle
    available_time: int      # Timestamp when confirmed (strictly >= event_time)
    
    # Price Anchors
    anchor_price: float
    boundary_high: float
    boundary_low: float
    
    # Source Candle Metadata
    source_candle_index: int
    confirmation_candle_index: int
    source_candle_count: int
    
    # Invalidation & State
    invalidation_rule: InvalidationCondition
    invalidation_price: float
    is_active: bool = True
    
    # Cross-Timeframe Lineage
    parent_event_id: Optional[str] = None
    child_event_ids: List[str] = field(default_factory=list)
    set_roles: Dict[str, str] = field(default_factory=dict)  # SetID -> Role (e.g. "SET_2": "HTF_BIAS")
    
    # Metadata Payload
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Strict Causal Invariant Enforcement: No time travel permitted
        if self.available_time < self.event_time:
            raise ValueError(
                f"Causal lookahead violation in event {self.event_id}: "
                f"available_time ({self.available_time}) < event_time ({self.event_time})"
            )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        d["invalidation_rule"] = self.invalidation_rule.value
        return d


class FractalEventGraph:
    """Queryable cross-timeframe dependency graph linking structural market events."""

    def __init__(self):
        self.events: Dict[str, CanonicalFractalEvent] = {}  # event_id -> event
        self.symbol_events: Dict[str, List[str]] = {}       # symbol -> list of event_ids
        self.timeframe_events: Dict[str, List[str]] = {}    # symbol:tf -> list of event_ids

    def register_event(self, event: CanonicalFractalEvent) -> CanonicalFractalEvent:
        """Registers a canonical event, enforcing uniqueness and indexing causal links."""
        if event.event_id in self.events:
            return self.events[event.event_id]

        self.events[event.event_id] = event
        self.symbol_events.setdefault(event.symbol, []).append(event.event_id)

        tf_key = f"{event.symbol}:{event.timeframe}"
        self.timeframe_events.setdefault(tf_key, []).append(event.event_id)

        # Link to parent if present
        if event.parent_event_id and event.parent_event_id in self.events:
            parent = self.events[event.parent_event_id]
            if event.event_id not in parent.child_event_ids:
                parent.child_event_ids.append(event.event_id)

        return event

    def get_events_visible_at(self, symbol: str, current_time_ms: int) -> List[CanonicalFractalEvent]:
        """Returns all events for a symbol that are causally available at current_time_ms."""
        event_ids = self.symbol_events.get(symbol, [])
        return [
            self.events[eid] for eid in event_ids
            if self.events[eid].available_time <= current_time_ms and self.events[eid].is_active
        ]

    def find_shared_root_event(self, event_id_a: str, event_id_b: str) -> Optional[str]:
        """Traverses parent lineage to determine if two events originate from the same root market event."""
        if event_id_a == event_id_b:
            return event_id_a

        def get_ancestors(eid: str) -> Set[str]:
            ancestors = {eid}
            curr = self.events.get(eid)
            while curr and curr.parent_event_id:
                ancestors.add(curr.parent_event_id)
                curr = self.events.get(curr.parent_event_id)
            return ancestors

        ancestors_a = get_ancestors(event_id_a)
        ancestors_b = get_ancestors(event_id_b)
        intersection = ancestors_a.intersection(ancestors_b)
        if intersection:
            return next(iter(intersection))
        return None

    def detect_overlapping_exposure(
        self, candidate_trades: List[Dict[str, Any]]
    ) -> List[Tuple[Dict[str, Any], str]]:
        """Identifies candidate signals that share the same root market event to prevent duplicate portfolio risk.
        
        Returns:
            List of (candidate_trade, conflict_root_id)
        """
        conflicts = []
        root_map: Dict[str, Dict[str, Any]] = {}

        for cand in candidate_trades:
            root_event_id = cand.get("root_event_id")
            if not root_event_id:
                continue

            if root_event_id in root_map:
                conflicts.append((cand, root_event_id))
            else:
                root_map[root_event_id] = cand

        return conflicts


def create_swing_event(
    symbol: str,
    timeframe: str,
    swing_type: str,  # "HIGH" or "LOW"
    pivot_price: float,
    pivot_ts: int,
    confirmation_ts: int,
    pivot_idx: int,
    confirmation_idx: int,
) -> CanonicalFractalEvent:
    """Constructs a causally confirmed swing event."""
    is_high = (swing_type.upper() == "HIGH")
    event_type = EventType.SWING_HIGH if is_high else EventType.SWING_LOW
    direction = -1 if is_high else 1  # Swing high forms resistance (-1), Swing low forms support (+1)
    
    event_id = f"SWG_{symbol[:3]}_{timeframe}_{pivot_ts}_{'H' if is_high else 'L'}"
    return CanonicalFractalEvent(
        event_id=event_id,
        event_type=event_type,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        event_time=pivot_ts,
        available_time=confirmation_ts,
        anchor_price=pivot_price,
        boundary_high=pivot_price if is_high else pivot_price * 1.002,
        boundary_low=pivot_price * 0.998 if is_high else pivot_price,
        source_candle_index=pivot_idx,
        confirmation_candle_index=confirmation_idx,
        source_candle_count=confirmation_idx - pivot_idx + 1,
        invalidation_rule=InvalidationCondition.OPPOSITE_STRUCTURAL_BREAK,
        invalidation_price=pivot_price,
        meta={"swing_type": swing_type},
    )


def create_order_block_event(
    symbol: str,
    timeframe: str,
    ob_type: str,  # "DEMAND" or "SUPPLY"
    high_price: float,
    low_price: float,
    creation_ts: int,
    confirmation_ts: int,
    candle_idx: int,
    parent_swing_id: Optional[str] = None,
) -> CanonicalFractalEvent:
    """Constructs a causally verified Order Block event."""
    is_demand = (ob_type.upper() == "DEMAND")
    event_type = EventType.ORDER_BLOCK_DEMAND if is_demand else EventType.ORDER_BLOCK_SUPPLY
    direction = 1 if is_demand else -1

    event_id = f"OB_{symbol[:3]}_{timeframe}_{creation_ts}_{'DEM' if is_demand else 'SUP'}"
    return CanonicalFractalEvent(
        event_id=event_id,
        event_type=event_type,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        event_time=creation_ts,
        available_time=confirmation_ts,
        anchor_price=(high_price + low_price) / 2.0,
        boundary_high=high_price,
        boundary_low=low_price,
        source_candle_index=candle_idx,
        confirmation_candle_index=candle_idx + 1,
        source_candle_count=1,
        invalidation_rule=InvalidationCondition.CLOSE_BEYOND_OB,
        invalidation_price=low_price if is_demand else high_price,
        parent_event_id=parent_swing_id,
        meta={"ob_type": ob_type},
    )
