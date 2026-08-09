"""
Quantitative Systems Platform — Crypto Platform Product
Product 01: Market Language | Engine 4: KeyZone Engine (Hardened)

RESPONSIBILITY
--------------
Consumes OHLCV Candle history, Engine 2 StructureEvents, and Engine 3 LiquidityState.

Produces ONLY location intelligence:
    - Bullish & Bearish Order Blocks (OB)
    - Bullish & Bearish Fair Value Gaps (FVG)
    - KeyZone Mitigation tracking (UNMITIGATED -> MITIGATED -> INVALIDATED)
    - Complete Event Stream (KEYZONE_CREATED, KEYZONE_MITIGATED, KEYZONE_INVALIDATED)

STRICT BOUNDARY
---------------
This engine does NOT know about:
    - Market Phase (Engine 5)
    - Strategy signals, BUY/SELL commands, Entries, Stop Loss, Take Profit
    - Risk management, Position sizing, Broker APIs, or Execution Adapters
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set, Tuple

from market_intelligence.raw_swing_engine import Candle
from market_intelligence.structure_builder_engine import StructureEvent, EventType
from market_intelligence.liquidity_engine import LiquidityState, LiquidityEventType


class KeyZoneType(Enum):
    BULLISH_OB = "BULLISH_OB"
    BEARISH_OB = "BEARISH_OB"
    BULLISH_FVG = "BULLISH_FVG"
    BEARISH_FVG = "BEARISH_FVG"


class ZoneScope(Enum):
    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"


class ZoneStatus(Enum):
    UNMITIGATED = "UNMITIGATED"
    MITIGATED = "MITIGATED"
    INVALIDATED = "INVALIDATED"


class KeyZoneEventType(Enum):
    KEYZONE_CREATED = "KEYZONE_CREATED"
    KEYZONE_MITIGATED = "KEYZONE_MITIGATED"
    KEYZONE_INVALIDATED = "KEYZONE_INVALIDATED"


@dataclass(frozen=True)
class KeyZone:
    zone_id: str
    zone_type: KeyZoneType
    scope: ZoneScope
    price_level: float
    high_boundary: float
    low_boundary: float
    creation_timestamp: int
    creation_candle_index: int
    origin_candle_index: Optional[int] = None
    origin_swing_id: Optional[str] = None
    status: ZoneStatus = ZoneStatus.UNMITIGATED
    mitigation_timestamp: Optional[int] = None
    mitigation_candle_index: Optional[int] = None
    strength_score: float = 1.0


@dataclass(frozen=True)
class KeyZoneEvent:
    timestamp: int
    event_type: KeyZoneEventType
    zone_id: str
    zone_type: KeyZoneType
    price_level: float
    high_boundary: float
    low_boundary: float
    candle_index: int


@dataclass
class KeyZoneState:
    active_zones: List[KeyZone]
    mitigated_zones: List[KeyZone]
    invalidated_zones: List[KeyZone]
    events: List[KeyZoneEvent]


class KeyZoneEngine:
    """
    Deterministic, stateful KeyZone Location Engine.
    Detects Order Blocks and Fair Value Gaps and tracks mitigation/invalidation lifecycles.
    """

    def __init__(self, fvg_min_gap_pct: float = 0.0) -> None:
        if fvg_min_gap_pct < 0:
            raise ValueError("fvg_min_gap_pct must be >= 0")
        self.fvg_min_gap_pct = fvg_min_gap_pct
        self._emitted_event_keys: Set[Tuple] = set()

    def reset(self) -> None:
        """Reset stateful event tracking memory."""
        self._emitted_event_keys.clear()

    def process(
        self,
        candles: List[Candle],
        structure_events: List[StructureEvent],
        liquidity_state: Optional[LiquidityState] = None
    ) -> KeyZoneState:
        """
        Main Engine 4 processing loop.
        Identifies OBs and FVGs, emits creation events, and evaluates lifecycles.
        """
        if not candles:
            return KeyZoneState(active_zones=[], mitigated_zones=[], invalidated_zones=[], events=[])

        events: List[KeyZoneEvent] = []

        # 1. Detect Order Blocks from Structure Events
        obs, ob_creation_events = self._detect_order_blocks(candles, structure_events)

        # 2. Detect Fair Value Gaps from 3-Candle Imbalances
        fvgs, fvg_creation_events = self._detect_fair_value_gaps(candles)

        all_zones = self._deduplicate_zones(obs + fvgs)
        events.extend(ob_creation_events + fvg_creation_events)

        # 3. Enhance strength scores if liquidity sweep associated
        if liquidity_state and liquidity_state.events:
            all_zones = self._apply_liquidity_enhancement(all_zones, liquidity_state)

        # 4. Evaluate Lifecycles (UNMITIGATED -> MITIGATED -> INVALIDATED)
        active_zones, mitigated_zones, invalidated_zones, lifecycle_events = self._evaluate_zone_lifecycles(
            all_zones=all_zones,
            candles=candles
        )
        events.extend(lifecycle_events)

        # Sort events chronologically
        events.sort(key=lambda e: (e.candle_index, e.timestamp, e.event_type.value))

        return KeyZoneState(
            active_zones=active_zones,
            mitigated_zones=mitigated_zones,
            invalidated_zones=invalidated_zones,
            events=events
        )

    def _detect_order_blocks(
        self,
        candles: List[Candle],
        structure_events: List[StructureEvent]
    ) -> Tuple[List[KeyZone], List[KeyZoneEvent]]:
        zones: List[KeyZone] = []
        creation_events: List[KeyZoneEvent] = []

        if not candles or not structure_events:
            return zones, creation_events

        # Strict specification: Exclude INTERNAL_CHOCH
        valid_types = {
            EventType.EXTERNAL_BOS, EventType.EXTERNAL_CHOCH,
            EventType.INTERNAL_BOS, EventType.MSS
        }

        for ev in structure_events:
            if ev.event_type not in valid_types:
                continue

            break_idx = ev.candle_index
            if break_idx >= len(candles):
                continue

            is_bullish = "BULLISH" in ev.direction

            # Search backward from break index for the last opposing candle
            origin_idx = None
            for idx in range(break_idx - 1, -1, -1):
                c = candles[idx]
                if is_bullish and c.close < c.open:  # Bearish candle before bullish surge
                    origin_idx = idx
                    break
                elif not is_bullish and c.close > c.open:  # Bullish candle before bearish surge
                    origin_idx = idx
                    break

            if origin_idx is None:
                origin_idx = max(0, break_idx - 1)

            origin_candle = candles[origin_idx]
            high_b = origin_candle.high
            low_b = origin_candle.low
            price_lvl = (high_b + low_b) / 2.0

            z_type = KeyZoneType.BULLISH_OB if is_bullish else KeyZoneType.BEARISH_OB
            scope = ZoneScope.EXTERNAL if "EXTERNAL" in ev.event_type.value else ZoneScope.INTERNAL
            zone_id = f"OB_{z_type.value}_{origin_candle.timestamp}_{ev.broken_swing_id}"

            zone = KeyZone(
                zone_id=zone_id,
                zone_type=z_type,
                scope=scope,
                price_level=price_lvl,
                high_boundary=high_b,
                low_boundary=low_b,
                creation_timestamp=ev.timestamp,
                creation_candle_index=break_idx,
                origin_candle_index=origin_idx,
                origin_swing_id=ev.broken_swing_id,
                status=ZoneStatus.UNMITIGATED,
                strength_score=1.0
            )
            zones.append(zone)

            # Emit KEYZONE_CREATED event
            event_candle = candles[break_idx]
            self._emit_event(
                creation_events, event_candle, zone, KeyZoneEventType.KEYZONE_CREATED, break_idx
            )

        return zones, creation_events

    def _detect_fair_value_gaps(self, candles: List[Candle]) -> Tuple[List[KeyZone], List[KeyZoneEvent]]:
        zones: List[KeyZone] = []
        creation_events: List[KeyZoneEvent] = []

        if len(candles) < 3:
            return zones, creation_events

        for i in range(2, len(candles)):
            c0 = candles[i - 2]
            c1 = candles[i - 1]
            c2 = candles[i]

            # Bullish FVG: Low of candle 2 is higher than High of candle 0
            if c2.low > c0.high:
                gap_size = c2.low - c0.high
                min_gap = c0.high * self.fvg_min_gap_pct
                if gap_size >= min_gap:
                    high_b = c2.low
                    low_b = c0.high
                    price_lvl = (high_b + low_b) / 2.0
                    zone_id = f"FVG_BULLISH_{c1.timestamp}_{i}"
                    zone = KeyZone(
                        zone_id=zone_id,
                        zone_type=KeyZoneType.BULLISH_FVG,
                        scope=ZoneScope.INTERNAL,
                        price_level=price_lvl,
                        high_boundary=high_b,
                        low_boundary=low_b,
                        creation_timestamp=c2.timestamp,
                        creation_candle_index=i,
                        origin_candle_index=i - 1,
                        status=ZoneStatus.UNMITIGATED,
                        strength_score=1.0
                    )
                    zones.append(zone)
                    self._emit_event(
                        creation_events, c2, zone, KeyZoneEventType.KEYZONE_CREATED, i
                    )

            # Bearish FVG: High of candle 2 is lower than Low of candle 0
            elif c2.high < c0.low:
                gap_size = c0.low - c2.high
                min_gap = c0.low * self.fvg_min_gap_pct
                if gap_size >= min_gap:
                    high_b = c0.low
                    low_b = c2.high
                    price_lvl = (high_b + low_b) / 2.0
                    zone_id = f"FVG_BEARISH_{c1.timestamp}_{i}"
                    zone = KeyZone(
                        zone_id=zone_id,
                        zone_type=KeyZoneType.BEARISH_FVG,
                        scope=ZoneScope.INTERNAL,
                        price_level=price_lvl,
                        high_boundary=high_b,
                        low_boundary=low_b,
                        creation_timestamp=c2.timestamp,
                        creation_candle_index=i,
                        origin_candle_index=i - 1,
                        status=ZoneStatus.UNMITIGATED,
                        strength_score=1.0
                    )
                    zones.append(zone)
                    self._emit_event(
                        creation_events, c2, zone, KeyZoneEventType.KEYZONE_CREATED, i
                    )

        return zones, creation_events

    def _deduplicate_zones(self, zones: List[KeyZone]) -> List[KeyZone]:
        seen_ids: Set[str] = set()
        unique: List[KeyZone] = []
        for z in zones:
            if z.zone_id not in seen_ids:
                seen_ids.add(z.zone_id)
                unique.append(z)
        return unique

    def _apply_liquidity_enhancement(
        self,
        zones: List[KeyZone],
        liquidity_state: LiquidityState
    ) -> List[KeyZone]:
        # Filter explicitly for LIQUIDITY_SWEEP and INDUCEMENT events
        valid_sweep_types = {LiquidityEventType.LIQUIDITY_SWEEP, LiquidityEventType.INDUCEMENT}
        swept_indices = {
            ev.candle_index for ev in liquidity_state.events
            if ev.event_type in valid_sweep_types
        }
        enhanced: List[KeyZone] = []

        for z in zones:
            is_enhanced = False
            for idx in (z.creation_candle_index, z.origin_candle_index):
                if idx is not None and idx in swept_indices:
                    is_enhanced = True
                    break

            if is_enhanced:
                enhanced.append(KeyZone(
                    zone_id=z.zone_id,
                    zone_type=z.zone_type,
                    scope=z.scope,
                    price_level=z.price_level,
                    high_boundary=z.high_boundary,
                    low_boundary=z.low_boundary,
                    creation_timestamp=z.creation_timestamp,
                    creation_candle_index=z.creation_candle_index,
                    origin_candle_index=z.origin_candle_index,
                    origin_swing_id=z.origin_swing_id,
                    status=z.status,
                    mitigation_timestamp=z.mitigation_timestamp,
                    mitigation_candle_index=z.mitigation_candle_index,
                    strength_score=1.5
                ))
            else:
                enhanced.append(z)

        return enhanced

    def _evaluate_zone_lifecycles(
        self,
        all_zones: List[KeyZone],
        candles: List[Candle]
    ) -> Tuple[List[KeyZone], List[KeyZone], List[KeyZone], List[KeyZoneEvent]]:
        events: List[KeyZoneEvent] = []
        active_zones: List[KeyZone] = []
        mitigated_zones: List[KeyZone] = []
        invalidated_zones: List[KeyZone] = []

        for zone in all_zones:
            start_idx = zone.creation_candle_index + 1
            if start_idx >= len(candles):
                active_zones.append(zone)
                continue

            final_status = ZoneStatus.UNMITIGATED
            mitigation_ts = None
            mitigation_idx = None

            for idx in range(start_idx, len(candles)):
                c = candles[idx]

                # Bullish Zones (BULLISH_OB / BULLISH_FVG)
                if zone.zone_type in (KeyZoneType.BULLISH_OB, KeyZoneType.BULLISH_FVG):
                    if c.close < zone.low_boundary:
                        # Body closes below zone -> Invalidated (Terminal state)
                        final_status = ZoneStatus.INVALIDATED
                        self._emit_event(
                            events, c, zone, KeyZoneEventType.KEYZONE_INVALIDATED, idx
                        )
                        break
                    elif c.low <= zone.high_boundary and c.close >= zone.low_boundary:
                        # Price re-enters zone -> Mitigated
                        if final_status == ZoneStatus.UNMITIGATED:
                            final_status = ZoneStatus.MITIGATED
                            mitigation_ts = c.timestamp
                            mitigation_idx = idx
                            self._emit_event(
                                events, c, zone, KeyZoneEventType.KEYZONE_MITIGATED, idx
                            )

                # Bearish Zones (BEARISH_OB / BEARISH_FVG)
                elif zone.zone_type in (KeyZoneType.BEARISH_OB, KeyZoneType.BEARISH_FVG):
                    if c.close > zone.high_boundary:
                        # Body closes above zone -> Invalidated (Terminal state)
                        final_status = ZoneStatus.INVALIDATED
                        self._emit_event(
                            events, c, zone, KeyZoneEventType.KEYZONE_INVALIDATED, idx
                        )
                        break
                    elif c.high >= zone.low_boundary and c.close <= zone.high_boundary:
                        # Price re-enters zone -> Mitigated
                        if final_status == ZoneStatus.UNMITIGATED:
                            final_status = ZoneStatus.MITIGATED
                            mitigation_ts = c.timestamp
                            mitigation_idx = idx
                            self._emit_event(
                                events, c, zone, KeyZoneEventType.KEYZONE_MITIGATED, idx
                            )

            updated_zone = KeyZone(
                zone_id=zone.zone_id,
                zone_type=zone.zone_type,
                scope=zone.scope,
                price_level=zone.price_level,
                high_boundary=zone.high_boundary,
                low_boundary=zone.low_boundary,
                creation_timestamp=zone.creation_timestamp,
                creation_candle_index=zone.creation_candle_index,
                origin_candle_index=zone.origin_candle_index,
                origin_swing_id=zone.origin_swing_id,
                status=final_status,
                mitigation_timestamp=mitigation_ts,
                mitigation_candle_index=mitigation_idx,
                strength_score=zone.strength_score
            )

            if final_status == ZoneStatus.UNMITIGATED:
                active_zones.append(updated_zone)
            elif final_status == ZoneStatus.MITIGATED:
                mitigated_zones.append(updated_zone)
            elif final_status == ZoneStatus.INVALIDATED:
                invalidated_zones.append(updated_zone)

        return active_zones, mitigated_zones, invalidated_zones, events

    def _emit_event(
        self,
        events: List[KeyZoneEvent],
        candle: Candle,
        zone: KeyZone,
        event_type: KeyZoneEventType,
        candle_index: int
    ) -> None:
        event_key = (event_type.value, zone.zone_id, candle_index)
        if event_key in self._emitted_event_keys:
            return

        self._emitted_event_keys.add(event_key)
        events.append(KeyZoneEvent(
            timestamp=candle.timestamp,
            event_type=event_type,
            zone_id=zone.zone_id,
            zone_type=zone.zone_type,
            price_level=zone.price_level,
            high_boundary=zone.high_boundary,
            low_boundary=zone.low_boundary,
            candle_index=candle_index
        ))
