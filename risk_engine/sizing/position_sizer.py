from typing import Tuple, Optional
from strategy_engine.contracts.trade_plan import TradePlanPayload
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_rejection import RiskRejectionReason

class PositionSizer:
    MAX_RISK_FRACTION = 0.01  # 1.0% maximum absolute cap

    @staticmethod
    def calculate(plan: TradePlanPayload, account_state: AccountState) -> Tuple[Optional[float], Optional[float], Optional[RiskRejectionReason]]:
        """
        Returns (position_units, dollar_risk, rejection_reason)
        """
        # Calculate maximum allowed risk based on current liquid equity
        dollar_risk = account_state.current_equity * PositionSizer.MAX_RISK_FRACTION
        
        # Determine the structural distance to the invalidation point
        stop_distance = abs(plan.entry_price - plan.stop_invalidation_price)
        
        # Zero division safeguard (if entry and stop are exactly the same price)
        if stop_distance <= 0.0000001:
            return None, None, RiskRejectionReason.REJECT_INVALID_STOP
            
        position_units = dollar_risk / stop_distance
        
        # Position sizing sanity check
        if position_units <= 0:
            return None, None, RiskRejectionReason.REJECT_INVALID_POSITION_SIZE
            
        return position_units, dollar_risk, None
