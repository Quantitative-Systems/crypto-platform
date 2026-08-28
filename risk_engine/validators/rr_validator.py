from typing import Optional
from strategy_engine.contracts.trade_plan import TradePlanPayload
from risk_engine.contracts.risk_rejection import RiskRejectionReason
from risk_engine.contracts.risk_config import RiskConfig

class RRValidator:
    """
    Validates that the structural reward-to-risk ratio meets the configured floor.
    """
    @staticmethod
    def validate(plan: TradePlanPayload, config: RiskConfig) -> Optional[RiskRejectionReason]:
        if plan.raw_rr < config.min_rr_floor:
            return RiskRejectionReason.REJECT_RR_BELOW_FLOOR
        return None
