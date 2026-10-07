"""
Product 01 — Market Language
Sub-System 1 — Market Structure Engine

Responsibilities:
    1. Raw swing detection
    2. Zero-lookahead confirmation tracking
    3. Internal/external hierarchy classification
    4. HH/HL/LH/LL/EQH/EQL sequence labeling
    5. External and internal trend evaluation
    6. Protected/strong and weak swing roles
    7. Dealing range/equilibrium
    8. EQH/EQL liquidity pools
    9. BOS / CHOCH / MSS
    10. Liquidity sweeps
    11. Inducement
    12. Failed BOS
    13. Full structure snapshot

Important:
This engine describes market structure.
It does NOT generate entries, positions, risk, orders, or execution.
"""

from typing import List, Optional, Tuple
import math

from market_intelligence.primitives import (
    Candle,
    RawSwing,
    SwingType,
    SwingStatus,
    SwingScope,
    SequenceLabel,
    SequenceSwing,
    SequenceState,
    TrendDirection,
    StructuralRole,
    MarketEvent,
    EventType,
    LiquiditySide,
    LiquidityPoolType,
    StructureState,
    DealingRange,
    EQHLiquidityPool,
)


class MarketStructureEngine:

    # ============================================================
    # 1. RAW SWINGS
    # ============================================================

    @staticmethod
    def detect_raw_swings(
        candles: List[Candle],
        lookback: int = 2,
        timeframe: str = "1H",
    ) -> List[RawSwing]:
        """
        Detect confirmed geometric swing highs/lows.

        A swing at index i becomes known only at:
            i + lookback

        Therefore the actual extreme timestamp and the confirmation
        timestamp are deliberately different.

        This is critical for backtesting.
        """

        if lookback < 1:
            raise ValueError("lookback must be >= 1")

        swings: List[RawSwing] = []

        n = len(candles)

        if n < (2 * lookback + 1):
            return swings

        for i in range(lookback, n - lookback):

            current = candles[i]

            values = (
                current.open,
                current.high,
                current.low,
                current.close,
            )

            if not all(math.isfinite(value) for value in values):
                continue

            is_high = True
            is_low = True

            for j in range(1, lookback + 1):

                left = candles[i - j]
                right = candles[i + j]

                # High must be strictly above left highs and
                # at least as high as right highs.
                if left.high >= current.high:
                    is_high = False

                if right.high > current.high:
                    is_high = False

                # Low must be strictly below left lows and
                # at least as low as right lows.
                if left.low <= current.low:
                    is_low = False

                if right.low < current.low:
                    is_low = False

            confirmation_index = i + lookback
            confirmation_timestamp = candles[confirmation_index].timestamp

            if is_high:

                swings.append(
                    RawSwing(
                        swing_id=f"SW_HIGH_{i}",
                        timestamp=current.timestamp,
                        price=current.high,
                        swing_type=SwingType.SWING_HIGH,
                        candle_index=i,
                        confirmation_timestamp=confirmation_timestamp,
                        confirmation_index=confirmation_index,
                        timeframe=timeframe,
                        status=SwingStatus.CONFIRMED,
                        scope=SwingScope.INTERNAL,
                    )
                )

            elif is_low:

                swings.append(
                    RawSwing(
                        swing_id=f"SW_LOW_{i}",
                        timestamp=current.timestamp,
                        price=current.low,
                        swing_type=SwingType.SWING_LOW,
                        candle_index=i,
                        confirmation_timestamp=confirmation_timestamp,
                        confirmation_index=confirmation_index,
                        timeframe=timeframe,
                        status=SwingStatus.CONFIRMED,
                        scope=SwingScope.INTERNAL,
                    )
                )

        return swings

    # ============================================================
    # 2. HIERARCHICAL INTERNAL / EXTERNAL STRUCTURE
    # ============================================================

    @staticmethod
    def classify_hierarchical_structure(
        raw_swings: List[RawSwing],
        external_span: int = 2,
    ) -> List[RawSwing]:
        """
        Assigns a deterministic hierarchy to confirmed swings.

        IMPORTANT ARCHITECTURAL PRINCIPLE:

        Internal vs external is not an absolute market property.
        It is a structural scale.

        Therefore the engine exposes `external_span` explicitly
        instead of pretending that a universal percentage can define
        institutional structure.

        external_span=2 means an external pivot must dominate the
        surrounding same-type pivots across that structural window.

        Swings not qualifying at that scale remain INTERNAL.

        Only already-confirmed swings are considered.
        """

        if external_span < 1:
            raise ValueError("external_span must be >= 1")

        if not raw_swings:
            return []

        result = list(raw_swings)

        highs = [
            (index, swing)
            for index, swing in enumerate(result)
            if swing.swing_type == SwingType.SWING_HIGH
        ]

        lows = [
            (index, swing)
            for index, swing in enumerate(result)
            if swing.swing_type == SwingType.SWING_LOW
        ]

        def classify_group(group):

            for position, (raw_index, swing) in enumerate(group):

                start = max(0, position - external_span)
                end = min(len(group), position + external_span + 1)

                neighborhood = [
                    item[1]
                    for item in group[start:end]
                    if item[1].swing_id != swing.swing_id
                ]

                if not neighborhood:
                    swing.scope = SwingScope.EXTERNAL
                    continue

                if swing.swing_type == SwingType.SWING_HIGH:

                    is_dominant = all(
                        swing.price >= other.price
                        for other in neighborhood
                    )

                else:

                    is_dominant = all(
                        swing.price <= other.price
                        for other in neighborhood
                    )

                if is_dominant:
                    swing.scope = SwingScope.EXTERNAL
                else:
                    swing.scope = SwingScope.INTERNAL

        classify_group(highs)
        classify_group(lows)

        # The first confirmed swing at a scale is an anchor.
        if result:
            result[0].scope = SwingScope.EXTERNAL

        return result

    # ============================================================
    # 3. SEQUENCE LABELS
    # ============================================================

    @staticmethod
    def sequence_swings(
        raw_swings: List[RawSwing],
        eq_tolerance_pct: float = 0.0005,
    ) -> SequenceState:
        """
        Labels same-type swings:

        HIGH:
            HH / LH / EQH

        LOW:
            HL / LL / EQL
        """

        if eq_tolerance_pct < 0:
            raise ValueError("eq_tolerance_pct must be >= 0")

        if not raw_swings:
            return SequenceState(
                sequence_swings=[],
                total_swings=0,
            )

        sequence_swings: List[SequenceSwing] = []

        latest_high: Optional[SequenceSwing] = None
        previous_high: Optional[SequenceSwing] = None

        latest_low: Optional[SequenceSwing] = None
        previous_low: Optional[SequenceSwing] = None

        latest_external_high: Optional[SequenceSwing] = None
        latest_external_low: Optional[SequenceSwing] = None

        latest_internal_high: Optional[SequenceSwing] = None
        latest_internal_low: Optional[SequenceSwing] = None

        for raw in raw_swings:

            if raw.swing_type == SwingType.SWING_HIGH:

                previous_high = latest_high

                if latest_high is None:

                    label = SequenceLabel.UNKNOWN

                else:

                    previous_price = latest_high.raw_swing.price

                    diff_pct = (
                        abs(raw.price - previous_price)
                        / previous_price
                    )

                    if diff_pct <= eq_tolerance_pct:
                        label = SequenceLabel.EQH

                    elif raw.price > previous_price:
                        label = SequenceLabel.HH

                    else:
                        label = SequenceLabel.LH

                seq = SequenceSwing(
                    raw_swing=raw,
                    label=label,
                )

                latest_high = seq

                if raw.scope == SwingScope.EXTERNAL:
                    latest_external_high = seq
                else:
                    latest_internal_high = seq

            else:

                previous_low = latest_low

                if latest_low is None:

                    label = SequenceLabel.UNKNOWN

                else:

                    previous_price = latest_low.raw_swing.price

                    diff_pct = (
                        abs(raw.price - previous_price)
                        / previous_price
                    )

                    if diff_pct <= eq_tolerance_pct:
                        label = SequenceLabel.EQL

                    elif raw.price > previous_price:
                        label = SequenceLabel.HL

                    else:
                        label = SequenceLabel.LL

                seq = SequenceSwing(
                    raw_swing=raw,
                    label=label,
                )

                latest_low = seq

                if raw.scope == SwingScope.EXTERNAL:
                    latest_external_low = seq
                else:
                    latest_internal_low = seq

            sequence_swings.append(seq)

        return SequenceState(
            sequence_swings=sequence_swings,

            latest_high=latest_high,
            previous_high=previous_high,

            latest_low=latest_low,
            previous_low=previous_low,

            latest_external_high=latest_external_high,
            latest_external_low=latest_external_low,

            latest_internal_high=latest_internal_high,
            latest_internal_low=latest_internal_low,

            total_swings=len(sequence_swings),
        )

    # ============================================================
    # 4. TREND
    # ============================================================

    @staticmethod
    def determine_trend(
        sequence_state: SequenceState,
        scope: SwingScope = SwingScope.EXTERNAL,
    ) -> TrendDirection:
        """
        Determines trend from the selected structural hierarchy.

        External trend and internal trend are deliberately separate.

        Bullish:
            HH + HL

        Bearish:
            LH + LL

        Otherwise:
            RANGING / NEUTRAL
        """

        if scope == SwingScope.EXTERNAL:

            high = sequence_state.latest_external_high
            low = sequence_state.latest_external_low

        else:

            high = sequence_state.latest_internal_high
            low = sequence_state.latest_internal_low

        if high is None or low is None:
            return TrendDirection.NEUTRAL

        if high.label == SequenceLabel.HH and low.label == SequenceLabel.HL:
            return TrendDirection.BULLISH

        if high.label == SequenceLabel.LH and low.label == SequenceLabel.LL:
            return TrendDirection.BEARISH

        if high.label in (SequenceLabel.EQH, SequenceLabel.UNKNOWN):
            if low.label in (SequenceLabel.EQL, SequenceLabel.UNKNOWN):
                return TrendDirection.RANGING

        if low.label in (SequenceLabel.EQL, SequenceLabel.UNKNOWN):
            if high.label in (SequenceLabel.EQH, SequenceLabel.UNKNOWN):
                return TrendDirection.RANGING

        return TrendDirection.RANGING

    # ============================================================
    # 5. PROTECTED / WEAK SWINGS
    # ============================================================

    @staticmethod
    def assign_structural_roles(
        sequence_state: SequenceState,
        trend: TrendDirection,
    ) -> Tuple[
        Optional[SequenceSwing],
        Optional[SequenceSwing],
        Optional[SequenceSwing],
        Optional[SequenceSwing],
    ]:
        """
        Assigns structural roles from the current external sequence.

        Bullish:
            protected low = latest structural low
            weak high     = latest structural high

        Bearish:
            protected high = latest structural high
            weak low       = latest structural low

        This is a snapshot-level role assignment.

        A future stateful layer can preserve historical role transitions
        across candles.
        """

        protected_high = None
        protected_low = None
        weak_high = None
        weak_low = None

        if trend == TrendDirection.BULLISH:

            protected_low = sequence_state.latest_external_low
            weak_high = sequence_state.latest_external_high

            if protected_low:

                protected_low.role = StructuralRole.PROTECTED_LOW
                protected_low.is_protected = True
                protected_low.is_strong = True

                protected_low.raw_swing.status = SwingStatus.PROTECTED

            if weak_high:

                weak_high.role = StructuralRole.WEAK_HIGH
                weak_high.is_weak = True

                weak_high.raw_swing.status = SwingStatus.WEAK

        elif trend == TrendDirection.BEARISH:

            protected_high = sequence_state.latest_external_high
            weak_low = sequence_state.latest_external_low

            if protected_high:

                protected_high.role = StructuralRole.PROTECTED_HIGH
                protected_high.is_protected = True
                protected_high.is_strong = True

                protected_high.raw_swing.status = SwingStatus.PROTECTED

            if weak_low:

                weak_low.role = StructuralRole.WEAK_LOW
                weak_low.is_weak = True

                weak_low.raw_swing.status = SwingStatus.WEAK

        return (
            protected_high,
            protected_low,
            weak_high,
            weak_low,
        )

    # ============================================================
    # 6. DEALING RANGE
    # ============================================================

    @staticmethod
    def calculate_dealing_range(
        protected_high: Optional[SequenceSwing],
        protected_low: Optional[SequenceSwing],
    ) -> Optional[DealingRange]:

        if protected_high is None or protected_low is None:
            return None

        high_price = protected_high.raw_swing.price
        low_price = protected_low.raw_swing.price

        if high_price <= low_price:
            return None

        equilibrium = low_price + (
            (high_price - low_price) / 2.0
        )

        return DealingRange(
            high_swing=protected_high,
            low_swing=protected_low,
            equilibrium_price=equilibrium,
        )

    # ============================================================
    # 7. EQH / EQL LIQUIDITY
    # ============================================================

    @staticmethod
    def detect_eqh_eql_liquidity(
        sequence_swings: List[SequenceSwing],
        tolerance_pct: float = 0.0005,
    ) -> List[EQHLiquidityPool]:
        """
        Detects equal highs/lows.

        0.0005 = 0.05%.

        Pools are generated from actual structural swings.
        """

        if tolerance_pct < 0:
            raise ValueError("tolerance_pct must be >= 0")

        pools: List[EQHLiquidityPool] = []

        highs = [
            swing
            for swing in sequence_swings
            if swing.raw_swing.swing_type == SwingType.SWING_HIGH
        ]

        lows = [
            swing
            for swing in sequence_swings
            if swing.raw_swing.swing_type == SwingType.SWING_LOW
        ]

        def build_pools(
            swings: List[SequenceSwing],
            pool_type: LiquidityPoolType,
            prefix: str,
        ):

            local_pools = []

            for i in range(len(swings)):

                anchor = swings[i]

                members = [anchor]

                for j in range(i + 1, len(swings)):

                    candidate = swings[j]

                    anchor_price = anchor.raw_swing.price
                    candidate_price = candidate.raw_swing.price

                    difference = (
                        abs(candidate_price - anchor_price)
                        / anchor_price
                    )

                    if difference <= tolerance_pct:
                        members.append(candidate)

                if len(members) >= 2:

                    price_level = sum(
                        member.raw_swing.price
                        for member in members
                    ) / len(members)

                    pool_id = (
                        f"{prefix}_"
                        f"{members[0].raw_swing.swing_id}_"
                        f"{members[-1].raw_swing.swing_id}"
                    )

                    local_pools.append(
                        EQHLiquidityPool(
                            pool_id=pool_id,
                            pool_type=pool_type,
                            price_level=price_level,
                            swings=members,
                            tolerance_pct=tolerance_pct,
                        )
                    )

            return local_pools

        pools.extend(
            build_pools(
                highs,
                LiquidityPoolType.EQH,
                "EQH",
            )
        )

        pools.extend(
            build_pools(
                lows,
                LiquidityPoolType.EQL,
                "EQL",
            )
        )

        return pools

    # ============================================================
    # 8. LIQUIDITY SWEEP
    # ============================================================

    @staticmethod
    def detect_liquidity_sweep(
        candle: Candle,
        level: float,
        side: LiquiditySide,
    ) -> bool:
        """
        Sweep definition:

        BSL:
            high > level
            close <= level

        SSL:
            low < level
            close >= level
        """

        if side == LiquiditySide.BSL:

            return (
                candle.high > level
                and candle.close <= level
            )

        return (
            candle.low < level
            and candle.close >= level
        )

    # ============================================================
    # 9. STRUCTURAL EVENTS
    # ============================================================

    @classmethod
    def evaluate_structure_events(
        cls,
        candles: List[Candle],
        sequence_state: SequenceState,
        current_trend: TrendDirection,
        symbol: str = "BTC/USDT",
        timeframe: str = "1H",
    ) -> List[MarketEvent]:
        """
        Detects structural events from the latest candle.

        The engine distinguishes:

        BOS:
            continuation through structural target.

        CHOCH:
            break of opposing external structural level.

        MSS:
            internal structural shift.

        Sweep:
            wick crosses level but close returns inside.

        Failed BOS:
            breakout attempt through structural level fails
            and closes back inside.

        Inducement:
            internal liquidity is swept against current direction.
        """

        if not candles:
            return []

        latest_candle = candles[-1]

        events: List[MarketEvent] = []

        external_high = sequence_state.latest_external_high
        external_low = sequence_state.latest_external_low

        internal_high = sequence_state.latest_internal_high
        internal_low = sequence_state.latest_internal_low

        # --------------------------------------------------------
        # BULLISH-SIDE LEVEL
        # --------------------------------------------------------

        if external_high:

            level = external_high.raw_swing.price

            # Continuation
            if latest_candle.close > level:

                if current_trend == TrendDirection.BULLISH:

                    event_type = EventType.EXTERNAL_BOS

                else:

                    event_type = EventType.EXTERNAL_CHOCH

                events.append(
                    MarketEvent(
                        timestamp=latest_candle.timestamp,
                        timeframe=timeframe,
                        symbol=symbol,
                        event_type=event_type,
                        price_level=level,
                        metadata={
                            "direction": "BULLISH",
                            "scope": "EXTERNAL",
                            "broken_swing_id":
                                external_high.raw_swing.swing_id,
                        },
                    )
                )

            # Sweep / failed breakout
            elif cls.detect_liquidity_sweep(
                latest_candle,
                level,
                LiquiditySide.BSL,
            ):

                events.append(
                    MarketEvent(
                        timestamp=latest_candle.timestamp,
                        timeframe=timeframe,
                        symbol=symbol,
                        event_type=EventType.LIQUIDITY_SWEEP,
                        price_level=level,
                        metadata={
                            "direction": "BEARISH",
                            "liquidity_side": LiquiditySide.BSL.value,
                            "scope": "EXTERNAL",
                        },
                    )
                )

                events.append(
                    MarketEvent(
                        timestamp=latest_candle.timestamp,
                        timeframe=timeframe,
                        symbol=symbol,
                        event_type=EventType.FAILED_BOS,
                        price_level=level,
                        metadata={
                            "direction": "BULLISH",
                            "reason":
                                "Price traded above structural high "
                                "but closed back below/at it.",
                            "broken_swing_id":
                                external_high.raw_swing.swing_id,
                        },
                    )
                )

        # --------------------------------------------------------
        # BEARISH-SIDE LEVEL
        # --------------------------------------------------------

        if external_low:

            level = external_low.raw_swing.price

            if latest_candle.close < level:

                if current_trend == TrendDirection.BEARISH:

                    event_type = EventType.EXTERNAL_BOS

                else:

                    event_type = EventType.EXTERNAL_CHOCH

                events.append(
                    MarketEvent(
                        timestamp=latest_candle.timestamp,
                        timeframe=timeframe,
                        symbol=symbol,
                        event_type=event_type,
                        price_level=level,
                        metadata={
                            "direction": "BEARISH",
                            "scope": "EXTERNAL",
                            "broken_swing_id":
                                external_low.raw_swing.swing_id,
                        },
                    )
                )

            elif cls.detect_liquidity_sweep(
                latest_candle,
                level,
                LiquiditySide.SSL,
            ):

                events.append(
                    MarketEvent(
                        timestamp=latest_candle.timestamp,
                        timeframe=timeframe,
                        symbol=symbol,
                        event_type=EventType.LIQUIDITY_SWEEP,
                        price_level=level,
                        metadata={
                            "direction": "BULLISH",
                            "liquidity_side": LiquiditySide.SSL.value,
                            "scope": "EXTERNAL",
                        },
                    )
                )

                events.append(
                    MarketEvent(
                        timestamp=latest_candle.timestamp,
                        timeframe=timeframe,
                        symbol=symbol,
                        event_type=EventType.FAILED_BOS,
                        price_level=level,
                        metadata={
                            "direction": "BEARISH",
                            "reason":
                                "Price traded below structural low "
                                "but closed back above/at it.",
                            "broken_swing_id":
                                external_low.raw_swing.swing_id,
                        },
                    )
                )

        # --------------------------------------------------------
        # INTERNAL MSS
        # --------------------------------------------------------

        if internal_high:

            level = internal_high.raw_swing.price

            if (
                current_trend == TrendDirection.BEARISH
                and latest_candle.close > level
            ):

                events.append(
                    MarketEvent(
                        timestamp=latest_candle.timestamp,
                        timeframe=timeframe,
                        symbol=symbol,
                        event_type=EventType.MSS,
                        price_level=level,
                        metadata={
                            "direction": "BULLISH",
                            "scope": "INTERNAL",
                            "broken_swing_id":
                                internal_high.raw_swing.swing_id,
                        },
                    )
                )

        if internal_low:

            level = internal_low.raw_swing.price

            if (
                current_trend == TrendDirection.BULLISH
                and latest_candle.close < level
            ):

                events.append(
                    MarketEvent(
                        timestamp=latest_candle.timestamp,
                        timeframe=timeframe,
                        symbol=symbol,
                        event_type=EventType.MSS,
                        price_level=level,
                        metadata={
                            "direction": "BEARISH",
                            "scope": "INTERNAL",
                            "broken_swing_id":
                                internal_low.raw_swing.swing_id,
                        },
                    )
                )

        # --------------------------------------------------------
        # INTERNAL LIQUIDITY / INDUCEMENT
        # --------------------------------------------------------

        if current_trend == TrendDirection.BULLISH and internal_low:

            level = internal_low.raw_swing.price

            if cls.detect_liquidity_sweep(
                latest_candle,
                level,
                LiquiditySide.SSL,
            ):

                events.append(
                    MarketEvent(
                        timestamp=latest_candle.timestamp,
                        timeframe=timeframe,
                        symbol=symbol,
                        event_type=EventType.INDUCEMENT,
                        price_level=level,
                        metadata={
                            "direction": "BULLISH",
                            "liquidity_side": "SSL",
                            "internal_swing_id":
                                internal_low.raw_swing.swing_id,
                        },
                    )
                )

        if current_trend == TrendDirection.BEARISH and internal_high:

            level = internal_high.raw_swing.price

            if cls.detect_liquidity_sweep(
                latest_candle,
                level,
                LiquiditySide.BSL,
            ):

                events.append(
                    MarketEvent(
                        timestamp=latest_candle.timestamp,
                        timeframe=timeframe,
                        symbol=symbol,
                        event_type=EventType.INDUCEMENT,
                        price_level=level,
                        metadata={
                            "direction": "BEARISH",
                            "liquidity_side": "BSL",
                            "internal_swing_id":
                                internal_high.raw_swing.swing_id,
                        },
                    )
                )

        return events

    # ============================================================
    # 10. FULL STRUCTURE SNAPSHOT
    # ============================================================

    @classmethod
    def process_full_structure(
        cls,
        candles: List[Candle],
        symbol: str = "BTC/USDT",
        timeframe: str = "1H",
        lookback: int = 2,
        external_span: int = 2,
        eq_tolerance_pct: float = 0.0005,
    ) -> StructureState:
        """
        Complete structure pipeline:

            candles
               ↓
            raw swings
               ↓
            hierarchy
               ↓
            sequence
               ↓
            external trend
               ↓
            internal trend
               ↓
            structural roles
               ↓
            dealing range
        """

        raw_swings = cls.detect_raw_swings(
            candles=candles,
            lookback=lookback,
            timeframe=timeframe,
        )

        classified_swings = cls.classify_hierarchical_structure(
            raw_swings,
            external_span=external_span,
        )

        sequence_state = cls.sequence_swings(
            classified_swings,
            eq_tolerance_pct=eq_tolerance_pct,
        )

        external_trend = cls.determine_trend(
            sequence_state,
            scope=SwingScope.EXTERNAL,
        )

        internal_trend = cls.determine_trend(
            sequence_state,
            scope=SwingScope.INTERNAL,
        )

        (
            protected_high,
            protected_low,
            weak_high,
            weak_low,
        ) = cls.assign_structural_roles(
            sequence_state,
            external_trend,
        )

        dealing_range = cls.calculate_dealing_range(
            protected_high,
            protected_low,
        )

        external_swings = [
            swing
            for swing in sequence_state.sequence_swings
            if swing.raw_swing.scope == SwingScope.EXTERNAL
        ]

        internal_swings = [
            swing
            for swing in sequence_state.sequence_swings
            if swing.raw_swing.scope == SwingScope.INTERNAL
        ]

        events = cls.evaluate_structure_events(
            candles=candles,
            sequence_state=sequence_state,
            current_trend=external_trend,
            symbol=symbol,
            timeframe=timeframe,
        )

        last_event = events[-1] if events else None

        return StructureState(
            external_trend=external_trend,

            internal_trend=internal_trend,

            external_swings=external_swings,

            internal_swings=internal_swings,

            protected_high=protected_high,

            protected_low=protected_low,

            weak_high=weak_high,

            weak_low=weak_low,

            dealing_range=dealing_range,

            last_event=last_event,
        )
