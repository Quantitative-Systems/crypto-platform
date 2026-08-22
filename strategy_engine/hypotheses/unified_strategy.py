"""
Product 02 — Strategy Engine: Unified Strategy
Implements canonical unified state-machine:
HTF Bias -> HTF Keyzone Interaction -> MTF Setup (Re-alignment) -> MTF Keyzone Retest -> LTF Entry Model.
"""

from typing import Optional
from strategy_engine.hypotheses.base_hypothesis import BaseHypothesis
from market_intelligence.primitives import MarketStatePayload
from strategy_engine.contracts.trade_plan import TradePlanPayload, DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.contracts.telemetry import TelemetryHelper
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.entry.ltf_entry_model import LTFEntryModel


class UnifiedStrategy(BaseHypothesis):
    @property
    def hypothesis_id(self) -> str:
        return "UNIFIED_STRATEGY"

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
        
        # Trade direction based on HTF Bias
        is_long = candidate.directional_permission == DirectionalPermission.PERMIT_LONG
        req_setup_dir = "BULLISH" if is_long else "BEARISH"
        opposing_setup_dir = "BEARISH" if is_long else "BULLISH"
        
        # Check Candidate Expiration
        if candidate.is_expired(ltf_payload.timestamp):
            candidate.transition_to(CandidateState.REJECTED)
            candidate.invalidation_reason = "REJECT_SETUP_LIFESPAN_EXPIRED"
            candidate.invalidation_timestamp = ltf_payload.timestamp
            return TelemetryHelper.reject(
                candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                ltf_payload.timestamp, "REJECT_SETUP_LIFESPAN_EXPIRED",
                structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
            )

        # =========================================================================
        # 0. STRUCTURAL INVALIDATION ENGINE
        # =========================================================================
        # Invalidation 1: Parent HTF context is superseded by a newer HTF structural event
        htf_events = getattr(htf_payload.structure_state, 'events', None) or htf_payload.events or []
        if candidate.htf_context_timestamp:
            for ev in reversed(htf_events):
                ev_ts = getattr(ev, 'timestamp', 0)
                if ev_ts > candidate.htf_context_timestamp:
                    if "BOS" in str(ev.event_type) or "CHOCH" in str(ev.event_type):
                        candidate.transition_to(CandidateState.REJECTED)
                        candidate.invalidation_reason = "REJECT_SUPERSEDED_HTF_CONTEXT"
                        candidate.invalidation_timestamp = ev_ts
                        return TelemetryHelper.reject(
                            candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                            ltf_payload.timestamp, "REJECT_SUPERSEDED_HTF_CONTEXT",
                            structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                        )

        # Invalidation 2: Opposing MTF BOS/CHOCH invalidates the setup after alignment
        mtf_events = getattr(mtf_payload.structure_state, 'events', None) or mtf_payload.events or []
        if candidate.state in [CandidateState.WAIT_MTF_RETEST, CandidateState.WAIT_LTF_TRIGGER, CandidateState.RISK_GATE]:
            if candidate.mtf_alignment_timestamp:
                for ev in reversed(mtf_events):
                    ev_ts = getattr(ev, 'timestamp', 0)
                    if ev_ts > candidate.mtf_alignment_timestamp:
                        ev_dir = getattr(ev, 'direction', None) or (ev.metadata.get('direction', '') if hasattr(ev, 'metadata') else '')
                        if ("CHOCH" in str(ev.event_type) or "BOS" in str(ev.event_type)) and opposing_setup_dir in str(ev_dir):
                            candidate.transition_to(CandidateState.REJECTED)
                            candidate.invalidation_reason = "REJECT_OPPOSING_MTF_STRUCTURE"
                            candidate.invalidation_timestamp = ev_ts
                            return TelemetryHelper.reject(
                                candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                                ltf_payload.timestamp, "REJECT_OPPOSING_MTF_STRUCTURE",
                                structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                            )

        # Invalidation 3: Price breaks structural origin of the MTF KeyZone
        if candidate.state in [CandidateState.WAIT_MTF_RETEST, CandidateState.WAIT_LTF_TRIGGER, CandidateState.RISK_GATE]:
            if candidate.mtf_keyzone_id:
                for kz in mtf_payload.keyzones:
                    if getattr(kz, 'zone_id', '') == candidate.mtf_keyzone_id:
                        if "INVALIDATED" in str(getattr(kz, 'status', '')):
                            candidate.transition_to(CandidateState.REJECTED)
                            candidate.invalidation_reason = "REJECT_STRUCTURAL_ORIGIN_BROKEN"
                            candidate.invalidation_timestamp = mtf_payload.timestamp
                            return TelemetryHelper.reject(
                                candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                                ltf_payload.timestamp, "REJECT_STRUCTURAL_ORIGIN_BROKEN",
                                structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                            )
                        # Check price breach beyond the origin boundary
                        high_bound = getattr(kz, 'high_boundary', getattr(kz, 'high', None))
                        low_bound = getattr(kz, 'low_boundary', getattr(kz, 'low', None))
                        if not is_long and high_bound is not None:  # Short setup: invalid if price breaks above keyzone origin
                            if mtf_payload.current_price > high_bound:
                                candidate.transition_to(CandidateState.REJECTED)
                                candidate.invalidation_reason = "REJECT_STRUCTURAL_ORIGIN_BROKEN"
                                candidate.invalidation_timestamp = mtf_payload.timestamp
                                return TelemetryHelper.reject(
                                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                                    ltf_payload.timestamp, "REJECT_STRUCTURAL_ORIGIN_BROKEN",
                                    structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                                )
                        elif is_long and low_bound is not None:  # Long setup: invalid if price breaks below keyzone origin
                            if mtf_payload.current_price < low_bound:
                                candidate.transition_to(CandidateState.REJECTED)
                                candidate.invalidation_reason = "REJECT_STRUCTURAL_ORIGIN_BROKEN"
                                candidate.invalidation_timestamp = mtf_payload.timestamp
                                return TelemetryHelper.reject(
                                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                                    ltf_payload.timestamp, "REJECT_STRUCTURAL_ORIGIN_BROKEN",
                                    structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                                )

        # =========================================================================
        # 1. WAIT_MTF_ALIGNMENT
        # =========================================================================
        if candidate.state == CandidateState.WAIT_MTF_ALIGNMENT:
            # MTF must develop structural shift aligning with HTF bias
            if mtf_events:
                for event in reversed(mtf_events):
                    event_dir = getattr(event, 'direction', None) or (event.metadata.get('direction', '') if hasattr(event, 'metadata') else '')
                    event_ts = getattr(event, 'timestamp', mtf_payload.timestamp)
                    
                    # Causality check: MTF alignment event must occur at or after HTF context timestamp
                    if candidate.htf_context_timestamp and event_ts < candidate.htf_context_timestamp:
                        break

                    is_choch = "CHOCH" in str(event.event_type) or "MSS" in str(event.event_type)
                    is_bos = "BOS" in str(event.event_type)
                    
                    if (is_choch or is_bos) and req_setup_dir in str(event_dir):
                        context = "PULLBACK" if is_choch else "CONTINUATION"
                        candidate.metadata = candidate.metadata or {}
                        candidate.metadata["context"] = context
                        
                        candidate.mtf_setup_id = f"mtf_align_{candidate.symbol}_{event_ts}"
                        candidate.mtf_setup_timestamp = event_ts
                        candidate.mtf_setup_direction = req_setup_dir
                        candidate.mtf_structural_event = str(event.event_type)
                        candidate.mtf_choch_id = getattr(event, 'broken_swing_id', None) or (event.metadata.get('broken_swing_id', '') if hasattr(event, 'metadata') else '')
                        candidate.mtf_alignment_timestamp = event_ts
                        candidate.transition_to(CandidateState.WAIT_MTF_RETEST)
                        break
            return None # Still pending
            
        # =========================================================================
        # 2. WAIT_MTF_RETEST
        # =========================================================================
        if candidate.state == CandidateState.WAIT_MTF_RETEST:
            # Filter MTF KeyZones to only those causally created at or after the MTF alignment event
            causal_zones = []
            for kz in mtf_payload.keyzones:
                kz_type_str = str(getattr(kz, 'zone_type', ''))
                if is_long and ("BULLISH" not in kz_type_str):
                    continue
                if (not is_long) and ("BEARISH" not in kz_type_str):
                    continue
                
                # Strict causality check for PULLBACK contexts: KeyZone MUST be created at or after MTF alignment timestamp
                # For CONTINUATION contexts, the keyzone can predate the most recent BOS.
                creation_ts = getattr(kz, 'creation_timestamp', None)
                context = candidate.metadata.get("context", "UNKNOWN") if candidate.metadata else "UNKNOWN"
                
                if context == "PULLBACK":
                    if candidate.mtf_alignment_timestamp and creation_ts is not None and creation_ts > 0:
                        if creation_ts < candidate.mtf_alignment_timestamp:
                            continue  # Zombie historical keyzone rejected
                
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
                    candidate.mtf_kz_creation_timestamp = getattr(kz, 'creation_timestamp', candidate.mtf_alignment_timestamp)
                    candidate.mtf_retest_timestamp = mtf_payload.timestamp
                    candidate.transition_to(CandidateState.WAIT_LTF_TRIGGER)
                    break
            return None # Still pending
            
        # =========================================================================
        # 3. WAIT_LTF_TRIGGER
        # =========================================================================
        if candidate.state == CandidateState.WAIT_LTF_TRIGGER:
            if LTFEntryModel.evaluate(ltf_payload, req_setup_dir):
                candidate.ltf_confirmation_timestamp = ltf_payload.timestamp
                candidate.ltf_entry_reason = "LTF_SWEEP_AND_DISPLACEMENT_CONFIRMED"
                candidate.transition_to(CandidateState.RISK_GATE)
            return None # Still pending
            
        # =========================================================================
        # 4. RISK_GATE
        # =========================================================================
        if candidate.state == CandidateState.RISK_GATE:
            entry_price = ltf_payload.current_price
            candidate.ltf_entry_price = entry_price
            
            # Initial SL: LTF structural invalidation point associated with entry setup
            # LONG: SL = LTF protected_low
            # SHORT: SL = LTF protected_high
            stop_price = None
            try:
                if is_long:
                    stop_price = ltf_payload.structure_state.protected_low.raw_swing.price if ltf_payload.structure_state.protected_low else None
                else:
                    stop_price = ltf_payload.structure_state.protected_high.raw_swing.price if ltf_payload.structure_state.protected_high else None
            except AttributeError:
                pass

            candidate.ltf_structural_sl = stop_price

            # Target: Derived from HTF Context Engine
            target_price = candidate.htf_target_price

            if stop_price is None or target_price is None:
                candidate.transition_to(CandidateState.REJECTED)
                candidate.invalidation_reason = "REJECT_MISSING_STRUCTURAL_ANCHORS"
                return TelemetryHelper.reject(
                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission, ltf_payload.timestamp, 
                    "REJECT_MISSING_STRUCTURAL_ANCHORS", entry_price=entry_price, stop_invalidation_price=0.0, target_price=0.0,
                    structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                )
                
            # Directional Geometry Validation
            # LONG: SL < ENTRY < TP
            # SHORT: TP < ENTRY < SL
            if is_long:
                if not (stop_price < entry_price < target_price):
                    candidate.transition_to(CandidateState.REJECTED)
                    candidate.invalidation_reason = "REJECT_INVALID_ANCHOR_GEOMETRY"
                    return TelemetryHelper.reject(
                        candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission, ltf_payload.timestamp,
                        "REJECT_INVALID_ANCHOR_GEOMETRY", entry_price=entry_price, stop_invalidation_price=stop_price, target_price=target_price, raw_rr=0.0,
                        structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                    )
            else:
                if not (target_price < entry_price < stop_price):
                    candidate.transition_to(CandidateState.REJECTED)
                    candidate.invalidation_reason = "REJECT_INVALID_ANCHOR_GEOMETRY"
                    return TelemetryHelper.reject(
                        candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission, ltf_payload.timestamp,
                        "REJECT_INVALID_ANCHOR_GEOMETRY", entry_price=entry_price, stop_invalidation_price=stop_price, target_price=target_price, raw_rr=0.0,
                        structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                    )

            # Planned RR calculated ONLY after geometry passes
            raw_rr = abs(target_price - entry_price) / abs(entry_price - stop_price)
                
            if raw_rr < 4.0:
                candidate.transition_to(CandidateState.REJECTED)
                candidate.invalidation_reason = "REJECT_RR_BELOW_4R"
                return TelemetryHelper.reject(
                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission, ltf_payload.timestamp, 
                    "REJECT_RR_BELOW_4R", entry_price=entry_price, stop_invalidation_price=stop_price, target_price=target_price, raw_rr=raw_rr,
                    structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                )
                
            candidate.transition_to(CandidateState.ENTERED)
            provenance = candidate.to_provenance_dict()
            provenance["context"] = candidate.metadata.get("context", "UNKNOWN") if candidate.metadata else "UNKNOWN"
            
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
                structural_provenance=provenance,
                source_timeframes=timeframes
            )

        return None
