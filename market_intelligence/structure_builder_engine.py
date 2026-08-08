"""
APEX Product 01 — Engine 2.3
Hierarchical Causal Stateful Market Structure Engine

RESPONSIBILITY
--------------
Consumes confirmed RawSwing objects from Engine 1 and Candle history.

Produces ONLY:
    - HH / HL / LH / LL / EQH / EQL
    - External / Internal hierarchy
    - External / Internal trend
    - Protected / Strong swings
    - Weak swings
    - Active dealing range + equilibrium
    - External BOS / CHOCH
    - Internal BOS / CHOCH
    - MSS
    - Failed BOS / wick rejection
    - Deduplicated structural events

STRICT BOUNDARY
---------------
No:
    - Liquidity
    - Order Blocks
    - FVG
    - Market Phase
    - Strategy
    - Entries
    - Risk
    - Execution
    - Broker/API logic

CAUSALITY
---------
A RawSwing becomes structurally usable only after confirmation_index.

Structural events are generated only from candles occurring at or after
the swing's confirmation.

No future structural information is used to create an earlier event.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set, Tuple

from market_intelligence.raw_swing_engine import (
    Candle,
    RawSwing,
    SwingType,
)


# ============================================================================
# ENUMS
# ============================================================================


class SequenceLabel(Enum):
    HH = "HH"
    HL = "HL"
    LH = "LH"
    LL = "LL"
    EQH = "EQH"
    EQL = "EQL"
    UNKNOWN = "UNKNOWN"


class SwingScope(Enum):
    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"


class TrendDirection(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    RANGING = "RANGING"
    NEUTRAL = "NEUTRAL"


class EventType(Enum):
    EXTERNAL_BOS = "EXTERNAL_BOS"
    EXTERNAL_CHOCH = "EXTERNAL_CHOCH"
    INTERNAL_BOS = "INTERNAL_BOS"
    INTERNAL_CHOCH = "INTERNAL_CHOCH"
    MSS = "MSS"
    FAILED_BOS = "FAILED_BOS"


# ============================================================================
# DATA CONTRACTS
# ============================================================================


@dataclass(frozen=True)
class SequenceSwing:
    raw_swing: RawSwing
    label: SequenceLabel
    scope: SwingScope

    is_protected: bool = False
    is_strong: bool = False
    is_weak: bool = False


@dataclass(frozen=True)
class StructureEvent:
    timestamp: int
    event_type: EventType
    price_level: float
    broken_swing_id: str
    direction: str
    candle_index: int
    confirmation: str = "BODY_CLOSE"
    structural_epoch: int = 0


@dataclass(frozen=True)
class DealingRange:
    high_price: float
    low_price: float
    equilibrium_price: float


@dataclass
class StructureState:
    sequence_swings: List[SequenceSwing]

    external_trend: TrendDirection
    internal_trend: TrendDirection

    protected_high: Optional[SequenceSwing]
    protected_low: Optional[SequenceSwing]

    weak_high: Optional[SequenceSwing]
    weak_low: Optional[SequenceSwing]

    dealing_range: Optional[DealingRange]

    events: List[StructureEvent]

    structural_epoch: int = 0


# ============================================================================
# ENGINE
# ============================================================================


class StructureBuilderEngine:

    def __init__(
        self,
        eq_tolerance_pct: float = 0.0005,
    ) -> None:

        if eq_tolerance_pct < 0:
            raise ValueError(
                "eq_tolerance_pct must be >= 0"
            )

        self.eq_tolerance_pct = eq_tolerance_pct

        # Stateful event deduplication ledger.
        self._emitted_event_keys: Set[Tuple] = set()

        # Monotonic structural event counter.
        self._structural_epoch: int = 0

    # ======================================================================
    # PUBLIC API
    # ======================================================================

    def reset(self) -> None:
        """
        Reset event-emission state.
        """

        self._emitted_event_keys.clear()
        self._structural_epoch = 0

    def process(
        self,
        raw_swings: List[RawSwing],
        candles: List[Candle],
    ) -> StructureState:

        self._validate_inputs(
            raw_swings,
            candles,
        )

        latest_candle_index = (
            len(candles) - 1
            if candles
            else None
        )

        usable_swings = self._causal_swings(
            raw_swings,
            latest_candle_index,
        )

        if not usable_swings:
            return self._empty_state()

        # --------------------------------------------------------------
        # 1. SEQUENCE LABELING
        # --------------------------------------------------------------

        labeled_swings = self._label_sequences(
            usable_swings
        )

        # --------------------------------------------------------------
        # 2. HIERARCHY
        # --------------------------------------------------------------

        classified_swings, external_trend = (
            self._build_hierarchy(
                labeled_swings
            )
        )

        # --------------------------------------------------------------
        # 3. INTERNAL TREND
        # --------------------------------------------------------------

        internal_swings = [
            swing
            for swing in classified_swings
            if swing.scope == SwingScope.INTERNAL
        ]

        internal_trend = self._trend_from_sequence(
            internal_swings
        )

        # --------------------------------------------------------------
        # 4. CAUSAL STRUCTURAL ROLES
        # --------------------------------------------------------------

        (
            protected_high,
            protected_low,
            weak_high,
            weak_low,
        ) = self._assign_causal_roles(
            labeled_swings,
            external_trend,
        )

        # --------------------------------------------------------------
        # 5. APPLY ROLE FLAGS
        # --------------------------------------------------------------

        final_swings = self._apply_roles(
            classified_swings,
            protected_high,
            protected_low,
            weak_high,
            weak_low,
        )

        # --------------------------------------------------------------
        # IMPORTANT:
        # Rebind role references to the FINAL role-bearing objects.
        #
        # Previously the state returned the original objects from
        # _assign_causal_roles(), whose flags were all False.
        # --------------------------------------------------------------

        protected_high = self._find_swing(
            final_swings,
            protected_high,
        )

        protected_low = self._find_swing(
            final_swings,
            protected_low,
        )

        weak_high = self._find_swing(
            final_swings,
            weak_high,
        )

        weak_low = self._find_swing(
            final_swings,
            weak_low,
        )

        # --------------------------------------------------------------
        # 6. DEALING RANGE
        # --------------------------------------------------------------

        dealing_range = (
            self._calculate_dealing_range(
                final_swings,
                external_trend,
                protected_high,
                protected_low,
                weak_high,
                weak_low,
            )
        )

        # --------------------------------------------------------------
        # 7. EVENT REPLAY
        # --------------------------------------------------------------

        events = self._replay_structural_events(
            final_swings,
            labeled_swings,
            candles,
        )

        return StructureState(
            sequence_swings=final_swings,
            external_trend=external_trend,
            internal_trend=internal_trend,
            protected_high=protected_high,
            protected_low=protected_low,
            weak_high=weak_high,
            weak_low=weak_low,
            dealing_range=dealing_range,
            events=events,
            structural_epoch=self._structural_epoch,
        )

    # Compatibility API.
    def build_structure(
        self,
        raw_swings: List[RawSwing],
        candles: List[Candle],
    ) -> StructureState:

        return self.process(
            raw_swings,
            candles,
        )

    # ======================================================================
    # VALIDATION
    # ======================================================================

    def _validate_inputs(
        self,
        raw_swings: List[RawSwing],
        candles: List[Candle],
    ) -> None:

        swing_ids = [
            swing.swing_id
            for swing in raw_swings
        ]

        if len(set(swing_ids)) != len(swing_ids):
            raise ValueError(
                "Duplicate swing_id detected"
            )

        for swing in raw_swings:

            if swing.candle_index < 0:
                raise ValueError(
                    "RawSwing candle_index must be >= 0"
                )

            if swing.confirmation_index < 0:
                raise ValueError(
                    "RawSwing confirmation_index must be >= 0"
                )

            if swing.price <= 0:
                raise ValueError(
                    "RawSwing price must be > 0"
                )

        previous_timestamp = None

        for candle in candles:

            if candle.high < candle.low:
                raise ValueError(
                    "Candle high cannot be below candle low"
                )

            if candle.close < candle.low:
                raise ValueError(
                    "Candle close cannot be below candle low"
                )

            if candle.close > candle.high:
                raise ValueError(
                    "Candle close cannot be above candle high"
                )

            if (
                previous_timestamp is not None
                and candle.timestamp <= previous_timestamp
            ):
                raise ValueError(
                    "Candle timestamps must be strictly increasing"
                )

            previous_timestamp = candle.timestamp

    # ======================================================================
    # CAUSAL SWING FILTER
    # ======================================================================

    def _causal_swings(
        self,
        raw_swings: List[RawSwing],
        latest_candle_index: Optional[int],
    ) -> List[RawSwing]:

        ordered = sorted(
            raw_swings,
            key=lambda swing: (
                swing.candle_index,
                swing.confirmation_index,
                swing.swing_id,
            ),
        )

        if latest_candle_index is None:
            return ordered

        return [
            swing
            for swing in ordered
            if swing.confirmation_index
            <= latest_candle_index
        ]

    # ======================================================================
    # EMPTY STATE
    # ======================================================================

    def _empty_state(self) -> StructureState:

        return StructureState(
            sequence_swings=[],
            external_trend=TrendDirection.NEUTRAL,
            internal_trend=TrendDirection.NEUTRAL,
            protected_high=None,
            protected_low=None,
            weak_high=None,
            weak_low=None,
            dealing_range=None,
            events=[],
            structural_epoch=self._structural_epoch,
        )

    # ======================================================================
    # SEQUENCE LABELING
    # ======================================================================

    def _label_sequences(
        self,
        swings: List[RawSwing],
    ) -> List[SequenceSwing]:

        result = []

        previous_high = None
        previous_low = None

        for raw in swings:

            if raw.swing_type == SwingType.HIGH:

                if previous_high is None:

                    label = SequenceLabel.UNKNOWN

                else:

                    difference = (
                        abs(
                            raw.price
                            - previous_high.price
                        )
                        / max(
                            abs(previous_high.price),
                            1e-12,
                        )
                    )

                    if (
                        difference
                        <= self.eq_tolerance_pct
                    ):

                        label = SequenceLabel.EQH

                    elif (
                        raw.price
                        > previous_high.price
                    ):

                        label = SequenceLabel.HH

                    else:

                        label = SequenceLabel.LH

                previous_high = raw

            else:

                if previous_low is None:

                    label = SequenceLabel.UNKNOWN

                else:

                    difference = (
                        abs(
                            raw.price
                            - previous_low.price
                        )
                        / max(
                            abs(previous_low.price),
                            1e-12,
                        )
                    )

                    if (
                        difference
                        <= self.eq_tolerance_pct
                    ):

                        label = SequenceLabel.EQL

                    elif (
                        raw.price
                        > previous_low.price
                    ):

                        label = SequenceLabel.HL

                    else:

                        label = SequenceLabel.LL

                previous_low = raw

            result.append(
                SequenceSwing(
                    raw_swing=raw,
                    label=label,
                    scope=SwingScope.INTERNAL,
                )
            )

        return result

    # ======================================================================
    # TREND
    # ======================================================================

    def _trend_from_sequence(
        self,
        swings: List[SequenceSwing],
    ) -> TrendDirection:

        highs = [
            swing
            for swing in swings
            if swing.raw_swing.swing_type
            == SwingType.HIGH
        ]

        lows = [
            swing
            for swing in swings
            if swing.raw_swing.swing_type
            == SwingType.LOW
        ]

        if len(highs) < 2 or len(lows) < 2:
            return TrendDirection.NEUTRAL

        latest_high = highs[-1].label
        latest_low = lows[-1].label

        bullish_high = latest_high in (
            SequenceLabel.HH,
            SequenceLabel.EQH,
        )

        bullish_low = latest_low in (
            SequenceLabel.HL,
            SequenceLabel.EQL,
        )

        bearish_high = latest_high in (
            SequenceLabel.LH,
            SequenceLabel.EQH,
        )

        bearish_low = latest_low in (
            SequenceLabel.LL,
            SequenceLabel.EQL,
        )

        if bullish_high and bullish_low:
            return TrendDirection.BULLISH

        if bearish_high and bearish_low:
            return TrendDirection.BEARISH

        return TrendDirection.RANGING

    # ======================================================================
    # EXTERNAL / INTERNAL HIERARCHY
    # ======================================================================

    def _build_hierarchy(
        self,
        swings: List[SequenceSwing],
    ) -> Tuple[
        List[SequenceSwing],
        TrendDirection,
    ]:

        if not swings:
            return [], TrendDirection.NEUTRAL

        external_trend = self._trend_from_sequence(
            swings
        )

        external_ids: Set[str] = set()

        # Initial structural anchors.
        for swing in swings[:2]:
            external_ids.add(
                swing.raw_swing.swing_id
            )

        if external_trend == TrendDirection.BULLISH:

            # HH = bullish external expansion.
            for swing in swings:

                if swing.label == SequenceLabel.HH:

                    external_ids.add(
                        swing.raw_swing.swing_id
                    )

            # A HL becomes external after a later HH
            # proves that this low originated expansion.
            for index, swing in enumerate(swings):

                if swing.label != SequenceLabel.HL:
                    continue

                later_hh = any(
                    later.label == SequenceLabel.HH
                    for later in swings[index + 1:]
                )

                if later_hh:

                    external_ids.add(
                        swing.raw_swing.swing_id
                    )

        elif external_trend == TrendDirection.BEARISH:

            # LL = bearish external expansion.
            for swing in swings:

                if swing.label == SequenceLabel.LL:

                    external_ids.add(
                        swing.raw_swing.swing_id
                    )

            # LH becomes external after later LL confirms
            # its causal role.
            for index, swing in enumerate(swings):

                if swing.label != SequenceLabel.LH:
                    continue

                later_ll = any(
                    later.label == SequenceLabel.LL
                    for later in swings[index + 1:]
                )

                if later_ll:

                    external_ids.add(
                        swing.raw_swing.swing_id
                    )

        classified = []

        for swing in swings:

            scope = (
                SwingScope.EXTERNAL
                if swing.raw_swing.swing_id
                in external_ids
                else SwingScope.INTERNAL
            )

            classified.append(
                SequenceSwing(
                    raw_swing=swing.raw_swing,
                    label=swing.label,
                    scope=scope,
                )
            )

        return (
            classified,
            external_trend,
        )

    # ======================================================================
    # CAUSAL ROLES
    # ======================================================================

    def _assign_causal_roles(
        self,
        labeled_swings: List[SequenceSwing],
        external_trend: TrendDirection,
    ):

        protected_high = None
        protected_low = None

        weak_high = None
        weak_low = None

        if external_trend == TrendDirection.BULLISH:

            higher_highs = [
                swing
                for swing in labeled_swings
                if swing.label == SequenceLabel.HH
            ]

            if higher_highs:

                latest_hh = higher_highs[-1]

                weak_high = latest_hh

                hh_index = labeled_swings.index(
                    latest_hh
                )

                preceding_lows = [
                    swing
                    for swing in labeled_swings[:hh_index]
                    if swing.raw_swing.swing_type
                    == SwingType.LOW
                ]

                if preceding_lows:

                    protected_low = preceding_lows[-1]

        elif external_trend == TrendDirection.BEARISH:

            lower_lows = [
                swing
                for swing in labeled_swings
                if swing.label == SequenceLabel.LL
            ]

            if lower_lows:

                latest_ll = lower_lows[-1]

                weak_low = latest_ll

                ll_index = labeled_swings.index(
                    latest_ll
                )

                preceding_highs = [
                    swing
                    for swing in labeled_swings[:ll_index]
                    if swing.raw_swing.swing_type
                    == SwingType.HIGH
                ]

                if preceding_highs:

                    protected_high = preceding_highs[-1]

        return (
            protected_high,
            protected_low,
            weak_high,
            weak_low,
        )

    # ======================================================================
    # APPLY ROLE FLAGS
    # ======================================================================

    def _apply_roles(
        self,
        swings: List[SequenceSwing],
        protected_high,
        protected_low,
        weak_high,
        weak_low,
    ) -> List[SequenceSwing]:

        protected_ids = {
            swing.raw_swing.swing_id
            for swing in (
                protected_high,
                protected_low,
            )
            if swing is not None
        }

        weak_ids = {
            swing.raw_swing.swing_id
            for swing in (
                weak_high,
                weak_low,
            )
            if swing is not None
        }

        result = []

        for swing in swings:

            swing_id = (
                swing.raw_swing.swing_id
            )

            is_protected = (
                swing_id in protected_ids
            )

            is_weak = (
                swing_id in weak_ids
            )

            result.append(
                SequenceSwing(
                    raw_swing=swing.raw_swing,
                    label=swing.label,
                    scope=swing.scope,
                    is_protected=is_protected,
                    is_strong=is_protected,
                    is_weak=is_weak,
                )
            )

        return result

    # ======================================================================
    # FIND FINAL ROLE OBJECT
    # ======================================================================

    def _find_swing(
        self,
        swings: List[SequenceSwing],
        target: Optional[SequenceSwing],
    ) -> Optional[SequenceSwing]:

        if target is None:
            return None

        target_id = target.raw_swing.swing_id

        for swing in swings:

            if swing.raw_swing.swing_id == target_id:
                return swing

        return None

    # ======================================================================
    # DEALING RANGE
    # ======================================================================

    def _calculate_dealing_range(
        self,
        swings: List[SequenceSwing],
        external_trend: TrendDirection,
        protected_high: Optional[SequenceSwing],
        protected_low: Optional[SequenceSwing],
        weak_high: Optional[SequenceSwing],
        weak_low: Optional[SequenceSwing],
    ) -> Optional[DealingRange]:

        external_highs = [
            swing
            for swing in swings
            if (
                swing.scope == SwingScope.EXTERNAL
                and swing.raw_swing.swing_type
                == SwingType.HIGH
            )
        ]

        external_lows = [
            swing
            for swing in swings
            if (
                swing.scope == SwingScope.EXTERNAL
                and swing.raw_swing.swing_type
                == SwingType.LOW
            )
        ]

        if external_trend == TrendDirection.BULLISH:

            if weak_high is None:

                return None

            # Active bullish dealing range:
            #
            # LOW  = latest causal protected low
            # HIGH = active weak expansion high
            #
            if protected_low is None:

                if not external_lows:
                    return None

                low_price = (
                    external_lows[-1]
                    .raw_swing.price
                )

            else:

                low_price = (
                    protected_low
                    .raw_swing.price
                )

            high_price = (
                weak_high.raw_swing.price
            )

        elif external_trend == TrendDirection.BEARISH:

            if weak_low is None:

                return None

            # Active bearish dealing range:
            #
            # HIGH = latest structural external high
            # LOW  = active weak expansion low
            #
            # IMPORTANT:
            # The protected high is the causal invalidation anchor.
            # The dealing-range high is the external structural
            # boundary. These are not necessarily the same swing.
            if not external_highs:
                return None

            high_price = (
                external_highs[0]
                .raw_swing.price
            )

            low_price = (
                weak_low.raw_swing.price
            )

        else:

            return None

        if high_price <= low_price:
            return None

        equilibrium = (
            low_price
            + (
                high_price
                - low_price
            ) / 2.0
        )

        return DealingRange(
            high_price=high_price,
            low_price=low_price,
            equilibrium_price=equilibrium,
        )

    # ======================================================================
    # TREND AT HISTORICAL CANDLE
    # ======================================================================

    def _trend_at_candle(
        self,
        swings: List[SequenceSwing],
        candle_index: int,
    ) -> TrendDirection:

        if candle_index < 0:
            return TrendDirection.NEUTRAL

        available = [
            swing
            for swing in swings
            if (
                swing.raw_swing.confirmation_index
                <= candle_index
            )
        ]

        return self._trend_from_sequence(
            available
        )

    # ======================================================================
    # EVENT REPLAY
    # ======================================================================

    def _replay_structural_events(
        self,
        classified_swings: List[SequenceSwing],
        labeled_swings: List[SequenceSwing],
        candles: List[Candle],
    ) -> List[StructureEvent]:

        if not candles:
            return []

        events = []

        external_swings = [
            swing
            for swing in classified_swings
            if swing.scope == SwingScope.EXTERNAL
        ]

        internal_swings = [
            swing
            for swing in classified_swings
            if swing.scope == SwingScope.INTERNAL
        ]

        targets = (
            external_swings
            + internal_swings
        )

        for target in targets:

            start_index = (
                target.raw_swing.confirmation_index
            )

            if start_index >= len(candles):
                continue

            level = (
                target.raw_swing.price
            )

            is_high = (
                target.raw_swing.swing_type
                == SwingType.HIGH
            )

            break_index = None

            # ----------------------------------------------------------
            # BODY-CLOSE BREAK
            # ----------------------------------------------------------

            for candle_index in range(
                start_index,
                len(candles),
            ):

                candle = candles[candle_index]

                bullish_break = (
                    is_high
                    and candle.close > level
                )

                bearish_break = (
                    not is_high
                    and candle.close < level
                )

                if not (
                    bullish_break
                    or bearish_break
                ):
                    continue

                break_index = candle_index

                prior_external_trend = (
                    self._trend_at_candle(
                        labeled_swings,
                        candle_index - 1,
                    )
                )

                internal_only = [
                    swing
                    for swing in classified_swings
                    if swing.scope
                    == SwingScope.INTERNAL
                ]

                prior_internal_trend = (
                    self._trend_at_candle(
                        internal_only,
                        candle_index - 1,
                    )
                )

                if (
                    target.scope
                    == SwingScope.EXTERNAL
                ):

                    if is_high:

                        if (
                            prior_external_trend
                            == TrendDirection.BULLISH
                        ):

                            event_type = (
                                EventType.EXTERNAL_BOS
                            )

                        else:

                            event_type = (
                                EventType.EXTERNAL_CHOCH
                            )

                        direction = "BULLISH"

                    else:

                        if (
                            prior_external_trend
                            == TrendDirection.BEARISH
                        ):

                            event_type = (
                                EventType.EXTERNAL_BOS
                            )

                        else:

                            event_type = (
                                EventType.EXTERNAL_CHOCH
                            )

                        direction = "BEARISH"

                else:

                    if (
                        is_high
                        and prior_external_trend
                        == TrendDirection.BEARISH
                    ):

                        event_type = EventType.MSS
                        direction = "BULLISH_MSS"

                    elif (
                        not is_high
                        and prior_external_trend
                        == TrendDirection.BULLISH
                    ):

                        event_type = EventType.MSS
                        direction = "BEARISH_MSS"

                    elif (
                        is_high
                        and prior_internal_trend
                        == TrendDirection.BULLISH
                    ):

                        event_type = (
                            EventType.INTERNAL_BOS
                        )

                        direction = (
                            "BULLISH_INTERNAL"
                        )

                    elif (
                        not is_high
                        and prior_internal_trend
                        == TrendDirection.BEARISH
                    ):

                        event_type = (
                            EventType.INTERNAL_BOS
                        )

                        direction = (
                            "BEARISH_INTERNAL"
                        )

                    else:

                        event_type = (
                            EventType.INTERNAL_CHOCH
                        )

                        direction = (
                            "BULLISH_INTERNAL"
                            if is_high
                            else "BEARISH_INTERNAL"
                        )

                self._emit(
                    events=events,
                    candle=candle,
                    event_type=event_type,
                    swing=target,
                    direction=direction,
                    candle_index=candle_index,
                )

                break

            # ----------------------------------------------------------
            # FAILED BOS / WICK REJECTION
            # ----------------------------------------------------------

            evaluation_end = (
                break_index
                if break_index is not None
                else len(candles)
            )

            for candle_index in range(
                start_index,
                evaluation_end,
            ):

                candle = candles[candle_index]

                wick_rejection = (
                    (
                        is_high
                        and candle.high > level
                        and candle.close <= level
                    )
                    or
                    (
                        not is_high
                        and candle.low < level
                        and candle.close >= level
                    )
                )

                if wick_rejection:

                    self._emit(
                        events=events,
                        candle=candle,
                        event_type=EventType.FAILED_BOS,
                        swing=target,
                        direction="REJECTION",
                        candle_index=candle_index,
                        confirmation="WICK_REJECTED",
                    )

        return sorted(
            events,
            key=lambda event: (
                event.candle_index,
                event.timestamp,
                event.event_type.value,
                event.broken_swing_id,
            ),
        )

    # ======================================================================
    # EVENT EMITTER
    # ======================================================================

    def _emit(
        self,
        events: List[StructureEvent],
        candle: Candle,
        event_type: EventType,
        swing: SequenceSwing,
        direction: str,
        candle_index: int,
        confirmation: str = "BODY_CLOSE",
    ) -> None:

        if (
            event_type
            == EventType.FAILED_BOS
        ):

            key = (
                event_type.value,
                swing.raw_swing.swing_id,
                candle_index,
            )

        else:

            key = (
                event_type.value,
                swing.raw_swing.swing_id,
            )

        if key in self._emitted_event_keys:
            return

        self._emitted_event_keys.add(key)

        self._structural_epoch += 1

        events.append(
            StructureEvent(
                timestamp=candle.timestamp,
                event_type=event_type,
                price_level=swing.raw_swing.price,
                broken_swing_id=swing.raw_swing.swing_id,
                direction=direction,
                candle_index=candle_index,
                confirmation=confirmation,
                structural_epoch=self._structural_epoch,
            )
        )


__all__ = [
    "SequenceLabel",
    "SwingScope",
    "TrendDirection",
    "EventType",
    "SequenceSwing",
    "StructureEvent",
    "DealingRange",
    "StructureState",
    "StructureBuilderEngine",
]
