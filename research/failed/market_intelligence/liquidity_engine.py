"""
Quantitative Systems Platform
Product 01: Crypto Platform
Market Language — Engine 3: Liquidity Intelligence Engine

VERSION
-------
Engine 3 Hardened / Lifecycle-Verified

RESPONSIBILITY
--------------
Consumes confirmed SequenceSwing objects from Engine 2 and sequential Candle
history.

Produces ONLY market-liquidity intelligence:

    • EQH — Equal High liquidity pools
    • EQL — Equal Low liquidity pools
    • BSL — Buy-Side Liquidity anchors
    • SSL — Sell-Side Liquidity anchors
    • External / Internal liquidity classification
    • Liquidity sweep events
    • Internal-liquidity inducement classification
    • Pool lifecycle:

          ACTIVE -> SWEPT -> CONSUMED

STRICT BOUNDARY
--------------
This engine MUST NOT know about:

    • Order Blocks
    • Fair Value Gaps
    • Keyzones
    • Market Phase
    • Trading strategies
    • BUY / SELL signals
    • Entry models
    • Stop Loss
    • Take Profit
    • Position sizing
    • Broker APIs
    • Execution

SOURCE CONTRACT
---------------
The source specification defines liquidity as the layer that converts
structural equalities / swing liquidity into liquidity objects and identifies
wick penetration followed by body rejection.

NO LOOKAHEAD
------------
A liquidity pool may only be evaluated from the confirmation index of its
latest contributing swing onward.

POOL TERMINALITY
----------------
Once a pool becomes CONSUMED, it can never return to ACTIVE or SWEPT within
that processing pass.

BODY GEOMETRY
-------------
For high-side liquidity:

    valid sweep:
        candle.high > boundary
        AND
        max(open, close) <= boundary

    consumed:
        open > boundary OR close > boundary

For low-side liquidity:

    valid sweep:
        candle.low < boundary
        AND
        min(open, close) >= boundary

    consumed:
        open < boundary OR close < boundary

A wick that merely touches the boundary is NOT a sweep.

A candle body that straddles the boundary is NOT a sweep.

A candle opening beyond the boundary is treated as a broken/consumed pool.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Set, Tuple

from market_intelligence.raw_swing_engine import Candle, SwingType
from market_intelligence.structure_builder_engine import (
    SequenceSwing,
    SwingScope,
    TrendDirection,
)


# ============================================================================
# ENUMS
# ============================================================================


class LiquidityPoolType(Enum):
    EQH = "EQH"
    EQL = "EQL"
    BSL = "BSL"
    SSL = "SSL"


class LiquidityScope(Enum):
    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"


class PoolStatus(Enum):
    ACTIVE = "ACTIVE"
    SWEPT = "SWEPT"
    CONSUMED = "CONSUMED"


class LiquidityEventType(Enum):
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
    INDUCEMENT = "INDUCEMENT"


# ============================================================================
# DATA CONTRACTS
# ============================================================================


@dataclass(frozen=True)
class LiquidityPool:
    """
    Immutable representation of one liquidity pool.

    status is the final lifecycle state for the current processing pass.

    sweep_count records the number of valid wick sweeps observed before
    consumption, if consumption occurs.
    """

    pool_id: str
    pool_type: LiquidityPoolType

    price_level: float

    high_boundary: float
    low_boundary: float

    swings: List[SequenceSwing]

    creation_timestamp: int

    status: PoolStatus = PoolStatus.ACTIVE

    scope: LiquidityScope = LiquidityScope.EXTERNAL

    sweep_count: int = 0


@dataclass(frozen=True)
class LiquidityEvent:
    """
    Immutable event emitted by Engine 3.

    Event geometry fields are derived from the candle that actually produced
    the event. They are not caller-controlled semantic flags.
    """

    timestamp: int

    event_type: LiquidityEventType

    pool_id: str

    pool_type: LiquidityPoolType

    liquidity_scope: LiquidityScope

    price_level: float

    direction: str

    candle_index: int

    swept_by_wick: bool

    body_closed_inside: bool


@dataclass
class LiquidityState:
    """
    Complete Engine 3 output state.

    Events represent newly emitted sweep/inducement events for the current
    stateful engine instance.
    """

    active_pools: List[LiquidityPool]

    swept_pools: List[LiquidityPool]

    consumed_pools: List[LiquidityPool]

    events: List[LiquidityEvent]


# ============================================================================
# INTERNAL CANDLE DECISION CONTRACT
# ============================================================================


@dataclass(frozen=True)
class _SweepDecision:
    """
    Internal geometry decision.

    This prevents event construction from manually asserting that a candle
    was a sweep.
    """

    is_consumed: bool
    is_sweep: bool

    swept_by_wick: bool
    body_closed_inside: bool


# ============================================================================
# ENGINE 3
# ============================================================================


class LiquidityEngine:
    """
    Deterministic, stateful Liquidity Intelligence Engine.

    Lifecycle:

        ACTIVE
           |
           | wick penetration + body rejection
           v
        SWEPT
           |
           | later body crosses boundary
           v
        CONSUMED

    A consumed pool is terminal.

    Event emission is deduplicated across repeated process() calls using:

        (event_type, pool_id, candle_index)
    """

    def __init__(
        self,
        eq_tolerance_pct: float = 0.0005,
        boundary_epsilon: float = 0.0,
    ) -> None:

        if eq_tolerance_pct < 0:
            raise ValueError("eq_tolerance_pct must be >= 0")

        if boundary_epsilon < 0:
            raise ValueError("boundary_epsilon must be >= 0")

        self.eq_tolerance_pct = eq_tolerance_pct

        self.boundary_epsilon = boundary_epsilon

        self._emitted_event_keys: Set[Tuple] = set()

    # ------------------------------------------------------------------------
    # STATE CONTROL
    # ------------------------------------------------------------------------

    def reset(self) -> None:
        """
        Reset event-emission memory.

        Pool detection itself remains deterministic and stateless per process
        call. Only duplicate-event memory is reset here.
        """

        self._emitted_event_keys.clear()

    # ------------------------------------------------------------------------
    # PUBLIC PROCESSOR
    # ------------------------------------------------------------------------

    def process(
        self,
        swings: List[SequenceSwing],
        candles: List[Candle],
        external_trend: TrendDirection = TrendDirection.NEUTRAL,
    ) -> LiquidityState:
        """
        Build liquidity pools and evaluate their candle lifecycle.

        Causal rule:

            pool evaluation begins at the confirmation index of the latest
            swing contributing to that pool.

        Therefore candles occurring before pool confirmation cannot generate
        liquidity events for that pool.
        """

        if not swings:
            return LiquidityState(
                active_pools=[],
                swept_pools=[],
                consumed_pools=[],
                events=[],
            )

        # ------------------------------------------------------------------
        # 1. Detect equal-high / equal-low pools.
        # ------------------------------------------------------------------

        eq_pools = self._detect_eq_pools(swings)

        # ------------------------------------------------------------------
        # 2. Detect structural swing liquidity.
        # ------------------------------------------------------------------

        structural_pools = self._detect_structural_pools(swings)

        # ------------------------------------------------------------------
        # 3. Merge without duplicate pool IDs.
        # ------------------------------------------------------------------

        all_pools = self._deduplicate_pools(
            eq_pools + structural_pools
        )

        # ------------------------------------------------------------------
        # 4. Evaluate lifecycle.
        # ------------------------------------------------------------------

        (
            active_pools,
            swept_pools,
            consumed_pools,
            events,
        ) = self._evaluate_pool_sweeps(
            all_pools=all_pools,
            candles=candles,
            external_trend=external_trend,
        )

        return LiquidityState(
            active_pools=active_pools,
            swept_pools=swept_pools,
            consumed_pools=consumed_pools,
            events=events,
        )

    # =========================================================================
    # EQH / EQL DETECTION
    # =========================================================================

    def _detect_eq_pools(
        self,
        swings: List[SequenceSwing],
    ) -> List[LiquidityPool]:

        pools: List[LiquidityPool] = []

        highs = [
            s
            for s in swings
            if s.raw_swing.swing_type == SwingType.HIGH
        ]

        lows = [
            s
            for s in swings
            if s.raw_swing.swing_type == SwingType.LOW
        ]

        # ------------------------------------------------------------------
        # Equal Highs
        # ------------------------------------------------------------------

        for i in range(len(highs)):

            anchor = highs[i]

            cluster = [anchor]

            for j in range(i + 1, len(highs)):

                candidate = highs[j]

                if anchor.raw_swing.price <= 0:
                    continue

                diff = (
                    abs(
                        candidate.raw_swing.price
                        - anchor.raw_swing.price
                    )
                    / anchor.raw_swing.price
                )

                if diff <= self.eq_tolerance_pct:
                    cluster.append(candidate)

            if len(cluster) >= 2:

                avg_price = (
                    sum(
                        s.raw_swing.price
                        for s in cluster
                    )
                    / len(cluster)
                )

                pool_id = (
                    f"EQH_"
                    f"{cluster[0].raw_swing.swing_id}_"
                    f"{cluster[-1].raw_swing.swing_id}"
                )

                pools.append(
                    LiquidityPool(
                        pool_id=pool_id,
                        pool_type=LiquidityPoolType.EQH,
                        price_level=avg_price,
                        high_boundary=max(
                            s.raw_swing.price
                            for s in cluster
                        ),
                        low_boundary=min(
                            s.raw_swing.price
                            for s in cluster
                        ),
                        swings=cluster,
                        creation_timestamp=cluster[-1]
                        .raw_swing.timestamp,
                        status=PoolStatus.ACTIVE,
                        scope=LiquidityScope.EXTERNAL,
                    )
                )

        # ------------------------------------------------------------------
        # Equal Lows
        # ------------------------------------------------------------------

        for i in range(len(lows)):

            anchor = lows[i]

            cluster = [anchor]

            for j in range(i + 1, len(lows)):

                candidate = lows[j]

                if anchor.raw_swing.price <= 0:
                    continue

                diff = (
                    abs(
                        candidate.raw_swing.price
                        - anchor.raw_swing.price
                    )
                    / anchor.raw_swing.price
                )

                if diff <= self.eq_tolerance_pct:
                    cluster.append(candidate)

            if len(cluster) >= 2:

                avg_price = (
                    sum(
                        s.raw_swing.price
                        for s in cluster
                    )
                    / len(cluster)
                )

                pool_id = (
                    f"EQL_"
                    f"{cluster[0].raw_swing.swing_id}_"
                    f"{cluster[-1].raw_swing.swing_id}"
                )

                pools.append(
                    LiquidityPool(
                        pool_id=pool_id,
                        pool_type=LiquidityPoolType.EQL,
                        price_level=avg_price,
                        high_boundary=max(
                            s.raw_swing.price
                            for s in cluster
                        ),
                        low_boundary=min(
                            s.raw_swing.price
                            for s in cluster
                        ),
                        swings=cluster,
                        creation_timestamp=cluster[-1]
                        .raw_swing.timestamp,
                        status=PoolStatus.ACTIVE,
                        scope=LiquidityScope.EXTERNAL,
                    )
                )

        return pools

    # =========================================================================
    # STRUCTURAL LIQUIDITY
    # =========================================================================

    def _detect_structural_pools(
        self,
        swings: List[SequenceSwing],
    ) -> List[LiquidityPool]:

        pools: List[LiquidityPool] = []

        for swing in swings:

            if swing.raw_swing.swing_type == SwingType.HIGH:

                pool_type = LiquidityPoolType.BSL

            else:

                pool_type = LiquidityPoolType.SSL

            if swing.scope == SwingScope.EXTERNAL:

                pool_scope = LiquidityScope.EXTERNAL

            else:

                pool_scope = LiquidityScope.INTERNAL

            pool_id = (
                f"{pool_type.value}_"
                f"{swing.raw_swing.swing_id}"
            )

            price = swing.raw_swing.price

            pools.append(
                LiquidityPool(
                    pool_id=pool_id,
                    pool_type=pool_type,
                    price_level=price,
                    high_boundary=price,
                    low_boundary=price,
                    swings=[swing],
                    creation_timestamp=swing.raw_swing.timestamp,
                    status=PoolStatus.ACTIVE,
                    scope=pool_scope,
                )
            )

        return pools

    # =========================================================================
    # POOL DEDUPLICATION
    # =========================================================================

    def _deduplicate_pools(
        self,
        pools: List[LiquidityPool],
    ) -> List[LiquidityPool]:

        seen_ids: Set[str] = set()

        unique: List[LiquidityPool] = []

        for pool in pools:

            if pool.pool_id in seen_ids:
                continue

            seen_ids.add(pool.pool_id)

            unique.append(pool)

        return unique

    # =========================================================================
    # CANDLE GEOMETRY
    # =========================================================================

    def _evaluate_high_side_candle(
        self,
        candle: Candle,
        boundary: float,
    ) -> _SweepDecision:
        """
        Evaluate BSL / EQH geometry.

        Consumed:
            open > boundary
            OR
            close > boundary

        Sweep:
            high > boundary
            AND
            entire body <= boundary
        """

        upper = boundary + self.boundary_epsilon

        body_top = max(
            candle.open,
            candle.close,
        )

        body_crossed = (
            candle.open > upper
            or candle.close > upper
        )

        if body_crossed:

            return _SweepDecision(
                is_consumed=True,
                is_sweep=False,
                swept_by_wick=False,
                body_closed_inside=False,
            )

        wick_penetrated = candle.high > upper

        if wick_penetrated and body_top <= upper:

            return _SweepDecision(
                is_consumed=False,
                is_sweep=True,
                swept_by_wick=True,
                body_closed_inside=True,
            )

        return _SweepDecision(
            is_consumed=False,
            is_sweep=False,
            swept_by_wick=False,
            body_closed_inside=True,
        )

    def _evaluate_low_side_candle(
        self,
        candle: Candle,
        boundary: float,
    ) -> _SweepDecision:
        """
        Evaluate SSL / EQL geometry.

        Consumed:
            open < boundary
            OR
            close < boundary

        Sweep:
            low < boundary
            AND
            entire body >= boundary
        """

        lower = boundary - self.boundary_epsilon

        body_bottom = min(
            candle.open,
            candle.close,
        )

        body_crossed = (
            candle.open < lower
            or candle.close < lower
        )

        if body_crossed:

            return _SweepDecision(
                is_consumed=True,
                is_sweep=False,
                swept_by_wick=False,
                body_closed_inside=False,
            )

        wick_penetrated = candle.low < lower

        if wick_penetrated and body_bottom >= lower:

            return _SweepDecision(
                is_consumed=False,
                is_sweep=True,
                swept_by_wick=True,
                body_closed_inside=True,
            )

        return _SweepDecision(
            is_consumed=False,
            is_sweep=False,
            swept_by_wick=False,
            body_closed_inside=True,
        )

    # =========================================================================
    # LIFECYCLE ENGINE
    # =========================================================================

    def _evaluate_pool_sweeps(
        self,
        all_pools: List[LiquidityPool],
        candles: List[Candle],
        external_trend: TrendDirection,
    ) -> Tuple[
        List[LiquidityPool],
        List[LiquidityPool],
        List[LiquidityPool],
        List[LiquidityEvent],
    ]:

        if not candles:

            return (
                all_pools,
                [],
                [],
                [],
            )

        events: List[LiquidityEvent] = []

        active_pools: List[LiquidityPool] = []

        swept_pools: List[LiquidityPool] = []

        consumed_pools: List[LiquidityPool] = []

        # ------------------------------------------------------------------
        # Process every independent pool.
        # ------------------------------------------------------------------

        for pool in all_pools:

            latest_swing = max(
                pool.swings,
                key=lambda s: s.raw_swing.confirmation_index,
            )

            start_index = latest_swing.raw_swing.confirmation_index

            # --------------------------------------------------------------
            # No candle after confirmation.
            # --------------------------------------------------------------

            if start_index >= len(candles):

                active_pools.append(pool)

                continue

            final_status = PoolStatus.ACTIVE

            sweep_count = 0

            # --------------------------------------------------------------
            # Causal candle replay.
            # --------------------------------------------------------------

            for candle_index in range(
                start_index,
                len(candles),
            ):

                candle = candles[candle_index]

                # ==========================================================
                # HIGH-SIDE LIQUIDITY
                # ==========================================================

                if pool.pool_type in (
                    LiquidityPoolType.BSL,
                    LiquidityPoolType.EQH,
                ):

                    decision = self._evaluate_high_side_candle(
                        candle=candle,
                        boundary=pool.high_boundary,
                    )

                    # ------------------------------------------------------
                    # Body crossed boundary.
                    #
                    # This is terminal.
                    # ------------------------------------------------------

                    if decision.is_consumed:

                        final_status = PoolStatus.CONSUMED

                        break

                    # ------------------------------------------------------
                    # Valid wick sweep.
                    # ------------------------------------------------------

                    if decision.is_sweep:

                        sweep_count += 1

                        final_status = PoolStatus.SWEPT

                        is_internal = (
                            pool.scope
                            == LiquidityScope.INTERNAL
                            or any(
                                swing.scope
                                == SwingScope.INTERNAL
                                for swing in pool.swings
                            )
                        )

                        event_type = (
                            LiquidityEventType.INDUCEMENT
                            if (
                                external_trend
                                == TrendDirection.BEARISH
                                and is_internal
                            )
                            else LiquidityEventType.LIQUIDITY_SWEEP
                        )

                        self._emit_event(
                            events=events,
                            candle=candle,
                            pool=pool,
                            event_type=event_type,
                            direction="BEARISH_SWEEP",
                            candle_index=candle_index,
                            swept_by_wick=decision.swept_by_wick,
                            body_closed_inside=decision.body_closed_inside,
                        )

                        # IMPORTANT:
                        #
                        # Do NOT break.
                        #
                        # The pool remains observable so a later candle can
                        # transition:
                        #
                        # SWEPT -> CONSUMED
                        #
                        continue

                # ==========================================================
                # LOW-SIDE LIQUIDITY
                # ==========================================================

                elif pool.pool_type in (
                    LiquidityPoolType.SSL,
                    LiquidityPoolType.EQL,
                ):

                    decision = self._evaluate_low_side_candle(
                        candle=candle,
                        boundary=pool.low_boundary,
                    )

                    # ------------------------------------------------------
                    # Body crossed boundary.
                    # ------------------------------------------------------

                    if decision.is_consumed:

                        final_status = PoolStatus.CONSUMED

                        break

                    # ------------------------------------------------------
                    # Valid wick sweep.
                    # ------------------------------------------------------

                    if decision.is_sweep:

                        sweep_count += 1

                        final_status = PoolStatus.SWEPT

                        is_internal = (
                            pool.scope
                            == LiquidityScope.INTERNAL
                            or any(
                                swing.scope
                                == SwingScope.INTERNAL
                                for swing in pool.swings
                            )
                        )

                        event_type = (
                            LiquidityEventType.INDUCEMENT
                            if (
                                external_trend
                                == TrendDirection.BULLISH
                                and is_internal
                            )
                            else LiquidityEventType.LIQUIDITY_SWEEP
                        )

                        self._emit_event(
                            events=events,
                            candle=candle,
                            pool=pool,
                            event_type=event_type,
                            direction="BULLISH_SWEEP",
                            candle_index=candle_index,
                            swept_by_wick=decision.swept_by_wick,
                            body_closed_inside=decision.body_closed_inside,
                        )

                        # Continue scanning for:
                        #
                        # SWEPT -> CONSUMED
                        #
                        continue

            # ----------------------------------------------------------------
            # Create immutable final pool snapshot.
            # ----------------------------------------------------------------

            updated_pool = LiquidityPool(
                pool_id=pool.pool_id,
                pool_type=pool.pool_type,
                price_level=pool.price_level,
                high_boundary=pool.high_boundary,
                low_boundary=pool.low_boundary,
                swings=pool.swings,
                creation_timestamp=pool.creation_timestamp,
                status=final_status,
                scope=pool.scope,
                sweep_count=sweep_count,
            )

            # ----------------------------------------------------------------
            # Partition final state.
            # ----------------------------------------------------------------

            if final_status == PoolStatus.ACTIVE:

                active_pools.append(updated_pool)

            elif final_status == PoolStatus.SWEPT:

                swept_pools.append(updated_pool)

            elif final_status == PoolStatus.CONSUMED:

                consumed_pools.append(updated_pool)

        return (
            active_pools,
            swept_pools,
            consumed_pools,
            events,
        )

    # =========================================================================
    # EVENT EMISSION
    # =========================================================================

    def _emit_event(
        self,
        events: List[LiquidityEvent],
        candle: Candle,
        pool: LiquidityPool,
        event_type: LiquidityEventType,
        direction: str,
        candle_index: int,
        swept_by_wick: bool,
        body_closed_inside: bool,
    ) -> None:
        """
        Emit one deterministic event.

        Geometry booleans are supplied only after the dedicated geometry
        evaluator has proven the event condition.
        """

        event_key = (
            event_type.value,
            pool.pool_id,
            candle_index,
        )

        if event_key in self._emitted_event_keys:

            return

        self._emitted_event_keys.add(event_key)

        events.append(
            LiquidityEvent(
                timestamp=candle.timestamp,
                event_type=event_type,
                pool_id=pool.pool_id,
                pool_type=pool.pool_type,
                liquidity_scope=pool.scope,
                price_level=pool.price_level,
                direction=direction,
                candle_index=candle_index,
                swept_by_wick=swept_by_wick,
                body_closed_inside=body_closed_inside,
            )
        )
