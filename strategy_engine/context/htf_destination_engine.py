"""
Product 02 — Strategy Engine: HTF Destination Engine
Discovers and validates forward structural destinations (Take Profit targets) from HTF MarketStatePayload.
Replaces brittle weak-swing hardcoding with objectively defined destination candidates.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
from market_intelligence.primitives import (
    MarketStatePayload,
    TrendDirection,
    KeyZone,
    EQHLiquidityPool,
    SequenceSwing
)


class DestinationType(Enum):
    OPPOSING_KEYZONE = "OPPOSING_KEYZONE"
    LIQUIDITY_POOL = "LIQUIDITY_POOL"
    WEAK_SWING = "WEAK_SWING"
    FORWARD_STRUCTURAL_EXPANSION = "FORWARD_STRUCTURAL_EXPANSION"
    NONE = "NONE"


@dataclass(frozen=True)
class StructuralDestination:
    target_price: Optional[float]
    destination_type: DestinationType
    source_id: Optional[str]
    is_valid: bool
    rejection_reason: Optional[str] = None


class HTFDestinationEngine:
    """
    Objectively identifies and ranks forward structural destinations.
    Enforces strict forward geometry:
      - Long: Target > Reference Price
      - Short: Target < Reference Price
    Rejects invalid geometry rather than inventing artificial targets.
    """
    ENABLE_FORWARD_EXPANSION: bool = False
    TARGET_HIERARCHY_MODE: str = "CLOSEST_OBJECTIVE"

    @staticmethod
    def evaluate(
        htf_payload: MarketStatePayload,
        reference_price: Optional[float] = None,
        is_long: Optional[bool] = None,
        enable_forward_expansion: Optional[bool] = None,
        hierarchy_mode: Optional[str] = None
    ) -> StructuralDestination:
        if enable_forward_expansion is None:
            enable_forward_expansion = HTFDestinationEngine.ENABLE_FORWARD_EXPANSION
        if hierarchy_mode is None:
            hierarchy_mode = HTFDestinationEngine.TARGET_HIERARCHY_MODE

        trend = htf_payload.trend_state
        if is_long is None:
            if trend == TrendDirection.BULLISH or "BULLISH" in str(trend):
                is_long = True
            elif trend == TrendDirection.BEARISH or "BEARISH" in str(trend):
                is_long = False
            else:
                return StructuralDestination(
                    target_price=None,
                    destination_type=DestinationType.NONE,
                    source_id=None,
                    is_valid=False,
                    rejection_reason="REJECT_NO_TREND_BIAS"
                )

        ref_price = reference_price if reference_price is not None and reference_price > 0 else htf_payload.current_price
        if ref_price <= 0:
            return StructuralDestination(
                target_price=None,
                destination_type=DestinationType.NONE,
                source_id=None,
                is_valid=False,
                rejection_reason="REJECT_INVALID_REFERENCE_PRICE"
            )

        candidates: List[Tuple[float, DestinationType, str]] = []

        # Candidate Pool 1: Opposing Unmitigated HTF KeyZones
        # For Longs: Opposing keyzones are Bearish OBs/FVGs (supply resistance) located ABOVE current price.
        # Target the entry/front boundary of the zone: low_boundary.
        # For Shorts: Opposing keyzones are Bullish OBs/FVGs (demand support) located BELOW current price.
        # Target the entry/front boundary of the zone: high_boundary.
        for kz in (htf_payload.keyzones or []):
            kz_type = str(getattr(kz, 'zone_type', ''))
            status = str(getattr(kz, 'status', ''))
            if "INVALIDATED" in status:
                continue

            low_b = getattr(kz, 'low_boundary', None)
            if low_b is None:
                low_b = getattr(kz, 'low', None)
            high_b = getattr(kz, 'high_boundary', None)
            if high_b is None:
                high_b = getattr(kz, 'high', None)

            # Standard order: low_b <= high_b
            if low_b is not None and high_b is not None and low_b > high_b:
                low_b, high_b = high_b, low_b
            zone_id = getattr(kz, 'zone_id', 'unknown_kz')

            if is_long:
                if "BEARISH" in kz_type and low_b is not None and low_b > 0.0 and low_b > ref_price:
                    candidates.append((low_b, DestinationType.OPPOSING_KEYZONE, zone_id))
            else:
                if "BULLISH" in kz_type and high_b is not None and high_b > 0.0 and high_b < ref_price:
                    candidates.append((high_b, DestinationType.OPPOSING_KEYZONE, zone_id))

        # Candidate Pool 2: Unswept HTF Liquidity Pools (EQH/EQL)
        for pool in (htf_payload.liquidity_pools or []):
            if getattr(pool, 'is_swept', False):
                continue
            pool_price = getattr(pool, 'price_level', None)
            pool_id = getattr(pool, 'pool_id', 'unknown_pool')
            if pool_price is None or pool_price <= 0.0:
                continue

            if is_long and pool_price > ref_price:
                candidates.append((pool_price, DestinationType.LIQUIDITY_POOL, pool_id))
            elif not is_long and pool_price < ref_price:
                candidates.append((pool_price, DestinationType.LIQUIDITY_POOL, pool_id))

        # Candidate Pool 3: HTF Weak Swing
        struct = htf_payload.structure_state
        if struct:
            weak_swing = struct.weak_high if is_long else struct.weak_low
            if weak_swing and weak_swing.raw_swing:
                ws_price = weak_swing.raw_swing.price
                ws_id = getattr(weak_swing.raw_swing, 'swing_id', 'weak_swing')
                if ws_price is not None and ws_price > 0.0:
                    if is_long and ws_price > ref_price:
                        candidates.append((ws_price, DestinationType.WEAK_SWING, ws_id))
                    elif not is_long and ws_price < ref_price:
                        candidates.append((ws_price, DestinationType.WEAK_SWING, ws_id))

        # Candidate Pool 4: Forward Structural Expansion (Fallback if target-starved, disabled by default)
        if enable_forward_expansion and not candidates and struct and struct.dealing_range:
            dr = struct.dealing_range
            range_width = dr.high_price - dr.low_price
            if range_width > 0:
                if is_long:
                    expansion_target = dr.high_price + (range_width * 1.0)
                    if expansion_target > 0.0 and expansion_target > ref_price:
                        candidates.append((expansion_target, DestinationType.FORWARD_STRUCTURAL_EXPANSION, f"DR_EXPANSION_1.0_L_{dr.low_price}_{dr.high_price}"))
                else:
                    expansion_target = dr.low_price - (range_width * 1.0)
                    if expansion_target > 0.0 and expansion_target < ref_price:
                        candidates.append((expansion_target, DestinationType.FORWARD_STRUCTURAL_EXPANSION, f"DR_EXPANSION_1.0_S_{dr.high_price}_{dr.low_price}"))

        # Enforce strict positive price constraints across all candidates
        candidates = [c for c in candidates if c[0] > 0.0]

        if not candidates:
            return StructuralDestination(
                target_price=None,
                destination_type=DestinationType.NONE,
                source_id=None,
                is_valid=False,
                rejection_reason="REJECT_NO_FORWARD_STRUCTURAL_DESTINATION"
            )

        # Hierarchy / Ranking:
        if hierarchy_mode == "STRUCTURAL_OBJECTIVE":
            # Structural Objective Hierarchy:
            # Tier 1: WEAK_SWING (Primary directional trend destination / liquidation point)
            # Tier 2: LIQUIDITY_POOL (Unswept external EQH / EQL pools)
            # Tier 3: OPPOSING_KEYZONE (Internal supply / demand zones)
            # Tier 4: FORWARD_STRUCTURAL_EXPANSION (Dealing range expansion fallback)
            # Within each tier, select the closest objective to reference price.
            tier_priority = {
                DestinationType.WEAK_SWING: 1,
                DestinationType.LIQUIDITY_POOL: 2,
                DestinationType.OPPOSING_KEYZONE: 3,
                DestinationType.FORWARD_STRUCTURAL_EXPANSION: 4,
            }
            candidates.sort(key=lambda x: (tier_priority.get(x[1], 99), abs(x[0] - ref_price)))
        else:
            # Default / Baseline: CLOSEST_OBJECTIVE
            # Sort candidates strictly by distance from reference price (closest forward structural objective)
            if is_long:
                candidates.sort(key=lambda x: x[0])  # Smallest target > ref_price
            else:
                candidates.sort(key=lambda x: x[0], reverse=True)  # Largest target < ref_price

        best_target, best_type, best_id = candidates[0]

        # Final geometric and absolute price verification
        if best_target <= 0.0:
            return StructuralDestination(
                target_price=None,
                destination_type=DestinationType.NONE,
                source_id=None,
                is_valid=False,
                rejection_reason="REJECT_NON_POSITIVE_TARGET_PRICE"
            )

        if is_long and best_target <= ref_price:
            return StructuralDestination(
                target_price=None,
                destination_type=DestinationType.NONE,
                source_id=None,
                is_valid=False,
                rejection_reason="REJECT_INVALID_TARGET_GEOMETRY"
            )
        elif not is_long and best_target >= ref_price:
            return StructuralDestination(
                target_price=None,
                destination_type=DestinationType.NONE,
                source_id=None,
                is_valid=False,
                rejection_reason="REJECT_INVALID_TARGET_GEOMETRY"
            )

        return StructuralDestination(
            target_price=best_target,
            destination_type=best_type,
            source_id=best_id,
            is_valid=True,
            rejection_reason=None
        )
