from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

from market_intelligence.primitives import Candle, RawSwing, SwingType

class SetupState(Enum):
    WAITING_75 = "WAITING_75"
    WAITING_25 = "WAITING_25"
    WAITING_CROSSOVER = "WAITING_CROSSOVER"
    READY = "READY"

@dataclass
class TimeframeContext:
    tf_name: str
    supertrend: float = 0.0
    st_direction: int = 0
    k: float = 50.0
    d: float = 50.0
    
    # State tracking
    state: SetupState = SetupState.WAITING_25
    condition_met_ts: Optional[int] = None
    target_price: Optional[float] = None

@dataclass
class StrategyCandidateLogic:
    """
    Evaluates the strict conditions for the candidate strategy.
    """
    
    @staticmethod
    def extract_target_swing(swings: List[RawSwing], current_ts: int, direction: int) -> Optional[float]:
        """
        Extracts the relevant previous high/swing prior to the pullback.
        direction: 1 for bullish (needs HIGH), -1 for bearish (needs LOW)
        """
        valid_swings = [s for s in swings if s.confirmation_timestamp <= current_ts]
        target_type = SwingType.HIGH if direction == 1 else SwingType.LOW
        
        for i in range(len(valid_swings)-1, -1, -1):
            if valid_swings[i].swing_type == target_type:
                return valid_swings[i].price
        return None

    @staticmethod
    def evaluate_htf(context: TimeframeContext, st_dir: int, k: float, swings: List[RawSwing], current_ts: int, direction: int):
        context.st_direction = st_dir
        context.k = k
        
        if direction == 1:
            if st_dir != 1:
                context.state = SetupState.WAITING_25
                context.condition_met_ts = None
                return
                
            if context.state == SetupState.WAITING_25:
                if k <= 25.0:
                    context.state = SetupState.READY
                    context.condition_met_ts = current_ts
                    context.target_price = StrategyCandidateLogic.extract_target_swing(swings, current_ts, direction)
        else:
            if st_dir != -1:
                context.state = SetupState.WAITING_25
                context.condition_met_ts = None
                return
                
            if context.state == SetupState.WAITING_25:
                if k >= 75.0:
                    context.state = SetupState.READY
                    context.condition_met_ts = current_ts
                    context.target_price = StrategyCandidateLogic.extract_target_swing(swings, current_ts, direction)

    @staticmethod
    def evaluate_mtf(context: TimeframeContext, st_dir: int, k: float, swings: List[RawSwing], current_ts: int, direction: int):
        context.st_direction = st_dir
        context.k = k
        
        if direction == 1:
            if st_dir != 1:
                context.state = SetupState.WAITING_75
                context.condition_met_ts = None
                return
                
            if context.state == SetupState.WAITING_75:
                if k >= 75.0:
                    context.state = SetupState.WAITING_25
            elif context.state == SetupState.WAITING_25:
                if k <= 25.0:
                    context.state = SetupState.READY
                    context.condition_met_ts = current_ts
                    context.target_price = StrategyCandidateLogic.extract_target_swing(swings, current_ts, direction)
        else:
            if st_dir != -1:
                context.state = SetupState.WAITING_75
                context.condition_met_ts = None
                return
                
            if context.state == SetupState.WAITING_75:
                if k <= 25.0:
                    context.state = SetupState.WAITING_25
            elif context.state == SetupState.WAITING_25:
                if k >= 75.0:
                    context.state = SetupState.READY
                    context.condition_met_ts = current_ts
                    context.target_price = StrategyCandidateLogic.extract_target_swing(swings, current_ts, direction)

    @staticmethod
    def evaluate_ltf(context: TimeframeContext, st_dir: int, k: float, d: float, prev_k: float, prev_d: float, swings: List[RawSwing], current_ts: int, direction: int):
        context.st_direction = st_dir
        context.k = k
        context.d = d
        
        if direction == 1:
            if st_dir != 1:
                context.state = SetupState.WAITING_75
                context.condition_met_ts = None
                return
                
            if context.state == SetupState.WAITING_75:
                if k >= 75.0:
                    context.state = SetupState.WAITING_25
            elif context.state == SetupState.WAITING_25:
                if k <= 25.0:
                    context.state = SetupState.WAITING_CROSSOVER
            elif context.state == SetupState.WAITING_CROSSOVER:
                # Need K to cross above D
                if prev_k <= prev_d and k > d:
                    context.state = SetupState.READY
                    context.condition_met_ts = current_ts
                    context.target_price = StrategyCandidateLogic.extract_target_swing(swings, current_ts, direction)
        else:
            if st_dir != -1:
                context.state = SetupState.WAITING_75
                context.condition_met_ts = None
                return
                
            if context.state == SetupState.WAITING_75:
                if k <= 25.0:
                    context.state = SetupState.WAITING_25
            elif context.state == SetupState.WAITING_25:
                if k >= 75.0:
                    context.state = SetupState.WAITING_CROSSOVER
            elif context.state == SetupState.WAITING_CROSSOVER:
                # Need K to cross below D
                if prev_k >= prev_d and k < d:
                    context.state = SetupState.READY
                    context.condition_met_ts = current_ts
                    context.target_price = StrategyCandidateLogic.extract_target_swing(swings, current_ts, direction)
