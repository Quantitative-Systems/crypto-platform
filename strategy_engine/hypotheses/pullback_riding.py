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
            mtf_events = getattr(mtf_payload.structure_state, 'events', None) or mtf_payload.events
            if mtf_events:
                for event in reversed(mtf_events):
                    event_dir = getattr(event, 'direction', None) or (event.metadata.get('direction', '') if hasattr(event, 'metadata') else '')
                    if "CHOCH" in str(event.event_type) and req_event_dir in str(event_dir):
                        # Alignment confirmed. Record causal timestamp and swing ID.
                        candidate.mtf_choch_id = getattr(event, 'broken_swing_id', None) or (event.metadata.get('broken_swing_id', '') if hasattr(event, 'metadata') else '')
                        candidate.mtf_alignment_timestamp = getattr(event, 'timestamp', mtf_payload.timestamp)
                        candidate.transition_to(CandidateState.WAIT_MTF_RETEST)
                        break
            return None # Still pending or just transitioned
            
        # 2. WAIT_MTF_RETEST
        if candidate.state == CandidateState.WAIT_MTF_RETEST:
            # Filter MTF KeyZones to only those causally created at or after the MTF alignment event
            causal_zones = []
            for kz in mtf_payload.keyzones:
                kz_type_str = str(getattr(kz, 'zone_type', ''))
                if is_long and ("BULLISH" not in kz_type_str):
                    continue
                if (not is_long) and ("BEARISH" not in kz_type_str):
                    continue
                
                # Causal timestamp check: Must be created at or after alignment event
                creation_ts = getattr(kz, 'creation_timestamp', None)
                if candidate.mtf_alignment_timestamp and creation_ts is not None and creation_ts > 0:
                    if creation_ts < candidate.mtf_alignment_timestamp:
                        continue  # Stale historical keyzone rejected
                
                causal_zones.append(kz)
                
            # Check if any causal MTF KeyZone is mitigated or retested
            for kz in causal_zones:
                is_mitigated = "MITIGATED" in str(getattr(kz, 'status', ''))
                price_in_zone = False
                high_bound = getattr(kz, 'high_boundary', getattr(kz, 'high', None))
                low_bound = getattr(kz, 'low_boundary', getattr(kz, 'low', None))
                if high_bound is not None and low_bound is not None:
                    if mtf_payload.current_candle:
                        price_in_zone = (mtf_payload.current_candle.low <= high_bound and mtf_payload.current_candle.high >= low_bound)
                    else:
                        price_in_zone = (low_bound <= mtf_payload.current_price <= high_bound)
                
                if is_mitigated or price_in_zone:
                    candidate.mtf_keyzone_id = getattr(kz, 'zone_id', '')
                    candidate.transition_to(CandidateState.WAIT_LTF_TRIGGER)
                    break
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
                    target_price = htf_payload.structure_state.protected_high.raw_swing.price
                    raw_rr = (target_price - entry_price) / (entry_price - stop_price) if entry_price > stop_price else 0.0
                else:
                    stop_price = ltf_payload.structure_state.protected_high.raw_swing.price
                    target_price = htf_payload.structure_state.protected_low.raw_swing.price
                    raw_rr = (entry_price - target_price) / (stop_price - entry_price) if stop_price > entry_price else 0.0
            except AttributeError as e:
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
                    "htf_kz_id": candidate.htf_keyzone_id or "",
                    "mtf_choch_id": candidate.mtf_choch_id or "",
                    "mtf_kz_id": candidate.mtf_keyzone_id or "",
                    "mtf_alignment_ts": candidate.mtf_alignment_timestamp or 0
                },
                source_timeframes=timeframes
            )
            
        return None
