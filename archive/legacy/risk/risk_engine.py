"""
Product 01: Crypto Platform - Dynamic Risk Engine & Position Sizing Calculus
Calculates position size using 1.0% equity risk with hardcoded minimum stop distance floor.
"""

from dataclasses import dataclass


@dataclass
class RiskValidationResult:
    is_approved: bool
    position_size_units: float
    dollar_risk_usd: float
    reward_to_risk_ratio: float
    rejection_reason: str = ""


class RiskEngine:

    @staticmethod
    def validate_trade_risk(
        account_balance: float,
        entry_price: float,
        stop_loss_price: float,
        target_tp_price: float,
        risk_pct: float = 0.01,
        min_rr_floor: float = 4.0,
        min_stop_dist_pct: float = 0.0035  # 0.35% Minimum Stop Distance Floor
    ) -> RiskValidationResult:
        """
        Enforces 1.0% equity risk sizing, 1:4 minimum RR floor, and 0.35% minimum stop distance floor.
        Prevents position size explosions caused by micro-stops inside noise.
        """
        if account_balance <= 0 or entry_price <= 0:
            return RiskValidationResult(
                is_approved=False, position_size_units=0.0, dollar_risk_usd=0.0,
                reward_to_risk_ratio=0.0, rejection_reason="Invalid account balance or entry price."
            )

        stop_distance = abs(entry_price - stop_loss_price)
        stop_dist_pct = stop_distance / entry_price

        # Micro-Stop Floor Guard: Prevents leverage spikes when SL is too close to entry
        if stop_dist_pct < min_stop_dist_pct:
            return RiskValidationResult(
                is_approved=False, position_size_units=0.0, dollar_risk_usd=0.0,
                reward_to_risk_ratio=0.0,
                rejection_reason=f"Stop loss distance ({stop_dist_pct*100:.3f}%) is below minimum 0.35% structural floor."
            )

        tp_distance = abs(target_tp_price - entry_price)
        rr_ratio = tp_distance / stop_distance if stop_distance > 0 else 0.0

        # Enforce Minimum 1:4 Reward-to-Risk Floor
        if rr_ratio < min_rr_floor:
            return RiskValidationResult(
                is_approved=False, position_size_units=0.0, dollar_risk_usd=0.0,
                reward_to_risk_ratio=rr_ratio,
                rejection_reason=f"Reward-to-Risk ratio ({rr_ratio:.2f}) is below minimum {min_rr_floor:.1f} floor."
            )

        dollar_risk = account_balance * risk_pct
        position_size_units = dollar_risk / stop_distance

        return RiskValidationResult(
            is_approved=True,
            position_size_units=position_size_units,
            dollar_risk_usd=dollar_risk,
            reward_to_risk_ratio=rr_ratio,
            rejection_reason=""
        )