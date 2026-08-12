from typing import Optional
from strategy_engine.contracts.trade_plan import TradePlanPayload
from risk_engine.contracts.risk_rejection import RiskRejectionReason

class RRValidator:
    """
    Validates that the structural reward-to-risk ratio is at least 4.0.
    """
    @staticmethod
    def validate(plan: TradePlanPayload) -> Optional[RiskRejectionReason]:
        if plan.raw_rr < 4.0:
            return RiskRejectionReason.REJECT_RR_BELOW_FLOOR
        return None
