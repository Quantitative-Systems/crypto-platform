"""
APEX Quantitative Systems Platform
Product 01 — Market Language | Engine 5 — Market Phase Engine (Hardened Core)

PURPOSE
-------
Classify chronological market behavior into 7 canonical Wyckoff/SMC phases:
    ACCUMULATION, EXPANSION, PULLBACK, CONTINUATION, DISTRIBUTION, REVERSAL, COMPRESSION

STRICT BOUNDARY
---------------
This engine describes market behavior ONLY.
It MUST NOT know about strategy signals, entries, stop loss, take profit,
position sizing, account equity, or broker execution APIs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Set, Tuple

from market_intelligence.raw_swing_engine import Candle
from market_intelligence.structure_builder_engine import (
    EventType,
    StructureEvent,
    TrendDirection,
)
from market_intelligence.liquidity_engine import (
    LiquidityEventType,
    LiquidityPoolType,
    LiquidityScope,
    LiquidityState,
)
from market_intelligence.keyzone_engine import (
    KeyZoneEvent,
    KeyZoneEventType,
    KeyZoneState,
    KeyZoneType,
    ZoneStatus,
)


class MarketPhase(Enum):
    ACCUMULATION = "ACCUMULATION"
    EXPANSION = "EXPANSION"
    PULLBACK = "PULLBACK"
    CONTINUATION = "CONTINUATION"
    DISTRIBUTION = "DISTRIBUTION"
    REVERSAL = "REVERSAL"
    COMPRESSION = "COMPRESSION"


class PhaseEventType(Enum):
    PHASE_TRANSITION = "PHASE_TRANSITION"


class PhaseReason(Enum):
    INITIAL_STATE = "INITIAL_STATE"
    RANGE_CONSOLIDATION = "RANGE_CONSOLIDATION"
    VOLATILITY_COMPRESSION = "VOLATILITY_COMPRESSION"
    EXTERNAL_BOS_EXPANSION = "EXTERNAL_BOS_EXPANSION"
    COUNTER_TREND_PULLBACK = "COUNTER_TREND_PULLBACK"
    KEYZONE_PULLBACK_ENTRY = "KEYZONE_PULLBACK_ENTRY"
    ALIGNED_INTERNAL_SHIFT = "ALIGNED_INTERNAL_SHIFT"
    DISTRIBUTION_FAILURE_TO_EXTEND = "DISTRIBUTION_FAILURE_TO_EXTEND"
    PROTECTED_STRUCTURE_BREAK = "PROTECTED_STRUCTURE_BREAK"
    EXTERNAL_CHOCH_REVERSAL = "EXTERNAL_CHOCH_REVERSAL"


@dataclass(frozen=True)
class PhaseEvidence:
    reason: PhaseReason
    structure_event_type: Optional[EventType] = None
    structure_candle_index: Optional[int] = None
    structure_broken_swing_id: Optional[str] = None
    liquidity_event_type: Optional[LiquidityEventType] = None
    liquidity_pool_type: Optional[LiquidityPoolType] = None
    liquidity_scope: Optional[LiquidityScope] = None
    liquidity_candle_index: Optional[int] = None
    keyzone_event_type: Optional[KeyZoneEventType] = None
    keyzone_id: Optional[str] = None
    keyzone_type: Optional[KeyZoneType] = None
    keyzone_candle_index: Optional[int] = None
    parent_trend: TrendDirection = TrendDirection.NEUTRAL


@dataclass(frozen=True)
class PhaseEvent:
    timestamp: int
    candle_index: int
    event_type: PhaseEventType
    previous_phase: MarketPhase
    new_phase: MarketPhase
    reason: PhaseReason
    evidence: Optional[PhaseEvidence] = None


@dataclass
class PhaseState:
    current_phase: MarketPhase
    current_trend: TrendDirection
    phase_history: List[PhaseEvent] = field(default_factory=list)
    events: List[PhaseEvent] = field(default_factory=list)


class PhaseEngine:
    """
    Deterministic, causal Market Phase Engine.
    Requires verified multi-engine contextual evidence for all state transitions.
    """

    def __init__(
        self,
        atr_period: int = 14,
        compression_baseline_period: int = 50,
        compression_ratio: float = 0.50,
        range_lookback: int = 20,
        range_max_width_pct: float = 0.03,
    ) -> None:

        if atr_period < 2:
            raise ValueError("atr_period must be >= 2")
        if compression_baseline_period < 2:
            raise ValueError("compression_baseline_period must be >= 2")
        if compression_ratio <= 0:
            raise ValueError("compression_ratio must be > 0")
        if range_lookback < 3:
            raise ValueError("range_lookback must be >= 3")
        if range_max_width_pct <= 0:
            raise ValueError("range_max_width_pct must be > 0")

        self.atr_period = atr_period
        self.compression_baseline_period = compression_baseline_period
        self.compression_ratio = compression_ratio
        self.range_lookback = range_lookback
        self.range_max_width_pct = range_max_width_pct
        self._emitted_event_keys: Set[Tuple] = set()

    def reset(self) -> None:
        self._emitted_event_keys.clear()

    def process(
        self,
        candles: List[Candle],
        structure_events: List[StructureEvent],
        liquidity_state: Optional[LiquidityState] = None,
        keyzone_state: Optional[KeyZoneState] = None,
    ) -> PhaseState:

        self._validate_inputs(candles, structure_events)

        if not candles:
            return PhaseState(
                current_phase=MarketPhase.ACCUMULATION,
                current_trend=TrendDirection.NEUTRAL,
            )

        structure_by_idx = self._index_structure_events(structure_events)
        liquidity_by_idx = self._index_liquidity_events(liquidity_state)
        keyzone_by_idx = self._index_keyzone_events(keyzone_state)

        atr = self._compute_atr(candles)

        current_phase = MarketPhase.ACCUMULATION
        current_trend = TrendDirection.NEUTRAL
        phase_history: List[PhaseEvent] = []

        pullback_zone_seen = False
        expansion_direction = TrendDirection.NEUTRAL
        terminal_extension_seen = False

        for idx, candle in enumerate(candles):

            candle_structure = structure_by_idx.get(idx, [])
            candle_liquidity = liquidity_by_idx.get(idx, [])
            candle_keyzones = keyzone_by_idx.get(idx, [])

            # 1. Update Macro Trend Causally
            for ev in candle_structure:
                direction = self._parse_direction(ev.direction)
                if ev.event_type == EventType.EXTERNAL_BOS:
                    if direction != TrendDirection.NEUTRAL:
                        current_trend = direction
                elif ev.event_type == EventType.EXTERNAL_CHOCH:
                    if direction != TrendDirection.NEUTRAL:
                        current_trend = direction
                elif ev.event_type == EventType.MSS:
                    if current_trend == TrendDirection.NEUTRAL:
                        if direction != TrendDirection.NEUTRAL:
                            current_trend = direction

            previous_phase = current_phase
            transition_reason: Optional[PhaseReason] = None
            transition_evidence: Optional[PhaseEvidence] = None

            # 2. Reversal Priority (EXTERNAL_CHOCH breaks protected structure)
            reversal_event = self._find_reversal_event(candle_structure, current_trend)
            if reversal_event is not None:
                direction = self._parse_direction(reversal_event.direction)
                old_trend = current_trend
                if direction != TrendDirection.NEUTRAL:
                    current_trend = direction

                current_phase = MarketPhase.REVERSAL
                transition_reason = (
                    PhaseReason.PROTECTED_STRUCTURE_BREAK
                    if reversal_event.event_type == EventType.EXTERNAL_CHOCH
                    else PhaseReason.EXTERNAL_CHOCH_REVERSAL
                )
                transition_evidence = PhaseEvidence(
                    reason=transition_reason,
                    structure_event_type=reversal_event.event_type,
                    structure_candle_index=reversal_event.candle_index,
                    structure_broken_swing_id=reversal_event.broken_swing_id,
                    parent_trend=old_trend,
                )

            # 3. External BOS -> Expansion
            elif self._has_external_bos(candle_structure):
                bos = self._first_event(candle_structure, EventType.EXTERNAL_BOS)
                direction = self._parse_direction(bos.direction)
                if direction != TrendDirection.NEUTRAL:
                    current_trend = direction
                    expansion_direction = direction

                current_phase = MarketPhase.EXPANSION
                terminal_extension_seen = False
                pullback_zone_seen = False
                transition_reason = PhaseReason.EXTERNAL_BOS_EXPANSION
                transition_evidence = PhaseEvidence(
                    reason=transition_reason,
                    structure_event_type=bos.event_type,
                    structure_candle_index=bos.candle_index,
                    structure_broken_swing_id=bos.broken_swing_id,
                    parent_trend=current_trend,
                )

            # 4. KeyZone Interaction (Strict: KEYZONE_MITIGATED required, NOT KEYZONE_CREATED)
            relevant_zone_event = self._find_mitigated_keyzone_event(
                candle_keyzones, expansion_direction or current_trend
            )

            if relevant_zone_event is not None:
                if (
                    current_phase == MarketPhase.EXPANSION
                    and expansion_direction != TrendDirection.NEUTRAL
                    and self._is_counter_trend_zone(relevant_zone_event, expansion_direction)
                ):
                    pullback_zone_seen = True
                    current_phase = MarketPhase.PULLBACK
                    transition_reason = PhaseReason.KEYZONE_PULLBACK_ENTRY
                    transition_evidence = PhaseEvidence(
                        reason=transition_reason,
                        keyzone_event_type=relevant_zone_event.event_type,
                        keyzone_id=relevant_zone_event.zone_id,
                        keyzone_type=relevant_zone_event.zone_type,
                        keyzone_candle_index=relevant_zone_event.candle_index,
                        parent_trend=expansion_direction,
                    )
                elif (
                    current_phase == MarketPhase.PULLBACK
                    and relevant_zone_event.event_type == KeyZoneEventType.KEYZONE_MITIGATED
                ):
                    pullback_zone_seen = True

            # 5. Liquidity Context
            sweep = self._find_counter_trend_sweep(candle_liquidity, expansion_direction)
            if (
                sweep is not None
                and current_phase == MarketPhase.EXPANSION
                and expansion_direction != TrendDirection.NEUTRAL
            ):
                terminal_extension_seen = True

            # 6. Pullback Confirmation
            if (
                current_phase == MarketPhase.EXPANSION
                and expansion_direction != TrendDirection.NEUTRAL
                and self._has_counter_trend_structure(candle_structure, expansion_direction)
                and (pullback_zone_seen or terminal_extension_seen)
            ):
                current_phase = MarketPhase.PULLBACK
                transition_reason = PhaseReason.COUNTER_TREND_PULLBACK
                transition_evidence = self._build_structure_evidence(
                    candle_structure, PhaseReason.COUNTER_TREND_PULLBACK, expansion_direction
                )

            # 7. Continuation (Requires Pullback + KeyZone Mitigation + Aligned Internal Shift)
            aligned_shift = self._find_aligned_internal_shift(candle_structure, expansion_direction)
            if (
                current_phase == MarketPhase.PULLBACK
                and pullback_zone_seen
                and aligned_shift is not None
            ):
                current_phase = MarketPhase.CONTINUATION
                transition_reason = PhaseReason.ALIGNED_INTERNAL_SHIFT
                transition_evidence = PhaseEvidence(
                    reason=transition_reason,
                    structure_event_type=aligned_shift.event_type,
                    structure_candle_index=aligned_shift.candle_index,
                    structure_broken_swing_id=aligned_shift.broken_swing_id,
                    parent_trend=expansion_direction,
                )
                pullback_zone_seen = False
                terminal_extension_seen = False

            # 8. Distribution
            if (
                current_phase in (MarketPhase.EXPANSION, MarketPhase.CONTINUATION)
                and self._distribution_context(candles, idx, expansion_direction, candle_liquidity)
            ):
                current_phase = MarketPhase.DISTRIBUTION
                transition_reason = PhaseReason.DISTRIBUTION_FAILURE_TO_EXTEND
                transition_evidence = self._build_distribution_evidence(candle_liquidity, expansion_direction)

            # 9. Compression
            if self._is_compressed(atr, idx):
                if current_phase not in (MarketPhase.EXPANSION, MarketPhase.REVERSAL):
                    current_phase = MarketPhase.COMPRESSION
                    transition_reason = PhaseReason.VOLATILITY_COMPRESSION
                    transition_evidence = PhaseEvidence(
                        reason=transition_reason,
                        parent_trend=current_trend,
                    )

            # 10. Range / Accumulation
            if (
                current_phase in (MarketPhase.ACCUMULATION, MarketPhase.COMPRESSION)
                and self._is_bounded_range(candles, idx)
                and not self._has_recent_external_bos(structure_events, idx)
            ):
                current_phase = MarketPhase.ACCUMULATION
                transition_reason = PhaseReason.RANGE_CONSOLIDATION
                transition_evidence = PhaseEvidence(
                    reason=transition_reason,
                    parent_trend=current_trend,
                )

            # 11. Emit Transitions Only
            if current_phase != previous_phase:
                reason = transition_reason or PhaseReason.INITIAL_STATE
                event_key = (previous_phase.value, current_phase.value, idx, reason.value)

                if event_key not in self._emitted_event_keys:
                    self._emitted_event_keys.add(event_key)
                    phase_event = PhaseEvent(
                        timestamp=candle.timestamp,
                        candle_index=idx,
                        event_type=PhaseEventType.PHASE_TRANSITION,
                        previous_phase=previous_phase,
                        new_phase=current_phase,
                        reason=reason,
                        evidence=transition_evidence,
                    )
                    phase_history.append(phase_event)

        return PhaseState(
            current_phase=current_phase,
            current_trend=current_trend,
            phase_history=phase_history,
            events=phase_history.copy(),
        )

    @staticmethod
    def _validate_inputs(candles: List[Candle], structure_events: List[StructureEvent]) -> None:
        if not isinstance(candles, list) or not isinstance(structure_events, list):
            raise TypeError("Inputs must be lists")

        prev_ts = None
        for idx, candle in enumerate(candles):
            if candle.high < candle.low or candle.open < candle.low or candle.open > candle.high or candle.close < candle.low or candle.close > candle.high:
                raise ValueError(f"candle[{idx}] price bounds invalid")
            if prev_ts is not None and candle.timestamp < prev_ts:
                raise ValueError("candles must be in chronological order")
            prev_ts = candle.timestamp

        for ev in structure_events:
            if ev.candle_index < 0 or (ev.candle_index >= len(candles) and candles):
                raise ValueError("structure event candle_index invalid")

    @staticmethod
    def _index_structure_events(events: Iterable[StructureEvent]) -> Dict[int, List[StructureEvent]]:
        indexed: Dict[int, List[StructureEvent]] = {}
        for event in events:
            indexed.setdefault(event.candle_index, []).append(event)
        for values in indexed.values():
            values.sort(key=lambda x: (x.timestamp, x.structural_epoch, x.event_type.value))
        return indexed

    @staticmethod
    def _index_liquidity_events(state: Optional[LiquidityState]) -> Dict[int, List]:
        indexed: Dict[int, List] = {}
        if state is None:
            return indexed
        for event in state.events:
            indexed.setdefault(event.candle_index, []).append(event)
        return indexed

    @staticmethod
    def _index_keyzone_events(state: Optional[KeyZoneState]) -> Dict[int, List[KeyZoneEvent]]:
        indexed: Dict[int, List[KeyZoneEvent]] = {}
        if state is None:
            return indexed
        for event in state.events:
            indexed.setdefault(event.candle_index, []).append(event)
        for values in indexed.values():
            values.sort(key=lambda x: (x.timestamp, x.event_type.value, x.zone_id))
        return indexed

    @staticmethod
    def _parse_direction(direction: str) -> TrendDirection:
        val = str(direction).upper()
        if "BULL" in val or val in {"LONG", "UP"}:
            return TrendDirection.BULLISH
        if "BEAR" in val or val in {"SHORT", "DOWN"}:
            return TrendDirection.BEARISH
        return TrendDirection.NEUTRAL

    @staticmethod
    def _has_external_bos(events: List[StructureEvent]) -> bool:
        return any(e.event_type == EventType.EXTERNAL_BOS for e in events)

    @staticmethod
    def _first_event(events: List[StructureEvent], event_type: EventType) -> StructureEvent:
        for e in events:
            if e.event_type == event_type:
                return e
        raise ValueError("Structure event does not exist")

    @staticmethod
    def _find_reversal_event(events: List[StructureEvent], current_trend: TrendDirection) -> Optional[StructureEvent]:
        for e in events:
            if e.event_type == EventType.EXTERNAL_CHOCH:
                return e
        return None

    def _has_counter_trend_structure(self, events: List[StructureEvent], parent_trend: TrendDirection) -> bool:
        for e in events:
            direction = self._parse_direction(e.direction)
            if e.event_type in (EventType.INTERNAL_CHOCH, EventType.MSS, EventType.FAILED_BOS):
                if parent_trend == TrendDirection.BULLISH and direction == TrendDirection.BEARISH:
                    return True
                if parent_trend == TrendDirection.BEARISH and direction == TrendDirection.BULLISH:
                    return True
        return False

    def _find_aligned_internal_shift(self, events: List[StructureEvent], parent_trend: TrendDirection) -> Optional[StructureEvent]:
        if parent_trend == TrendDirection.NEUTRAL:
            return None
        for e in events:
            direction = self._parse_direction(e.direction)
            if e.event_type in (EventType.INTERNAL_CHOCH, EventType.INTERNAL_BOS, EventType.MSS):
                if direction == parent_trend:
                    return e
        return None

    def _build_structure_evidence(self, events: List[StructureEvent], reason: PhaseReason, parent_trend: TrendDirection) -> Optional[PhaseEvidence]:
        for e in events:
            if e.event_type in (EventType.INTERNAL_CHOCH, EventType.MSS, EventType.FAILED_BOS):
                return PhaseEvidence(
                    reason=reason,
                    structure_event_type=e.event_type,
                    structure_candle_index=e.candle_index,
                    structure_broken_swing_id=e.broken_swing_id,
                    parent_trend=parent_trend,
                )
        return None

    @staticmethod
    def _find_counter_trend_sweep(events: List, parent_trend: TrendDirection):
        if parent_trend == TrendDirection.NEUTRAL:
            return None
        for e in events:
            if e.event_type != LiquidityEventType.LIQUIDITY_SWEEP:
                continue
            direction = str(e.direction).upper()
            if parent_trend == TrendDirection.BULLISH:
                if e.pool_type in (LiquidityPoolType.SSL, LiquidityPoolType.EQL) or "BEAR" in direction:
                    return e
            elif parent_trend == TrendDirection.BEARISH:
                if e.pool_type in (LiquidityPoolType.BSL, LiquidityPoolType.EQH) or "BULL" in direction:
                    return e
        return None

    @staticmethod
    def _find_mitigated_keyzone_event(events: List[KeyZoneEvent], parent_trend: TrendDirection) -> Optional[KeyZoneEvent]:
        if parent_trend == TrendDirection.NEUTRAL:
            return None
        for e in events:
            # Strictly KEYZONE_MITIGATED (Re-entry), NOT KEYZONE_CREATED
            if e.event_type != KeyZoneEventType.KEYZONE_MITIGATED:
                continue
            if parent_trend == TrendDirection.BULLISH and e.zone_type in (KeyZoneType.BULLISH_OB, KeyZoneType.BULLISH_FVG):
                return e
            if parent_trend == TrendDirection.BEARISH and e.zone_type in (KeyZoneType.BEARISH_OB, KeyZoneType.BEARISH_FVG):
                return e
        return None

    @staticmethod
    def _is_counter_trend_zone(event: KeyZoneEvent, parent_trend: TrendDirection) -> bool:
        if parent_trend == TrendDirection.BULLISH:
            return event.zone_type in (KeyZoneType.BULLISH_OB, KeyZoneType.BULLISH_FVG)
        if parent_trend == TrendDirection.BEARISH:
            return event.zone_type in (KeyZoneType.BEARISH_OB, KeyZoneType.BEARISH_FVG)
        return False

    def _compute_atr(self, candles: List[Candle]) -> List[Optional[float]]:
        atr: List[Optional[float]] = [None] * len(candles)
        true_ranges: List[float] = []
        for idx, c in enumerate(candles):
            if idx == 0:
                tr = c.high - c.low
            else:
                prev_close = candles[idx - 1].close
                tr = max(c.high - c.low, abs(c.high - prev_close), abs(c.low - prev_close))
            true_ranges.append(tr)

        for idx in range(self.atr_period - 1, len(candles)):
            window = true_ranges[idx - self.atr_period + 1 : idx + 1]
            atr[idx] = sum(window) / len(window)
        return atr

    def _is_compressed(self, atr: List[Optional[float]], idx: int) -> bool:
        if atr[idx] is None:
            return False
        start = idx - self.compression_baseline_period + 1
        if start < 0:
            return False
        baseline = [v for v in atr[start : idx + 1] if v is not None]
        if len(baseline) < self.compression_baseline_period:
            return False
        avg_base = sum(baseline) / len(baseline)
        return avg_base > 0 and atr[idx] < (avg_base * self.compression_ratio)

    def _is_bounded_range(self, candles: List[Candle], idx: int) -> bool:
        if idx + 1 < self.range_lookback:
            return False
        window = candles[idx - self.range_lookback + 1 : idx + 1]
        high = max(c.high for c in window)
        low = min(c.low for c in window)
        ref = max(abs(window[-1].close), 1e-12)
        return ((high - low) / ref) <= self.range_max_width_pct

    def _distribution_context(self, candles: List[Candle], idx: int, direction: TrendDirection, liquidity_events: List) -> bool:
        if direction == TrendDirection.NEUTRAL or idx + 1 < self.range_lookback:
            return False
        window = candles[idx - self.range_lookback + 1 : idx + 1]
        high = max(c.high for c in window)
        low = min(c.low for c in window)
        width = high - low
        if width <= 0:
            return False
        last_close = candles[idx].close
        near_extreme = (last_close >= high - width * 0.25) if direction == TrendDirection.BULLISH else (last_close <= low + width * 0.25)
        has_sweep = any(e.event_type == LiquidityEventType.LIQUIDITY_SWEEP for e in liquidity_events)
        return near_extreme and has_sweep

    def _build_distribution_evidence(self, events: List, direction: TrendDirection) -> PhaseEvidence:
        for e in events:
            if e.event_type == LiquidityEventType.LIQUIDITY_SWEEP:
                return PhaseEvidence(
                    reason=PhaseReason.DISTRIBUTION_FAILURE_TO_EXTEND,
                    liquidity_event_type=e.event_type,
                    liquidity_pool_type=e.pool_type,
                    liquidity_scope=e.liquidity_scope,
                    liquidity_candle_index=e.candle_index,
                    parent_trend=direction,
                )
        return PhaseEvidence(reason=PhaseReason.DISTRIBUTION_FAILURE_TO_EXTEND, parent_trend=direction)

    @staticmethod
    def _has_recent_external_bos(events: List[StructureEvent], current_idx: int, lookback: int = 5) -> bool:
        return any(
            e.event_type == EventType.EXTERNAL_BOS and current_idx - lookback <= e.candle_index <= current_idx
            for e in events
        )


MarketPhaseEngine = PhaseEngine
