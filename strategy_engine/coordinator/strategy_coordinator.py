import uuid
from typing import List
from market_intelligence.primitives import MarketStatePayload
from strategy_engine.contracts.trade_plan import TradePlanPayload
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.classifiers.bias_classifier import BiasClassifier
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.hypotheses.continuation_riding import ContinuationRidingHypothesis
from strategy_engine.hypotheses.pullback_riding import PullbackRidingHypothesis
from strategy_engine.lifecycle.candidate_tracker import CandidateTracker, CandidateSetup
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager

class StrategyCoordinator:
    """
    Stateful orchestrator coordinating candidates across multiple candles and managing active trades.
    """
    
    def __init__(self):
        self.hypotheses = {
            "HYP_A_PULLBACK_RIDING": PullbackRidingHypothesis(),
            "HYP_B_CONTINUATION_RIDING": ContinuationRidingHypothesis()
        }
        self.candidate_tracker = CandidateTracker()
        self.active_manager = ActiveTradeManager()
        
    def evaluate(
        self,
        htf_payload: MarketStatePayload,
        mtf_payload: MarketStatePayload,
        ltf_payload: MarketStatePayload
    ) -> List[TradePlanPayload]:
        
        trade_plans = []
        symbol = htf_payload.symbol
        
        # 1. Evaluate Active Trades (MTF Trailing, TP, SL)
        exited_trades = self.active_manager.evaluate(htf_payload, mtf_payload, ltf_payload)
        trade_plans.extend(exited_trades)
        
        # 2. Check for New HTF Bias to create new CandidateSetups
        bias = BiasClassifier.evaluate(htf_payload)
        if bias != DirectionalPermission.NO_TRADE:
            # We could start tracking candidates for both hypotheses
            for hyp_id in self.hypotheses.keys():
                # For simplicity, if we don't already have an active candidate for this hyp, create one.
                active_cands = self.candidate_tracker.get_active_candidates(symbol, hyp_id)
                if not active_cands:
                    new_candidate = CandidateSetup(
                        candidate_id=str(uuid.uuid4()),
                        hypothesis_id=hyp_id,
                        symbol=symbol,
                        htf=htf_payload.timeframe,
                        mtf=mtf_payload.timeframe,
                        ltf=ltf_payload.timeframe,
                        state=CandidateState.WAIT_MTF_ALIGNMENT,
                        directional_permission=bias
                    )
                    self.candidate_tracker.add_candidate(new_candidate)
                    
        # 3. Progress Active Candidate Setups
        # Iterate over a copy since evaluate might cause removals
        for hyp_id, hypothesis in self.hypotheses.items():
            candidates = self.candidate_tracker.get_active_candidates(symbol, hyp_id)
            for candidate in candidates:
                try:
                    plan = hypothesis.evaluate(candidate, htf_payload, mtf_payload, ltf_payload)
                    
                    if plan:
                        trade_plans.append(plan)
                        self.candidate_tracker.remove_candidate(candidate.candidate_id)
                        
                        if plan.status == CandidateState.ENTERED.value:
                            self.active_manager.register_trade(candidate.candidate_id, plan)
                            
                except Exception as e:
                    self.candidate_tracker.remove_candidate(candidate.candidate_id)
                    raise RuntimeError(f"Hypothesis {hyp_id} failed during state evaluation: {str(e)}") from e
                    
        return trade_plans
