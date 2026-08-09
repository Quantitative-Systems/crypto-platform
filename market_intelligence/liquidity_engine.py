"""
Quantitative Systems Platform — Crypto Platform Product
Product 01: Market Language | Engine 3: Liquidity Intelligence Engine (Hardened)

RESPONSIBILITY
--------------
Consumes confirmed SequenceSwings from Engine 2 and sequential Candle history.

Produces ONLY:
    - Equal Highs (EQH) & Equal Lows (EQL) liquidity pools (0.05% relative tolerance)
    - Buy-Side Liquidity (BSL) & Sell-Side Liquidity (SSL) pool anchors (External & Internal)
    - Liquidity Sweeps (Wick pierces pool boundary, candle body sits strictly inside)
    - Inducement Events (Internal liquidity swept in direction of macro trend)
    - Complete Pool Lifecycle Tracking:
          ACTIVE -> SWEPT -> CONSUMED

STRICT BOUNDARY
---------------
This engine does NOT know about:
    - Order Blocks / Fair Value Gaps (Engine 4)
    - Market Phase (Engine 5)
    - Buy/Sell Signals or Strategy Logic
    - Risk / Position Sizing / Stop Loss
    - Execution Adapters / Broker APIs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Tuple

from market_intelligence.raw_swing_engine import Candle, SwingType
from market_intelligence.structure_builder_engine import SequenceSwing, SwingScope, TrendDirection


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


@dataclass(frozen=True)
class LiquidityPool:
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
    active_pools: List[LiquidityPool]
    swept_pools: List[LiquidityPool]
    consumed_pools: List[LiquidityPool]
    events: List[LiquidityEvent]


class LiquidityEngine:
    """
    Deterministic, stateful Liquidity Intelligence Engine.
    Tracks complete liquidity pool lifecycles (ACTIVE -> SWEPT -> CONSUMED)
    with strict candlestick body-inside geometry checks.
    """

    def __init__(self, eq_tolerance_pct: float = 0.0005, boundary_epsilon: float = 0.0) -> None:
        if eq_tolerance_pct < 0:
            raise ValueError("eq_tolerance_pct must be >= 0")
        if boundary_epsilon < 0:
            raise ValueError("boundary_epsilon must be >= 0")
        self.eq_tolerance_pct = eq_tolerance_pct
        self.boundary_epsilon = boundary_epsilon
        self._emitted_event_keys: Set[Tuple] = set()

    def reset(self) -> None:
        """Reset stateful event tracking memory."""
        self._emitted_event_keys.clear()

    def process(
        self,
        swings: List[SequenceSwing],
        candles: List[Candle],
        external_trend: TrendDirection = TrendDirection.NEUTRAL
    ) -> LiquidityState:
        """
        Main Engine 3 processing loop.
        Constructs liquidity pools and evaluates candle streams for complete lifecycles.
        """
        if not swings:
            return LiquidityState(active_pools=[], swept_pools=[], consumed_pools=[], events=[])

        # 1. Detect EQH / EQL Pools
        eq_pools = self._detect_eq_pools(swings)

        # 2. Detect BSL / SSL Structural Pools (External and Internal)
        structural_pools = self._detect_structural_pools(swings)

        all_pools = self._deduplicate_pools(eq_pools + structural_pools)

        # 3. Evaluate Sweeps and Complete Lifecycles across Candle Stream
        active_pools, swept_pools, consumed_pools, events = self._evaluate_pool_sweeps(
            all_pools=all_pools,
            candles=candles,
            external_trend=external_trend
        )

        return LiquidityState(
            active_pools=active_pools,
            swept_pools=swept_pools,
            consumed_pools=consumed_pools,
            events=events
        )

    def _detect_eq_pools(self, swings: List[SequenceSwing]) -> List[LiquidityPool]:
        pools: List[LiquidityPool] = []
        highs = [s for s in swings if s.raw_swing.swing_type == SwingType.HIGH]
        lows = [s for s in swings if s.raw_swing.swing_type == SwingType.LOW]

        # Scan Highs for EQH
        for i in range(len(highs)):
            anchor = highs[i]
            cluster = [anchor]
            for j in range(i + 1, len(highs)):
                cand = highs[j]
                diff = abs(cand.raw_swing.price - anchor.raw_swing.price) / anchor.raw_swing.price
                if diff <= self.eq_tolerance_pct:
                    cluster.append(cand)

            if len(cluster) >= 2:
                avg_price = sum(s.raw_swing.price for s in cluster) / len(cluster)
                pool_id = f"EQH_{cluster[0].raw_swing.swing_id}_{cluster[-1].raw_swing.swing_id}"
                pools.append(LiquidityPool(
                    pool_id=pool_id,
                    pool_type=LiquidityPoolType.EQH,
                    price_level=avg_price,
                    high_boundary=max(s.raw_swing.price for s in cluster),
                    low_boundary=min(s.raw_swing.price for s in cluster),
                    swings=cluster,
                    creation_timestamp=cluster[-1].raw_swing.timestamp,
                    status=PoolStatus.ACTIVE,
                    scope=LiquidityScope.EXTERNAL
                ))

        # Scan Lows for EQL
        for i in range(len(lows)):
            anchor = lows[i]
            cluster = [anchor]
            for j in range(i + 1, len(lows)):
                cand = lows[j]
                diff = abs(cand.raw_swing.price - anchor.raw_swing.price) / anchor.raw_swing.price
                if diff <= self.eq_tolerance_pct:
                    cluster.append(cand)

            if len(cluster) >= 2:
                avg_price = sum(s.raw_swing.price for s in cluster) / len(cluster)
                pool_id = f"EQL_{cluster[0].raw_swing.swing_id}_{cluster[-1].raw_swing.swing_id}"
                pools.append(LiquidityPool(
                    pool_id=pool_id,
                    pool_type=LiquidityPoolType.EQL,
                    price_level=avg_price,
                    high_boundary=max(s.raw_swing.price for s in cluster),
                    low_boundary=min(s.raw_swing.price for s in cluster),
                    swings=cluster,
                    creation_timestamp=cluster[-1].raw_swing.timestamp,
                    status=PoolStatus.ACTIVE,
                    scope=LiquidityScope.EXTERNAL
                ))

        return pools

    def _detect_structural_pools(self, swings: List[SequenceSwing]) -> List[LiquidityPool]:
        pools: List[LiquidityPool] = []
        for s in swings:
            p_type = LiquidityPoolType.BSL if s.raw_swing.swing_type == SwingType.HIGH else LiquidityPoolType.SSL
            p_scope = LiquidityScope.EXTERNAL if s.scope == SwingScope.EXTERNAL else LiquidityScope.INTERNAL
            pool_id = f"{p_type.value}_{s.raw_swing.swing_id}"
            pools.append(LiquidityPool(
                pool_id=pool_id,
                pool_type=p_type,
                price_level=s.raw_swing.price,
                high_boundary=s.raw_swing.price,
                low_boundary=s.raw_swing.price,
                swings=[s],
                creation_timestamp=s.raw_swing.timestamp,
                status=PoolStatus.ACTIVE,
                scope=p_scope
            ))
        return pools

    def _deduplicate_pools(self, pools: List[LiquidityPool]) -> List[LiquidityPool]:
        seen_ids: Set[str] = set()
        unique: List[LiquidityPool] = []
        for p in pools:
            if p.pool_id not in seen_ids:
                seen_ids.add(p.pool_id)
                unique.append(p)
        return unique

    def _evaluate_pool_sweeps(
        self,
        all_pools: List[LiquidityPool],
        candles: List[Candle],
        external_trend: TrendDirection
    ) -> Tuple[List[LiquidityPool], List[LiquidityPool], List[LiquidityPool], List[LiquidityEvent]]:
        if not candles:
            return all_pools, [], [], []

        events: List[LiquidityEvent] = []
        active_pools: List[LiquidityPool] = []
        swept_pools: List[LiquidityPool] = []
        consumed_pools: List[LiquidityPool] = []

        for pool in all_pools:
            latest_swing = max(pool.swings, key=lambda s: s.raw_swing.confirmation_index)
            start_index = latest_swing.raw_swing.confirmation_index

            final_status = PoolStatus.ACTIVE
            sweeps = 0

            for idx in range(start_index, len(candles)):
                candle = candles[idx]

                # High-Side Liquidity (BSL / EQH)
                if pool.pool_type in (LiquidityPoolType.BSL, LiquidityPoolType.EQH):
                    upper = pool.high_boundary + self.boundary_epsilon
                    body_top = max(candle.open, candle.close)

                    if candle.close > upper or candle.open > upper:
                        # Body Closed or Opened Above -> Pool Consumed / Broken
                        final_status = PoolStatus.CONSUMED
                        break
                    elif candle.high > upper and body_top <= upper:
                        # High Pierces, Body Sits Entirely Below -> True Wick Sweep
                        sweeps += 1
                        final_status = PoolStatus.SWEPT
                        is_internal = (pool.scope == LiquidityScope.INTERNAL) or any(s.scope == SwingScope.INTERNAL for s in pool.swings)
                        event_type = (
                            LiquidityEventType.INDUCEMENT
                            if external_trend == TrendDirection.BEARISH and is_internal
                            else LiquidityEventType.LIQUIDITY_SWEEP
                        )
                        self._emit_event(
                            events=events,
                            candle=candle,
                            pool=pool,
                            event_type=event_type,
                            direction="BEARISH_SWEEP",
                            candle_index=idx,
                            swept_by_wick=True,
                            body_closed_inside=True
                        )

                # Low-Side Liquidity (SSL / EQL)
                elif pool.pool_type in (LiquidityPoolType.SSL, LiquidityPoolType.EQL):
                    lower = pool.low_boundary - self.boundary_epsilon
                    body_bottom = min(candle.open, candle.close)

                    if candle.close < lower or candle.open < lower:
                        # Body Closed or Opened Below -> Pool Consumed / Broken
                        final_status = PoolStatus.CONSUMED
                        break
                    elif candle.low < lower and body_bottom >= lower:
                        # Low Pierces, Body Sits Entirely Above -> True Wick Sweep
                        sweeps += 1
                        final_status = PoolStatus.SWEPT
                        is_internal = (pool.scope == LiquidityScope.INTERNAL) or any(s.scope == SwingScope.INTERNAL for s in pool.swings)
                        event_type = (
                            LiquidityEventType.INDUCEMENT
                            if external_trend == TrendDirection.BULLISH and is_internal
                            else LiquidityEventType.LIQUIDITY_SWEEP
                        )
                        self._emit_event(
                            events=events,
                            candle=candle,
                            pool=pool,
                            event_type=event_type,
                            direction="BULLISH_SWEEP",
                            candle_index=idx,
                            swept_by_wick=True,
                            body_closed_inside=True
                        )

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
                sweep_count=sweeps
            )

            if final_status == PoolStatus.SWEPT:
                swept_pools.append(updated_pool)
            elif final_status == PoolStatus.CONSUMED:
                consumed_pools.append(updated_pool)
            else:
                active_pools.append(updated_pool)

        return active_pools, swept_pools, consumed_pools, events

    def _emit_event(
        self,
        events: List[LiquidityEvent],
        candle: Candle,
        pool: LiquidityPool,
        event_type: LiquidityEventType,
        direction: str,
        candle_index: int,
        swept_by_wick: bool = True,
        body_closed_inside: bool = True
    ) -> None:
        event_key = (event_type.value, pool.pool_id, candle_index)
        if event_key in self._emitted_event_keys:
            return

        self._emitted_event_keys.add(event_key)
        events.append(LiquidityEvent(
            timestamp=candle.timestamp,
            event_type=event_type,
            pool_id=pool.pool_id,
            pool_type=pool.pool_type,
            liquidity_scope=pool.scope,
            price_level=pool.price_level,
            direction=direction,
            candle_index=candle_index,
            swept_by_wick=swept_by_wick,
            body_closed_inside=body_closed_inside
        ))
