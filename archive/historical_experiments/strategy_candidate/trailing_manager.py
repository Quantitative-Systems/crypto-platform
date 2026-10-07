from dataclasses import dataclass
from enum import Enum

class TrailingPhase(Enum):
    PHASE_1_LTF = "PHASE_1_LTF"
    PHASE_2_WAITING_MTF = "PHASE_2_WAITING_MTF"
    PHASE_2_MTF = "PHASE_2_MTF"
    PHASE_3_WAITING_HTF = "PHASE_3_WAITING_HTF"
    PHASE_3_HTF = "PHASE_3_HTF"

@dataclass
class TrailingManager:
    direction: int
    tp1: float
    tp2: float
    tp3: float
    
    current_sl: float
    phase: TrailingPhase = TrailingPhase.PHASE_1_LTF
    
    def update(self, ltf_st: float, mtf_st: float, htf_st: float) -> float:
        if self.direction == 1:
            # Bullish
            if self.phase == TrailingPhase.PHASE_1_LTF:
                self.current_sl = max(self.current_sl, ltf_st)
                if mtf_st >= self.tp1:
                    self.phase = TrailingPhase.PHASE_2_WAITING_MTF
            
            if self.phase == TrailingPhase.PHASE_2_WAITING_MTF:
                if mtf_st >= self.current_sl:
                    self.phase = TrailingPhase.PHASE_2_MTF
                    self.current_sl = mtf_st
            elif self.phase == TrailingPhase.PHASE_2_MTF:
                self.current_sl = max(self.current_sl, mtf_st)
                if htf_st >= self.current_sl:
                    self.phase = TrailingPhase.PHASE_3_HTF
                    self.current_sl = htf_st
                    
            if self.phase == TrailingPhase.PHASE_3_HTF:
                self.current_sl = max(self.current_sl, htf_st)
                
        else:
            # Bearish
            if self.phase == TrailingPhase.PHASE_1_LTF:
                self.current_sl = min(self.current_sl, ltf_st)
                if mtf_st <= self.tp1:
                    self.phase = TrailingPhase.PHASE_2_WAITING_MTF
            
            if self.phase == TrailingPhase.PHASE_2_WAITING_MTF:
                if mtf_st <= self.current_sl:
                    self.phase = TrailingPhase.PHASE_2_MTF
                    self.current_sl = mtf_st
            elif self.phase == TrailingPhase.PHASE_2_MTF:
                self.current_sl = min(self.current_sl, mtf_st)
                if htf_st <= self.current_sl:
                    self.phase = TrailingPhase.PHASE_3_HTF
                    self.current_sl = htf_st
                    
            if self.phase == TrailingPhase.PHASE_3_HTF:
                self.current_sl = min(self.current_sl, htf_st)
                
        return self.current_sl
