import uuid
from typing import List
from market_intelligence.primitives import MarketStatePayload, MarketPhase
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
            is_long = bias == DirectionalPermission.PERMIT_LONG
            
            # --- HYP_A: Pullback Riding (Requires HTF Pullback Context + KeyZone Interaction) ---
            active_a = self.candidate_tracker.get_active_candidates(symbol, "HYP_A_PULLBACK_RIDING")
            if not active_a:
                # Find HTF KeyZone in trade direction that price is interacting with
                htf_interacting_kz = None
                for kz in htf_payload.keyzones:
                    kz_type_str = str(getattr(kz, 'zone_type', ''))
                    if is_long and ("BULLISH" not in kz_type_str):
                        continue
                    if (not is_long) and ("BEARISH" not in kz_type_str):
                        continue
                    
                    is_mitigated = "MITIGATED" in str(getattr(kz, 'status', ''))
                    high_bound = getattr(kz, 'high_boundary', getattr(kz, 'high', None))
                    low_bound = getattr(kz, 'low_boundary', getattr(kz, 'low', None))
                    price_in_zone = False
                    if high_bound is not None and low_bound is not None:
                        if htf_payload.current_candle:
                            price_in_zone = (htf_payload.current_candle.low <= high_bound and htf_payload.current_candle.high >= low_bound)
                        else:
                            price_in_zone = (low_bound <= htf_payload.current_price <= high_bound)
                            
                    if is_mitigated or price_in_zone:
                        htf_interacting_kz = kz
                        break
                
                # Create candidate if HTF KeyZone interaction or pullback phase is active
                is_pullback_phase = htf_payload.phase_state is not None and "PULLBACK" in str(htf_payload.phase_state)
                if htf_interacting_kz is not None or is_pullback_phase:
                    new_candidate = CandidateSetup(
                        candidate_id=str(uuid.uuid4()),
                        hypothesis_id="HYP_A_PULLBACK_RIDING",
                        symbol=symbol,
                        htf=htf_payload.timeframe,
                        mtf=mtf_payload.timeframe,
                        ltf=ltf_payload.timeframe,
                        state=CandidateState.WAIT_MTF_ALIGNMENT,
                        directional_permission=bias,
                        htf_keyzone_id=getattr(htf_interacting_kz, 'zone_id', None),
                        htf_interaction_timestamp=htf_payload.timestamp
                    )
                    self.candidate_tracker.add_candidate(new_candidate)

            # --- HYP_B: Continuation Riding ---
            active_b = self.candidate_tracker.get_active_candidates(symbol, "HYP_B_CONTINUATION_RIDING")
            if not active_b:
                new_candidate_b = CandidateSetup(
                    candidate_id=str(uuid.uuid4()),
                    hypothesis_id="HYP_B_CONTINUATION_RIDING",
                    symbol=symbol,
                    htf=htf_payload.timeframe,
                    mtf=mtf_payload.timeframe,
                    ltf=ltf_payload.timeframe,
                    state=CandidateState.WAIT_MTF_ALIGNMENT,
                    directional_permission=bias
                )
                self.candidate_tracker.add_candidate(new_candidate_b)
                    
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
