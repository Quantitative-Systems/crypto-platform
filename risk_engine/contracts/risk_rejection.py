from dataclasses import dataclass
from enum import Enum

class RiskRejectionReason(Enum):
    REJECT_RR_BELOW_FLOOR = "REJECT_RR_BELOW_FLOOR"
    REJECT_RISK_ABOVE_MAXIMUM = "REJECT_RISK_ABOVE_MAXIMUM"
    REJECT_DAILY_DRAWDOWN_LIMIT = "REJECT_DAILY_DRAWDOWN_LIMIT"
    REJECT_WEEKLY_DRAWDOWN_LIMIT = "REJECT_WEEKLY_DRAWDOWN_LIMIT"
    REJECT_SYSTEMIC_CIRCUIT_BREAKER = "REJECT_SYSTEMIC_CIRCUIT_BREAKER"
    REJECT_MAX_OPEN_POSITIONS = "REJECT_MAX_OPEN_POSITIONS"
    REJECT_MAX_ASSET_EXPOSURE = "REJECT_MAX_ASSET_EXPOSURE"
    REJECT_CORRELATED_EXPOSURE = "REJECT_CORRELATED_EXPOSURE"
    REJECT_INVALID_STOP = "REJECT_INVALID_STOP"
    REJECT_INVALID_POSITION_SIZE = "REJECT_INVALID_POSITION_SIZE"

@dataclass(frozen=True)
class RiskRejectionPayload:
    """
    Telemetry artifact for trades blocked by the Risk Firewall.
    Preserves structural provenance for downstream funnel analytics.
    """
    trade_plan_id: str
    hypothesis_id: str
    symbol: str
    reason: RiskRejectionReason
    
    # Original structural metrics
    entry_price: float
    stop_loss_price: float
    target_price: float
    raw_rr: float
