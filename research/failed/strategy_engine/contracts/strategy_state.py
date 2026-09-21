from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class CanonicalState(Enum):
    """
    Authoritative 19-state lifecycle for the Canonical Multi-Timeframe Strategy.
    """
    # 1. HTF Context Lifecycle
    HTF_STRUCTURE_IDENTIFIED = "HTF_STRUCTURE_IDENTIFIED"
    HTF_BIAS_CONFIRMED = "HTF_BIAS_CONFIRMED"
    HTF_KEYZONE_IDENTIFIED = "HTF_KEYZONE_IDENTIFIED"
    HTF_CONTEXT_ACTIVE = "HTF_CONTEXT_ACTIVE"

    # 2. MTF Setup & Alignment Lifecycle
    MTF_COUNTER_PHASE = "MTF_COUNTER_PHASE"
    MTF_ALIGNMENT_DETECTED = "MTF_ALIGNMENT_DETECTED"
    MTF_STRUCTURE_CONFIRMED = "MTF_STRUCTURE_CONFIRMED"
    MTF_KEYZONE_CREATED = "MTF_KEYZONE_CREATED"
    MTF_PULLBACK_ACTIVE = "MTF_PULLBACK_ACTIVE"

    # 3. LTF Entry Model Lifecycle
    LTF_ENTRY_ARMED = "LTF_ENTRY_ARMED"
    LTF_LIQUIDITY_EVENT = "LTF_LIQUIDITY_EVENT"
    LTF_ENTRY_CONFIRMATION = "LTF_ENTRY_CONFIRMATION"

    # 4. Position & Trailing Execution Lifecycle
    TRADE_ENTERED = "TRADE_ENTERED"
    MTF_TRAILING_ACTIVE = "MTF_TRAILING_ACTIVE"

    # 5. Terminal Trade & Risk Exit States
    HTF_TARGET_REACHED = "HTF_TARGET_REACHED"
    MTF_TRAIL_EXIT = "MTF_TRAIL_EXIT"
    LTF_INVALIDATION_EXIT = "LTF_INVALIDATION_EXIT"
    RISK_EXIT = "RISK_EXIT"
    TRADE_CLOSED = "TRADE_CLOSED"

    # Terminal Rejection / Expiration States
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class CandidateState(Enum):
    """
    Candidate setup lifecycle states (backward-compatible mapping to CanonicalState).
    """
    IDLE = "IDLE"
    HTF_BIAS_IDENTIFIED = "HTF_BIAS_IDENTIFIED"
    HTF_CONTEXT_ACTIVE = "HTF_CONTEXT_ACTIVE"
    MTF_COUNTER_PHASE = "MTF_COUNTER_PHASE"
    WAIT_MTF_ALIGNMENT = "WAIT_MTF_ALIGNMENT"
    MTF_ALIGNMENT_DETECTED = "MTF_ALIGNMENT_DETECTED"
    MTF_KEYZONE_CREATED = "MTF_KEYZONE_CREATED"
    WAIT_MTF_RETEST = "WAIT_MTF_RETEST"
    MTF_PULLBACK_ACTIVE = "MTF_PULLBACK_ACTIVE"
    LTF_ENTRY_ARMED = "LTF_ENTRY_ARMED"
    WAIT_LTF_TRIGGER = "WAIT_LTF_TRIGGER"
    LTF_LIQUIDITY_EVENT = "LTF_LIQUIDITY_EVENT"
    LTF_ENTRY_CONFIRMATION = "LTF_ENTRY_CONFIRMATION"
    RISK_GATE = "RISK_GATE"
    
    # Terminal Setup States
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    ENTERED = "ENTERED"


class PositionState(Enum):
    """
    Position execution lifecycle states.
    """
    ACTIVE_POSITION = "ACTIVE_POSITION"
    MTF_TRAILING_ACTIVE = "MTF_TRAILING_ACTIVE"
    
    # Terminal Position States
    TP_EXIT = "TP_EXIT"
    HTF_TARGET_REACHED = "HTF_TARGET_REACHED"
    MTF_TRAIL_EXIT = "MTF_TRAIL_EXIT"
    LTF_SL_EXIT = "LTF_SL_EXIT"
    LTF_INVALIDATION_EXIT = "LTF_INVALIDATION_EXIT"
    RISK_EXIT = "RISK_EXIT"
    TRADE_CLOSED = "TRADE_CLOSED"


@dataclass(frozen=True)
class StateTransitionEvent:
    """
    Immutable record of an explicit state transition with complete structural evidence and provenance.
    """
    timestamp: int
    timeframe: str
    direction: str
    from_state: str
    to_state: str
    structural_evidence: str
    source_candle: Optional[Dict[str, Any]] = None
    source_swing: Optional[Dict[str, Any]] = None
    source_keyzone: Optional[Dict[str, Any]] = None
    reason_code: str = ""
    provenance: Optional[Dict[str, Any]] = None
