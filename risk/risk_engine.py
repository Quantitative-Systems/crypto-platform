"""
Product 01: Crypto Platform - Math-Only Risk Firewall Engine
Implements Part G of strategy_specification.md v1.1.
"""

from dataclasses import dataclass


@dataclass
class RiskCheckResult:
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
        min_rr_floor: float = 4.0
    ) -> RiskCheckResult:
        """Validates 1.0% account risk sizing and >= 1:4 Reward-to-Risk floor."""
        if account_balance <= 0 or entry_price <= 0 or stop_loss_price <= 0:
            return RiskCheckResult(
                is_approved=False, position_size_units=0.0, dollar_risk_usd=0.0,
                reward_to_risk_ratio=0.0, rejection_reason="Invalid financial inputs."
            )

        risk_distance = abs(entry_price - stop_loss_price)
        reward_distance = abs(target_tp_price - entry_price)

        if risk_distance == 0:
            return RiskCheckResult(
                is_approved=False, position_size_units=0.0, dollar_risk_usd=0.0,
                reward_to_risk_ratio=0.0, rejection_reason="Risk distance is zero."
            )

        rr_ratio = reward_distance / risk_distance

        # Assert Reward-to-Risk Floor
        if rr_ratio < min_rr_floor:
            return RiskCheckResult(
                is_approved=False, position_size_units=0.0, dollar_risk_usd=0.0,
                reward_to_risk_ratio=rr_ratio,
                rejection_reason=f"True R:R ({rr_ratio:.2f}) is below mandatory 1:{min_rr_floor:.0f} floor."
            )

        # Dynamic 1.0% Position Sizing Calculus
        dollar_risk_usd = account_balance * risk_pct
        position_size_units = dollar_risk_usd / risk_distance

        return RiskCheckResult(
            is_approved=True,
            position_size_units=position_size_units,
            dollar_risk_usd=dollar_risk_usd,
            reward_to_risk_ratio=rr_ratio,
            rejection_reason=""
        )