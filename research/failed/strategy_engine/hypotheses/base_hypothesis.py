from abc import ABC, abstractmethod
from typing import Optional, List
from market_intelligence.primitives import MarketStatePayload
from strategy_engine.contracts.trade_plan import TradePlanPayload
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup

class BaseHypothesis(ABC):
    """
    Abstract interface for all stateful trading hypotheses.
    """
    
    @property
    @abstractmethod
    def hypothesis_id(self) -> str:
        """Unique identifier for the hypothesis"""
        pass
        
    @abstractmethod
    def evaluate(
        self,
        candidate: CandidateSetup,
        htf_payload: MarketStatePayload,
        mtf_payload: MarketStatePayload,
        ltf_payload: MarketStatePayload
    ) -> Optional[TradePlanPayload]:
        """
        Evaluate the candidate setup against new payloads and progress its state machine.
        Returns a TradePlanPayload if the setup reaches terminal state (VALIDATED or REJECTED).
        Returns None if the setup is still pending.
        """
        pass
