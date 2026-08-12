from typing import Optional
from strategy_engine.hypotheses.base_hypothesis import BaseHypothesis
from market_intelligence.primitives import MarketStatePayload
from strategy_engine.contracts.trade_plan import TradePlanPayload, DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.contracts.telemetry import TelemetryHelper
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.entry.ltf_entry_model import LTFEntryModel

class PullbackRidingHypothesis(BaseHypothesis):
    @property
    def hypothesis_id(self) -> str:
        return "HYP_A_PULLBACK_RIDING"

    def evaluate(
        self,
        candidate: CandidateSetup,
        htf_payload: MarketStatePayload,
        mtf_payload: MarketStatePayload,
        ltf_payload: MarketStatePayload
    ) -> Optional[TradePlanPayload]:
        
        timeframes = {
            "HTF": htf_payload.timeframe,
            "MTF": mtf_payload.timeframe,
            "LTF": ltf_payload.timeframe
        }
        
        is_long = candidate.directional_permission == DirectionalPermission.PERMIT_LONG
        req_event_dir = "BULLISH" if is_long else "BEARISH"
        
        # 1. WAIT_MTF_ALIGNMENT
        if candidate.state == CandidateState.WAIT_MTF_ALIGNMENT:
            mtf_events = mtf_payload.structure_state.events
            if mtf_events:
                last_event = mtf_events[-1]
                if "CHOCH" in str(last_event.event_type) and req_event_dir in str(last_event.direction):
                    # Alignment confirmed. 
                    candidate.mtf_choch_id = last_event.broken_swing_id
                    candidate.transition_to(CandidateState.WAIT_MTF_RETEST)
            return None # Still pending or just transitioned
            
        # 2. WAIT_MTF_RETEST
        if candidate.state == CandidateState.WAIT_MTF_RETEST:
            # Check if any MTF KeyZone is mitigated (retest)
            mtf_mitigated = [kz for kz in mtf_payload.keyzones if "MITIGATED" in str(kz.status)]
            if mtf_mitigated:
                candidate.mtf_keyzone_id = mtf_mitigated[-1].zone_id
                candidate.transition_to(CandidateState.WAIT_LTF_TRIGGER)
            return None # Still pending
            
        # 3. WAIT_LTF_TRIGGER
        if candidate.state == CandidateState.WAIT_LTF_TRIGGER:
            if LTFEntryModel.evaluate(ltf_payload, req_event_dir):
                candidate.transition_to(CandidateState.RISK_GATE)
            return None # Still pending
            
        # 4. RISK_GATE
        if candidate.state == CandidateState.RISK_GATE:
            entry_price = ltf_payload.current_price
            
            try:
                if is_long:
                    stop_price = ltf_payload.structure_state.protected_low.raw_swing.price
                    target_price = htf_payload.structure_state.weak_high.raw_swing.price
                    raw_rr = (target_price - entry_price) / (entry_price - stop_price) if entry_price > stop_price else 0.0
                else:
                    stop_price = ltf_payload.structure_state.protected_high.raw_swing.price
                    target_price = htf_payload.structure_state.weak_low.raw_swing.price
                    raw_rr = (entry_price - target_price) / (stop_price - entry_price) if stop_price > entry_price else 0.0
            except AttributeError as e:
                import traceback
                traceback.print_exc()
                candidate.transition_to(CandidateState.REJECTED)
                return TelemetryHelper.reject(
                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission, ltf_payload.timestamp, 
                    "REJECT_MISSING_STRUCTURAL_ANCHORS", source_timeframes=timeframes
                )
                
            if raw_rr < 4.0:
                candidate.transition_to(CandidateState.REJECTED)
                return TelemetryHelper.reject(
                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission, ltf_payload.timestamp, 
                    "REJECT_RR_BELOW_4R", entry_price=entry_price, stop_invalidation_price=stop_price, target_price=target_price, raw_rr=raw_rr, source_timeframes=timeframes
                )
                
            candidate.transition_to(CandidateState.ENTERED)
            return TradePlanPayload(
                trade_plan_id=candidate.candidate_id,
                hypothesis_id=self.hypothesis_id,
                symbol=candidate.symbol,
                directional_permission=candidate.directional_permission.value,
                setup_timestamp=ltf_payload.timestamp,
                entry_price=entry_price,
                stop_invalidation_price=stop_price,
                target_price=target_price,
                raw_rr=raw_rr,
                status=CandidateState.ENTERED.value,
                structural_provenance={
                    "mtf_choch_id": candidate.mtf_choch_id or "",
                    "mtf_kz_id": candidate.mtf_keyzone_id or ""
                },
                source_timeframes=timeframes
            )
            
        return None
