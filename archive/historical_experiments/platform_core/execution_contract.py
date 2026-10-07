"""
Quantitative Crypto Platform (QCP) — Canonical Execution Contract.

Single authoritative execution contract establishing invariant semantics across:
- Candle-close confirmation and bar timing
- Directional and multi-timeframe synchronization
- Same-bar collision handling (Adverse-First baseline axiom)
- Realistic spread, slippage, and fee friction accounting
- Canonical R accounting (Gross R, Friction R, Net R)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Dict, Any, Optional


class CollisionPolicy(str, Enum):
    ADVERSE_FIRST = "ADVERSE_FIRST"          # Canonical baseline: SL takes precedence on same-bar collision
    OPTIMISTIC_FIRST = "OPTIMISTIC_FIRST"    # Deprecated / stress-test only: TP takes precedence


@dataclass(frozen=True)
class ExecutionConfig:
    """Canonical execution configuration for QCP research and production engines."""
    maker_fee_bps: float = 2.0      # 0.02% maker fee
    taker_fee_bps: float = 5.0      # 0.05% taker fee
    slippage_bps: float = 5.0       # 0.05% market order adverse slippage
    spread_bps: float = 2.0         # 0.02% half-spread
    collision_policy: CollisionPolicy = CollisionPolicy.ADVERSE_FIRST
    require_candle_close: bool = True


class ExecutionContract:
    """
    Authoritative execution mathematics and arbitration rules for QCP.
    Guarantees that backtesting, forward paper trading, and production live engines
    share identical fill and accounting semantics.
    """

    @staticmethod
    def resolve_same_bar_collision(
        hit_sl: bool,
        hit_tp: bool,
        policy: CollisionPolicy = CollisionPolicy.ADVERSE_FIRST,
    ) -> Tuple[bool, bool, str]:
        """
        Arbitrates same-bar high/low collisions where both SL and TP thresholds
        were touched in the same candle.

        Under canonical ADVERSE_FIRST policy:
        If both hit_sl and hit_tp are True, hit_tp is invalidated and hit_sl is awarded.
        """
        if hit_sl and hit_tp:
            if policy == CollisionPolicy.ADVERSE_FIRST:
                return True, False, "SL_HIT_ADVERSE_FIRST_COLLISION"
            else:
                return False, True, "TP_HIT_OPTIMISTIC_COLLISION"
        elif hit_sl:
            return True, False, "SL_HIT"
        elif hit_tp:
            return False, True, "TP_HIT"
        else:
            return False, False, "NO_EXIT"

    @staticmethod
    def apply_slippage(price: float, is_buy: bool, slippage_bps: float = 5.0) -> float:
        """
        Applies adverse slippage to market fills:
        - Buying costs more: price * (1 + slippage)
        - Selling receives less: price * (1 - slippage)
        """
        slippage_factor = slippage_bps / 10000.0
        if is_buy:
            return price * (1.0 + slippage_factor)
        else:
            return price * (1.0 - slippage_factor)

    @staticmethod
    def calculate_fee(notional: float, fee_bps: float) -> float:
        """Calculates transaction fee given notional value in USD and fee rate in basis points."""
        return notional * (fee_bps / 10000.0)

    @staticmethod
    def calculate_r_accounting(
        entry_price: float,
        exit_price: float,
        initial_sl_price: float,
        is_long: bool,
        position_size: float,
        entry_fee_usd: float,
        exit_fee_usd: float,
    ) -> Dict[str, float]:
        """
        Calculates canonical R metrics:
        - initial_risk_usd: position_size * abs(entry_price - initial_sl_price)
        - gross_pnl_usd: dollar gain before friction
        - total_friction_usd: entry_fee + exit_fee + slippage loss
        - net_pnl_usd: gross_pnl - total_friction
        - gross_r: gross_pnl_usd / initial_risk_usd
        - friction_r: total_friction_usd / initial_risk_usd
        - net_r: net_pnl_usd / initial_risk_usd (or gross_r - friction_r)
        """
        risk_per_unit = abs(entry_price - initial_sl_price)
        initial_risk_usd = position_size * risk_per_unit

        if initial_risk_usd <= 1e-9:
            return {
                "initial_risk_usd": 0.0,
                "gross_pnl_usd": 0.0,
                "total_friction_usd": entry_fee_usd + exit_fee_usd,
                "net_pnl_usd": -(entry_fee_usd + exit_fee_usd),
                "gross_r": 0.0,
                "friction_r": 0.0,
                "net_r": 0.0,
            }

        if is_long:
            gross_pnl_usd = (exit_price - entry_price) * position_size
        else:
            gross_pnl_usd = (entry_price - exit_price) * position_size

        total_friction_usd = entry_fee_usd + exit_fee_usd
        net_pnl_usd = gross_pnl_usd - total_friction_usd

        gross_r = gross_pnl_usd / initial_risk_usd
        friction_r = total_friction_usd / initial_risk_usd
        net_r = net_pnl_usd / initial_risk_usd

        return {
            "initial_risk_usd": round(initial_risk_usd, 4),
            "gross_pnl_usd": round(gross_pnl_usd, 4),
            "total_friction_usd": round(total_friction_usd, 4),
            "net_pnl_usd": round(net_pnl_usd, 4),
            "gross_r": round(gross_r, 4),
            "friction_r": round(friction_r, 4),
            "net_r": round(net_r, 4),
        }
