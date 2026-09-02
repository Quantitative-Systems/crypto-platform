from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.contracts.trade_plan import DirectionalPermission

@dataclass
class CandidateSetup:
    """
    Mutable state tracker for a candidate setup across multiple candles.
    Maintains complete strict causal chain and structural provenance telemetry.
    """
    candidate_id: str
    hypothesis_id: str
    symbol: str
    htf: str
    mtf: str
    ltf: str
    
    state: CandidateState
    directional_permission: DirectionalPermission
    
    # 1. HTF Context Provenance
    htf_context: Optional[str] = None  # PULLBACK or CONTINUATION
    htf_context_id: Optional[str] = None
    htf_context_timestamp: Optional[int] = None
    htf_macro_direction: Optional[str] = None
    htf_phase: Optional[str] = None
    htf_expected_move: Optional[str] = None
    htf_target_price: Optional[float] = None
    htf_keyzone_id: Optional[str] = None
    htf_interaction_timestamp: Optional[int] = None
    
    # 2. MTF Setup & KeyZone Provenance
    mtf_setup_id: Optional[str] = None
    mtf_setup_timestamp: Optional[int] = None
    mtf_setup_direction: Optional[str] = None
    mtf_structural_event: Optional[str] = None
    mtf_choch_id: Optional[str] = None
    mtf_alignment_timestamp: Optional[int] = None
    mtf_keyzone_id: Optional[str] = None
    mtf_kz_creation_timestamp: Optional[int] = None
    mtf_retest_timestamp: Optional[int] = None
    
    # 3. LTF Confirmation & Invalidation Provenance
    ltf_confirmation_timestamp: Optional[int] = None
    ltf_entry_price: Optional[float] = None
    ltf_structural_sl: Optional[float] = None
    ltf_entry_reason: Optional[str] = None
    
    # Invalidation details
    invalidation_reason: Optional[str] = None
    invalidation_timestamp: Optional[int] = None
    
    # Custom arbitrary metadata
    metadata: Optional[Dict[str, Any]] = None

    # Setup Lifespan & Expiration
    creation_timestamp: Optional[int] = None
    max_lifespan_seconds: Optional[int] = None

    def is_expired(self, current_timestamp: int) -> bool:
        if not self.creation_timestamp or not self.max_lifespan_seconds:
            return False
        return (current_timestamp - self.creation_timestamp) > self.max_lifespan_seconds

    def transition_to(self, new_state: CandidateState):
        self.state = new_state

    def to_provenance_dict(self) -> Dict[str, Any]:
        return {
            "htf_context": self.htf_context or ("PULLBACK" if "PULLBACK" in str(self.htf_phase) else "CONTINUATION"),
            "htf_context_id": self.htf_context_id or "",
            "htf_context_timestamp": self.htf_context_timestamp or 0,
            "htf_macro_direction": self.htf_macro_direction or "",
            "htf_phase": self.htf_phase or "",
            "htf_expected_move": self.htf_expected_move or "",
            "htf_target_price": self.htf_target_price or 0.0,
            "htf_keyzone_id": self.htf_keyzone_id or "",
            "htf_interaction_timestamp": self.htf_interaction_timestamp or 0,
            "mtf_setup_id": self.mtf_setup_id or "",
            "mtf_setup_timestamp": self.mtf_setup_timestamp or 0,
            "mtf_setup_direction": self.mtf_setup_direction or "",
            "mtf_structural_event": self.mtf_structural_event or "",
            "mtf_choch_id": self.mtf_choch_id or "",
            "mtf_alignment_timestamp": self.mtf_alignment_timestamp or 0,
            "mtf_keyzone_id": self.mtf_keyzone_id or "",
            "mtf_kz_creation_timestamp": self.mtf_kz_creation_timestamp or 0,
            "mtf_retest_timestamp": self.mtf_retest_timestamp or 0,
            "ltf_confirmation_timestamp": self.ltf_confirmation_timestamp or 0,
            "ltf_entry_price": self.ltf_entry_price or 0.0,
            "ltf_structural_sl": self.ltf_structural_sl or 0.0,
            "ltf_entry_reason": self.ltf_entry_reason or "",
            "invalidation_reason": self.invalidation_reason or "",
            "invalidation_timestamp": self.invalidation_timestamp or 0
        }


class CandidateTracker:
    """
    In-memory state tracker for candidates.
    """
    def __init__(self):
        self.active_candidates: Dict[str, CandidateSetup] = {}
        
    def add_candidate(self, candidate: CandidateSetup):
        self.active_candidates[candidate.candidate_id] = candidate
        
    def get_active_candidates(self, symbol: str, hypothesis_id: str) -> list[CandidateSetup]:
        return [c for c in self.active_candidates.values() 
                if c.symbol == symbol and c.hypothesis_id == hypothesis_id]
                
    def remove_candidate(self, candidate_id: str):
        if candidate_id in self.active_candidates:
            del self.active_candidates[candidate_id]

    def prune_expired(self, current_timestamp: int) -> List[CandidateSetup]:
        """
        Removes and returns all active candidates that have exceeded their valid lifespan.
        """
        expired = []
        for c_id, c in list(self.active_candidates.items()):
            if c.is_expired(current_timestamp):
                c.transition_to(CandidateState.REJECTED)
                c.invalidation_reason = "REJECT_SETUP_LIFESPAN_EXPIRED"
                c.invalidation_timestamp = current_timestamp
                expired.append(c)
                del self.active_candidates[c_id]
        return expired
