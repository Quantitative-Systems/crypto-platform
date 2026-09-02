from typing import Tuple, Optional
from strategy_engine.contracts.trade_plan import TradePlanPayload
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_rejection import RiskRejectionReason
from risk_engine.contracts.risk_config import RiskConfig

class PositionSizer:
    MAX_RISK_FRACTION = 0.01  # 1.0% maximum absolute cap

    @staticmethod
    def calculate(plan: TradePlanPayload, account_state: AccountState, config: RiskConfig) -> Tuple[Optional[float], Optional[float], Optional[RiskRejectionReason]]:
        """
        Returns (position_units, dollar_risk, rejection_reason)
        """
        # Calculate maximum allowed risk based on current liquid equity
        max_risk_fraction = min(config.max_risk_fraction, PositionSizer.MAX_RISK_FRACTION)
        dollar_risk = account_state.current_equity * max_risk_fraction
        
        # Insufficient equity check
        if dollar_risk <= 0 or account_state.current_equity <= 0:
            return None, None, RiskRejectionReason.REJECT_INSUFFICIENT_EQUITY
        
        # Layer 5: Stop distance calculation and validation
        is_long = plan.directional_permission == "PERMIT_LONG"
        if is_long:
            stop_distance = plan.entry_price - plan.stop_invalidation_price
        else:
            stop_distance = plan.stop_invalidation_price - plan.entry_price
            
        if stop_distance < 0:
            return None, None, RiskRejectionReason.REJECT_NEGATIVE_STOP_DISTANCE
        if stop_distance == 0.0:
            return None, None, RiskRejectionReason.REJECT_ZERO_STOP_DISTANCE
            
        # Enforce minimum stop distance as a percentage of entry price
        min_distance = plan.entry_price * config.min_stop_distance_pct
        if stop_distance < min_distance:
            return None, None, RiskRejectionReason.REJECT_MIN_STOP_DISTANCE_VIOLATION
            
        # Initial theoretical position sizing
        position_units = dollar_risk / stop_distance
        
        # Round to quantity step size
        import math
        step = config.quantity_step_size
        if step > 0:
            # Round down to avoid exceeding intended risk
            position_units = math.floor(position_units / step) * step
            
        # Layer 6: Min/Max Quantity validation
        if position_units < config.min_quantity or position_units <= 0:
            return None, None, RiskRejectionReason.REJECT_INVALID_POSITION_SIZE
            
        if position_units > config.max_quantity:
            return None, None, RiskRejectionReason.REJECT_QUANTITY_STEP_VIOLATION
            
        # Layer 3: Maximum Leverage Constraint
        max_notional = account_state.current_equity * config.max_leverage
        intended_notional = position_units * plan.entry_price
        
        if intended_notional > max_notional:
            return None, None, RiskRejectionReason.REJECT_MAX_LEVERAGE_VIOLATION
            
        # Layer 4: Friction-Adjusted Worst-Case Loss
        # Approximating execution costs to ensure worst-case loss is bounded
        taker_fee_rate = 0.0005
        slippage_bps = 5.0
        slippage_rate = slippage_bps / 10000.0
        
        # Friction scales with notional size
        estimated_fees = intended_notional * taker_fee_rate
        estimated_slippage = intended_notional * slippage_rate
        worst_case_loss = dollar_risk + estimated_fees + estimated_slippage
        
        # Canonical rule: Worst-case loss including friction (fees + slippage) cannot exceed 1.20x dollar_risk (20% friction limit)
        if worst_case_loss > dollar_risk * 1.2:
            return None, None, RiskRejectionReason.REJECT_FRICTION_ADJUSTED_RISK_VIOLATION
            
        return position_units, dollar_risk, None
