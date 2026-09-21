from dataclasses import dataclass

@dataclass(frozen=True)
class RiskApprovedPlan:
    """
    An execution-ready plan approved by the Risk Firewall.
    Contains strictly defined position sizing and risk exposure.
    """
    trade_plan_id: str  # Matches CandidateSetup ID
    hypothesis_id: str
    symbol: str
    
    # Prices inherited strictly from Product 02
    entry_price: float
    stop_loss_price: float
    target_price: float
    
    # Sizing determined by Product 03
    position_units: float
    dollar_risk: float
    max_loss_pct: float  # e.g., 0.01 for 1%
