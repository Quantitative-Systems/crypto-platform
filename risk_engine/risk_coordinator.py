from typing import Union
from strategy_engine.contracts.trade_plan import TradePlanPayload
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.contracts.risk_rejection import RiskRejectionPayload, RiskRejectionReason
from risk_engine.validators.rr_validator import RRValidator
from risk_engine.validators.drawdown_validator import DrawdownValidator
from risk_engine.validators.exposure_validator import ExposureValidator
from risk_engine.sizing.position_sizer import PositionSizer

class RiskCoordinator:
    """
    Pure orchestrator. Evaluates TradePlanPayloads against Risk Firewall boundaries.
    """
    
    @staticmethod
    def _reject(plan: TradePlanPayload, reason: RiskRejectionReason) -> RiskRejectionPayload:
        return RiskRejectionPayload(
            trade_plan_id=plan.trade_plan_id,
            hypothesis_id=plan.hypothesis_id,
            symbol=plan.symbol,
            reason=reason,
            entry_price=plan.entry_price,
            stop_loss_price=plan.stop_invalidation_price,
            target_price=plan.target_price,
            raw_rr=plan.raw_rr
        )

    @staticmethod
    def evaluate(plan: TradePlanPayload, account_state: AccountState) -> Union[RiskApprovedPlan, RiskRejectionPayload]:
        
        # 1. Structural Validation (R:R Floor)
        rr_rejection = RRValidator.validate(plan)
        if rr_rejection:
            return RiskCoordinator._reject(plan, rr_rejection)
            
        # 2. Capital Circuit Breakers (Drawdown)
        dd_rejection = DrawdownValidator.validate(account_state)
        if dd_rejection:
            return RiskCoordinator._reject(plan, dd_rejection)
            
        # 3. Portfolio Exposure Validation
        exp_rejection = ExposureValidator.validate(plan, account_state)
        if exp_rejection:
            return RiskCoordinator._reject(plan, exp_rejection)
            
        # 4. Position Sizing Calculation
        position_units, dollar_risk, sizing_rejection = PositionSizer.calculate(plan, account_state)
        if sizing_rejection:
            return RiskCoordinator._reject(plan, sizing_rejection)
            
        # All gates cleared. Emit execution-ready plan.
        return RiskApprovedPlan(
            trade_plan_id=plan.trade_plan_id,
            hypothesis_id=plan.hypothesis_id,
            symbol=plan.symbol,
            entry_price=plan.entry_price,
            stop_loss_price=plan.stop_invalidation_price,
            target_price=plan.target_price,
            position_units=position_units, # type: ignore
            dollar_risk=dollar_risk, # type: ignore
            max_loss_pct=PositionSizer.MAX_RISK_FRACTION
        )
