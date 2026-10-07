from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional
from strategy_engine.contracts.strategy_state import CandidateState, PositionState


class DirectionalPermission(Enum):
    PERMIT_LONG = "PERMIT_LONG"
    PERMIT_SHORT = "PERMIT_SHORT"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=False)  # Mutable now since MTF trail updates and position state updates
class TradePlanPayload:
    """
    Stateful representation of an active trade plan and its trailing management.
    """
    hypothesis_id: str
    trade_plan_id: str
    symbol: str
    directional_permission: str
    setup_timestamp: int
    
    # Structural Price Levels
    entry_price: float
    stop_invalidation_price: float
    target_price: float
    
    raw_rr: float
    
    # Setup Status
    status: str  # String representation of CandidateState
    rejection_reason: Optional[str] = None
    
    # Active Position Tracking
    position_status: Optional[str] = None  # String representation of PositionState
    mtf_trailing_level: Optional[float] = None
    exit_timestamp: Optional[int] = None
    
    # Traceability back to Product 01 anchors
    structural_provenance: Dict[str, str] = field(default_factory=dict)
    
    # Source timeframes
    source_timeframes: Dict[str, str] = field(default_factory=dict)
