from dataclasses import dataclass, field
from typing import Optional, Dict
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.contracts.trade_plan import DirectionalPermission

@dataclass
class CandidateSetup:
    """
    Mutable state tracker for a candidate setup across multiple candles.
    """
    candidate_id: str
    hypothesis_id: str
    symbol: str
    htf: str
    mtf: str
    ltf: str
    
    state: CandidateState
    directional_permission: DirectionalPermission
    
    # Anchor provenance
    htf_keyzone_id: Optional[str] = None
    mtf_keyzone_id: Optional[str] = None
    mtf_choch_id: Optional[str] = None
    
    # Tracked Structural Boundaries
    htf_target_price: Optional[float] = None
    
    def transition_to(self, new_state: CandidateState):
        self.state = new_state


class CandidateTracker:
    """
    In-memory state tracker for candidates.
    In a live DB-backed system, this would write to Redis/Postgres.
    """
    def __init__(self):
        # Maps candidate_id -> CandidateSetup
        self.active_candidates: Dict[str, CandidateSetup] = {}
        
    def add_candidate(self, candidate: CandidateSetup):
        self.active_candidates[candidate.candidate_id] = candidate
        
    def get_active_candidates(self, symbol: str, hypothesis_id: str) -> list[CandidateSetup]:
        return [c for c in self.active_candidates.values() 
                if c.symbol == symbol and c.hypothesis_id == hypothesis_id]
                
    def remove_candidate(self, candidate_id: str):
        if candidate_id in self.active_candidates:
            del self.active_candidates[candidate_id]
