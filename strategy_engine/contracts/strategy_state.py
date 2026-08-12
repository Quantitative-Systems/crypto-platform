from enum import Enum

class CandidateState(Enum):
    IDLE = "IDLE"
    HTF_BIAS_IDENTIFIED = "HTF_BIAS_IDENTIFIED"
    WAIT_MTF_ALIGNMENT = "WAIT_MTF_ALIGNMENT"
    WAIT_MTF_RETEST = "WAIT_MTF_RETEST"
    WAIT_LTF_TRIGGER = "WAIT_LTF_TRIGGER"
    RISK_GATE = "RISK_GATE"
    
    # Terminal Setup States
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    ENTERED = "ENTERED"


class PositionState(Enum):
    ACTIVE_POSITION = "ACTIVE_POSITION"
    
    # Terminal Position States
    TP_EXIT = "TP_EXIT"
    MTF_TRAIL_EXIT = "MTF_TRAIL_EXIT"
    LTF_SL_EXIT = "LTF_SL_EXIT"
