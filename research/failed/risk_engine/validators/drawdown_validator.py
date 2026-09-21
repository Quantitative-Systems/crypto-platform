from typing import Optional
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_rejection import RiskRejectionReason

class DrawdownValidator:
    """
    Validates daily, weekly, and systemic drawdowns against hard-coded circuit breaker limits.
    """
    MAX_DAILY_DRAWDOWN_PCT = -0.03   # 3% daily limit
    MAX_WEEKLY_DRAWDOWN_PCT = -0.06  # 6% weekly limit
    MAX_SYSTEMIC_DRAWDOWN_PCT = -0.10 # 10% peak-to-trough systemic limit

    @staticmethod
    def validate(account_state: AccountState) -> Optional[RiskRejectionReason]:
        if account_state.peak_equity > 0:
            systemic_dd = (account_state.current_equity - account_state.peak_equity) / account_state.peak_equity
            if systemic_dd <= DrawdownValidator.MAX_SYSTEMIC_DRAWDOWN_PCT:
                return RiskRejectionReason.REJECT_SYSTEMIC_CIRCUIT_BREAKER
                
        daily_balance = account_state.current_equity - account_state.daily_pnl
        if daily_balance > 0:
            daily_pct = account_state.daily_pnl / daily_balance
            if daily_pct <= DrawdownValidator.MAX_DAILY_DRAWDOWN_PCT:
                return RiskRejectionReason.REJECT_DAILY_DRAWDOWN_LIMIT
                
        weekly_balance = account_state.current_equity - account_state.weekly_pnl
        if weekly_balance > 0:
            weekly_pct = account_state.weekly_pnl / weekly_balance
            if weekly_pct <= DrawdownValidator.MAX_WEEKLY_DRAWDOWN_PCT:
                return RiskRejectionReason.REJECT_WEEKLY_DRAWDOWN_LIMIT
                
        return None
