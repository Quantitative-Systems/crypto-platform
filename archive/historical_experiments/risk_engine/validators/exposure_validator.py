from typing import Optional
from strategy_engine.contracts.trade_plan import TradePlanPayload
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_rejection import RiskRejectionReason

class ExposureValidator:
    """
    Validates maximum open positions and asset-specific exposure.
    """
    MAX_OPEN_POSITIONS = 5
    MAX_ASSET_EXPOSURE_PCT = 0.03  # Max 3% total risk exposure per asset

    @staticmethod
    def validate(plan: TradePlanPayload, account_state: AccountState) -> Optional[RiskRejectionReason]:
        if account_state.open_position_count >= ExposureValidator.MAX_OPEN_POSITIONS:
            return RiskRejectionReason.REJECT_MAX_OPEN_POSITIONS
            
        current_asset_exposure = account_state.active_assets.get(plan.symbol, 0.0)
        
        # Prevent piling into the same asset if it breaches maximum asset correlation risk
        if current_asset_exposure + 0.01 > ExposureValidator.MAX_ASSET_EXPOSURE_PCT:
            return RiskRejectionReason.REJECT_MAX_ASSET_EXPOSURE
            
        return None
