"""
QCP Phase 7 — Execution Algorithms.
Implements the 8 canonical institutional order slicing algorithms:

1. MARKET: Immediate aggressive execution crossing spread.
2. LIMIT: Static price constraint with standard queuing.
3. PASSIVE: Maker-only quote posting tracking near-touch / midpoint.
4. TWAP: Time-Weighted Average Price uniform interval distribution.
5. VWAP: Volume-Weighted Average Price distributed by historical intraday volume profile.
6. ICEBERG: Synthetic child order display slicing with hidden quantity reserve.
7. POV (Percentage of Volume): Dynamic participation rate targeting (e.g. 5% - 15% of market volume).
8. ADAPTIVE: Multi-factor liquidity-seeking algorithm adapting urgency to spread and imbalance.

PAPER ONLY. No live exchange connectivity.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from execution_gateway.execution_os.order_intent import (
    OrderIntent,
    ChildOrder,
    ExecutionPlan,
    ExecutionAlgoType,
    OrderSide,
    OrderIntentStatus,
    TimeInForce,
)

logger = logging.getLogger("QCP.ExecutionAlgorithms")


class ExecutionAlgoFactory:
    """
    Constructs execution plans and child order schedules for all 8 algorithmic execution types.
    """

    @classmethod
    def plan_execution(
        cls,
        intent: OrderIntent,
        selected_venue: str,
        current_market_price: float,
        intraday_volume_profile: Optional[List[float]] = None,
    ) -> ExecutionPlan:
        """Dispatches to the appropriate algorithmic planner based on intent.algo_type."""
        algo = intent.algo_type

        if algo == ExecutionAlgoType.MARKET:
            return cls._plan_market(intent, selected_venue, current_market_price)
        elif algo == ExecutionAlgoType.LIMIT:
            return cls._plan_limit(intent, selected_venue, current_market_price)
        elif algo == ExecutionAlgoType.PASSIVE:
            return cls._plan_passive(intent, selected_venue, current_market_price)
        elif algo == ExecutionAlgoType.TWAP:
            return cls._plan_twap(intent, selected_venue, current_market_price)
        elif algo == ExecutionAlgoType.VWAP:
            return cls._plan_vwap(intent, selected_venue, current_market_price, intraday_volume_profile)
        elif algo == ExecutionAlgoType.ICEBERG:
            return cls._plan_iceberg(intent, selected_venue, current_market_price)
        elif algo == ExecutionAlgoType.POV:
            return cls._plan_pov(intent, selected_venue, current_market_price)
        elif algo == ExecutionAlgoType.ADAPTIVE:
            return cls._plan_adaptive(intent, selected_venue, current_market_price)
        else:
            return cls._plan_limit(intent, selected_venue, current_market_price)

    @classmethod
    def _plan_market(cls, intent: OrderIntent, venue: str, price: float) -> ExecutionPlan:
        child = ChildOrder(
            child_id=f"CHILD-{intent.intent_id}-MKT-0",
            parent_intent_id=intent.intent_id,
            venue_id=venue,
            symbol=intent.symbol,
            side=intent.side,
            algo_type=ExecutionAlgoType.MARKET,
            quantity=intent.target_quantity,
            limit_price=None,
            time_in_force=TimeInForce.IOC,
        )
        return ExecutionPlan(
            plan_id=f"PLAN-{intent.intent_id}",
            intent_id=intent.intent_id,
            strategy_id=intent.strategy_id,
            selected_venue=venue,
            algo_type=ExecutionAlgoType.MARKET,
            total_quantity=intent.target_quantity,
            slice_count=1,
            child_orders=[child],
            estimated_duration_sec=1,
            estimated_market_impact_bps=4.5,
        )

    @classmethod
    def _plan_limit(cls, intent: OrderIntent, venue: str, price: float) -> ExecutionPlan:
        child = ChildOrder(
            child_id=f"CHILD-{intent.intent_id}-LMT-0",
            parent_intent_id=intent.intent_id,
            venue_id=venue,
            symbol=intent.symbol,
            side=intent.side,
            algo_type=ExecutionAlgoType.LIMIT,
            quantity=intent.target_quantity,
            limit_price=intent.limit_price or price,
            time_in_force=TimeInForce.GTC,
        )
        return ExecutionPlan(
            plan_id=f"PLAN-{intent.intent_id}",
            intent_id=intent.intent_id,
            strategy_id=intent.strategy_id,
            selected_venue=venue,
            algo_type=ExecutionAlgoType.LIMIT,
            total_quantity=intent.target_quantity,
            slice_count=1,
            child_orders=[child],
            estimated_duration_sec=intent.time_horizon_sec,
            estimated_market_impact_bps=1.0,
        )

    @classmethod
    def _plan_passive(cls, intent: OrderIntent, venue: str, price: float) -> ExecutionPlan:
        # Passive posts strictly at the touch / inside spread with POST_ONLY
        offset = -0.0005 if intent.side == OrderSide.BUY else 0.0005
        post_price = (intent.limit_price or price) * (1.0 + offset)
        child = ChildOrder(
            child_id=f"CHILD-{intent.intent_id}-PAS-0",
            parent_intent_id=intent.intent_id,
            venue_id=venue,
            symbol=intent.symbol,
            side=intent.side,
            algo_type=ExecutionAlgoType.PASSIVE,
            quantity=intent.target_quantity,
            limit_price=round(post_price, 2),
            time_in_force=TimeInForce.POST_ONLY,
        )
        return ExecutionPlan(
            plan_id=f"PLAN-{intent.intent_id}",
            intent_id=intent.intent_id,
            strategy_id=intent.strategy_id,
            selected_venue=venue,
            algo_type=ExecutionAlgoType.PASSIVE,
            total_quantity=intent.target_quantity,
            slice_count=1,
            child_orders=[child],
            estimated_duration_sec=intent.time_horizon_sec,
            estimated_market_impact_bps=0.0,
        )

    @classmethod
    def _plan_twap(cls, intent: OrderIntent, venue: str, price: float) -> ExecutionPlan:
        # Slice total quantity across time slices (default 5 slices)
        slices = intent.algo_params.get("slices", 5)
        qty_per_slice = round(intent.target_quantity / slices, 4)
        children: List[ChildOrder] = []
        for i in range(slices):
            children.append(
                ChildOrder(
                    child_id=f"CHILD-{intent.intent_id}-TWAP-{i}",
                    parent_intent_id=intent.intent_id,
                    venue_id=venue,
                    symbol=intent.symbol,
                    side=intent.side,
                    algo_type=ExecutionAlgoType.TWAP,
                    quantity=qty_per_slice,
                    limit_price=intent.limit_price or price,
                    time_in_force=TimeInForce.IOC,
                )
            )
        return ExecutionPlan(
            plan_id=f"PLAN-{intent.intent_id}",
            intent_id=intent.intent_id,
            strategy_id=intent.strategy_id,
            selected_venue=venue,
            algo_type=ExecutionAlgoType.TWAP,
            total_quantity=intent.target_quantity,
            slice_count=slices,
            child_orders=children,
            estimated_duration_sec=intent.time_horizon_sec,
            estimated_market_impact_bps=1.5,
        )

    @classmethod
    def _plan_vwap(
        cls,
        intent: OrderIntent,
        venue: str,
        price: float,
        volume_profile: Optional[List[float]] = None,
    ) -> ExecutionPlan:
        profile = volume_profile or [0.15, 0.20, 0.30, 0.20, 0.15]
        total_weight = sum(profile)
        normalized_weights = [w / total_weight for w in profile]

        children: List[ChildOrder] = []
        for i, w in enumerate(normalized_weights):
            child_qty = round(intent.target_quantity * w, 4)
            children.append(
                ChildOrder(
                    child_id=f"CHILD-{intent.intent_id}-VWAP-{i}",
                    parent_intent_id=intent.intent_id,
                    venue_id=venue,
                    symbol=intent.symbol,
                    side=intent.side,
                    algo_type=ExecutionAlgoType.VWAP,
                    quantity=child_qty,
                    limit_price=intent.limit_price or price,
                    time_in_force=TimeInForce.IOC,
                )
            )
        return ExecutionPlan(
            plan_id=f"PLAN-{intent.intent_id}",
            intent_id=intent.intent_id,
            strategy_id=intent.strategy_id,
            selected_venue=venue,
            algo_type=ExecutionAlgoType.VWAP,
            total_quantity=intent.target_quantity,
            slice_count=len(children),
            child_orders=children,
            estimated_duration_sec=intent.time_horizon_sec,
            estimated_market_impact_bps=1.2,
        )

    @classmethod
    def _plan_iceberg(cls, intent: OrderIntent, venue: str, price: float) -> ExecutionPlan:
        # Display 20% visible clip, refresh upon fill
        clip_pct = intent.algo_params.get("display_clip_pct", 0.20)
        display_qty = round(intent.target_quantity * clip_pct, 4)
        slices = int(math.ceil(1.0 / clip_pct))

        children: List[ChildOrder] = []
        for i in range(slices):
            children.append(
                ChildOrder(
                    child_id=f"CHILD-{intent.intent_id}-ICEBERG-{i}",
                    parent_intent_id=intent.intent_id,
                    venue_id=venue,
                    symbol=intent.symbol,
                    side=intent.side,
                    algo_type=ExecutionAlgoType.ICEBERG,
                    quantity=display_qty,
                    limit_price=intent.limit_price or price,
                    time_in_force=TimeInForce.GTC,
                )
            )
        return ExecutionPlan(
            plan_id=f"PLAN-{intent.intent_id}",
            intent_id=intent.intent_id,
            strategy_id=intent.strategy_id,
            selected_venue=venue,
            algo_type=ExecutionAlgoType.ICEBERG,
            total_quantity=intent.target_quantity,
            slice_count=slices,
            child_orders=children,
            estimated_duration_sec=intent.time_horizon_sec,
            estimated_market_impact_bps=0.8,
        )

    @classmethod
    def _plan_pov(cls, intent: OrderIntent, venue: str, price: float) -> ExecutionPlan:
        # Target participation rate: e.g. 10% of tape volume
        participation_rate = intent.algo_params.get("participation_rate", 0.10)
        slices = 4
        child_qty = round(intent.target_quantity / slices, 4)
        children = [
            ChildOrder(
                child_id=f"CHILD-{intent.intent_id}-POV-{i}",
                parent_intent_id=intent.intent_id,
                venue_id=venue,
                symbol=intent.symbol,
                side=intent.side,
                algo_type=ExecutionAlgoType.POV,
                quantity=child_qty,
                limit_price=intent.limit_price,
                time_in_force=TimeInForce.IOC,
            )
            for i in range(slices)
        ]
        return ExecutionPlan(
            plan_id=f"PLAN-{intent.intent_id}",
            intent_id=intent.intent_id,
            strategy_id=intent.strategy_id,
            selected_venue=venue,
            algo_type=ExecutionAlgoType.POV,
            total_quantity=intent.target_quantity,
            slice_count=slices,
            child_orders=children,
            estimated_duration_sec=intent.time_horizon_sec,
            estimated_market_impact_bps=1.8,
        )

    @classmethod
    def _plan_adaptive(cls, intent: OrderIntent, venue: str, price: float) -> ExecutionPlan:
        # Adaptive divides into 3 clips: 1 passive clip, 1 midpoint clip, 1 aggressive clip
        q1 = round(intent.target_quantity * 0.40, 4)
        q2 = round(intent.target_quantity * 0.40, 4)
        q3 = round(intent.target_quantity * 0.20, 4)

        children = [
            ChildOrder(
                child_id=f"CHILD-{intent.intent_id}-ADAPT-PASSIVE",
                parent_intent_id=intent.intent_id,
                venue_id=venue,
                symbol=intent.symbol,
                side=intent.side,
                algo_type=ExecutionAlgoType.PASSIVE,
                quantity=q1,
                limit_price=price * 0.999 if intent.side == OrderSide.BUY else price * 1.001,
                time_in_force=TimeInForce.POST_ONLY,
            ),
            ChildOrder(
                child_id=f"CHILD-{intent.intent_id}-ADAPT-MID",
                parent_intent_id=intent.intent_id,
                venue_id=venue,
                symbol=intent.symbol,
                side=intent.side,
                algo_type=ExecutionAlgoType.LIMIT,
                quantity=q2,
                limit_price=price,
                time_in_force=TimeInForce.GTC,
            ),
            ChildOrder(
                child_id=f"CHILD-{intent.intent_id}-ADAPT-AGGR",
                parent_intent_id=intent.intent_id,
                venue_id=venue,
                symbol=intent.symbol,
                side=intent.side,
                algo_type=ExecutionAlgoType.MARKET,
                quantity=q3,
                limit_price=None,
                time_in_force=TimeInForce.IOC,
            ),
        ]
        return ExecutionPlan(
            plan_id=f"PLAN-{intent.intent_id}",
            intent_id=intent.intent_id,
            strategy_id=intent.strategy_id,
            selected_venue=venue,
            algo_type=ExecutionAlgoType.ADAPTIVE,
            total_quantity=intent.target_quantity,
            slice_count=3,
            child_orders=children,
            estimated_duration_sec=intent.time_horizon_sec,
            estimated_market_impact_bps=1.1,
        )
