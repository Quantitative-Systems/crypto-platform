from dataclasses import dataclass, field
from typing import Dict

@dataclass
class AccountState:
    """
    Snapshot of the account's current capital and exposure state.
    """
    current_equity: float
    peak_equity: float
    daily_pnl: float
    weekly_pnl: float
    open_position_count: int
    active_assets: Dict[str, float] = field(default_factory=dict)  # Maps asset symbol to its current percentage exposure
