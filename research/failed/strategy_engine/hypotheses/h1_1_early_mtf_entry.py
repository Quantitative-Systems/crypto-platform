"""
Product 03 — Strategy Engine: Hypothesis H1.1 (Early MTF Alignment Entry)
Parent Hypothesis: HTF_TREND_CONTINUATION_V1 (Baseline Control H1)
Trial ID: Trial 2

Research Hypothesis:
By triggering execution immediately upon MTF structural shift/alignment (CHOCH/MSS)
and retest/displacement into the causal MTF keyzone (without waiting for secondary
multi-bar LTF liquidity sweep confirmation), we eliminate late-stage entry latency,
obtain superior entry prices, and reduce adverse selection stop-outs.

Preserved Invariants:
- HTF Trend / Bias / Structural Invalidation logic
- MTF Independent Structure & Keyzone Detection
- Directional Permission & Macro Destination Target
- Structural Invalidation Stop Loss & 1% Maximum Equity Risk
- Minimum Planned RR >= 4.0R Entry Qualification
- Zero Lookahead Causality & Adverse-First Intrabar Execution
"""

from typing import Optional, List
from market_intelligence.primitives import MarketStatePayload, EventType, TrendDirection
from strategy_engine.contracts.trade_plan import TradePlanPayload, DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.contracts.telemetry import TelemetryHelper
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.hypotheses.base_hypothesis import BaseHypothesis
from risk_engine.validators.rr_validator import RRValidator
from risk_engine.sizing.position_sizer import PositionSizer


class H1_1_EarlyMtfAlignmentEntry(BaseHypothesis):
    """
    Child Hypothesis H1.1: Early MTF Alignment Entry State Machine.
    """

    @property
    def hypothesis_id(self) -> str:
        return "H1.1_EARLY_MTF_ALIGNMENT_ENTRY"

    def evaluate(
        self,
        candidate: CandidateSetup,
        htf_payload: MarketStatePayload,
        mtf_payload: MarketStatePayload,
        ltf_payload: MarketStatePayload
    ) -> Optional[TradePlanPayload]:
        
        # 0. Check Setup Expiration
        if candidate.is_expired(ltf_payload.timestamp):
            candidate.transition_to(CandidateState.REJECTED)
            candidate.invalidation_reason = "REJECT_SETUP_LIFESPAN_EXPIRED"
            candidate.invalidation_timestamp = ltf_payload.timestamp
            timeframes = {
                "htf": candidate.htf or htf_payload.timeframe,
                "mtf": candidate.mtf or mtf_payload.timeframe,
                "ltf": candidate.ltf or ltf_payload.timeframe
            }
            return TelemetryHelper.reject(
                candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                ltf_payload.timestamp, "REJECT_SETUP_LIFESPAN_EXPIRED",
                structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
            )

        req_dir = DirectionalPermission.PERMIT_LONG if candidate.directional_permission == "PERMIT_LONG" else DirectionalPermission.PERMIT_SHORT
        is_long = (req_dir == DirectionalPermission.PERMIT_LONG)
        req_setup_dir = "BULLISH" if is_long else "BEARISH"
        opposing_setup_dir = "BEARISH" if is_long else "BULLISH"
        timeframes = {
            "htf": candidate.htf or htf_payload.timeframe,
            "mtf": candidate.mtf or mtf_payload.timeframe,
            "ltf": candidate.ltf or ltf_payload.timeframe
        }

        # --- Invalidation 1: Superseded HTF Context ---
        htf_events = getattr(htf_payload.structure_state, 'events', None) or htf_payload.events or []
        if candidate.state in [CandidateState.WAIT_MTF_ALIGNMENT, CandidateState.WAIT_MTF_RETEST, CandidateState.RISK_GATE]:
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

        # --- Invalidation 2: Opposing MTF BOS/CHOCH ---
        mtf_events = getattr(mtf_payload.structure_state, 'events', None) or mtf_payload.events or []
        if candidate.state in [CandidateState.WAIT_MTF_RETEST, CandidateState.RISK_GATE]:
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

        # --- Invalidation 3: Price breaks MTF KeyZone Origin ---
        if candidate.state in [CandidateState.WAIT_MTF_RETEST, CandidateState.RISK_GATE]:
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
                        high_bound = getattr(kz, 'high_boundary', getattr(kz, 'high', None))
                        low_bound = getattr(kz, 'low_boundary', getattr(kz, 'low', None))
                        if not is_long and high_bound is not None:
                            if mtf_payload.current_price > high_bound:
                                candidate.transition_to(CandidateState.REJECTED)
                                candidate.invalidation_reason = "REJECT_STRUCTURAL_ORIGIN_BROKEN"
                                candidate.invalidation_timestamp = mtf_payload.timestamp
                                return TelemetryHelper.reject(
                                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                                    ltf_payload.timestamp, "REJECT_STRUCTURAL_ORIGIN_BROKEN",
                                    structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                                )
                        elif is_long and low_bound is not None:
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
            if mtf_events:
                for event in reversed(mtf_events):
                    event_dir = getattr(event, 'direction', None) or (event.metadata.get('direction', '') if hasattr(event, 'metadata') else '')
                    event_ts = getattr(event, 'timestamp', mtf_payload.timestamp)
                    
                    if candidate.htf_context_timestamp and event_ts < candidate.htf_context_timestamp:
                        break

                    is_choch = "CHOCH" in str(event.event_type) or "MSS" in str(event.event_type)
                    is_bos = "BOS" in str(event.event_type)
                    
                    if (is_choch or is_bos) and req_setup_dir in str(event_dir):
                        candidate.mtf_setup_id = f"mtf_align_{candidate.symbol}_{event_ts}"
                        candidate.mtf_setup_timestamp = event_ts
                        candidate.mtf_setup_direction = req_setup_dir
                        candidate.mtf_structural_event = str(event.event_type)
                        candidate.mtf_choch_id = getattr(event, 'broken_swing_id', None) or (event.metadata.get('broken_swing_id', '') if hasattr(event, 'metadata') else '')
                        candidate.mtf_alignment_timestamp = event_ts
                        candidate.transition_to(CandidateState.WAIT_MTF_RETEST)
                        break
            return None

        # =========================================================================
        # 2. WAIT_MTF_RETEST (H1.1 Triggers Directly to RISK_GATE upon Retest)
        # =========================================================================
        if candidate.state == CandidateState.WAIT_MTF_RETEST:
            causal_zones = []
            for kz in mtf_payload.keyzones:
                kz_type_str = str(getattr(kz, 'zone_type', ''))
                if is_long and ("BULLISH" not in kz_type_str):
                    continue
                if (not is_long) and ("BEARISH" not in kz_type_str):
                    continue
                
                creation_ts = getattr(kz, 'creation_timestamp', None)
                if candidate.mtf_alignment_timestamp and creation_ts is not None and creation_ts > 0:
                    if creation_ts < candidate.mtf_alignment_timestamp:
                        continue
                
                causal_zones.append(kz)
                
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
                    candidate.ltf_confirmation_timestamp = ltf_payload.timestamp
                    candidate.ltf_entry_reason = "EARLY_MTF_RETEST_TRIGGER"
                    # H1.1 INNOVATION: Direct Transition to RISK_GATE
                    candidate.transition_to(CandidateState.RISK_GATE)
                    break
            return None
            
        # =========================================================================
        # 3. RISK_GATE
        # =========================================================================
        if candidate.state == CandidateState.RISK_GATE:
            entry_price = ltf_payload.current_price
            candidate.ltf_entry_price = entry_price
            
            stop_price = None
            try:
                if is_long:
                    stop_price = ltf_payload.structure_state.protected_low.raw_swing.price if ltf_payload.structure_state.protected_low else None
                else:
                    stop_price = ltf_payload.structure_state.protected_high.raw_swing.price if ltf_payload.structure_state.protected_high else None
            except AttributeError:
                pass

            candidate.ltf_structural_sl = stop_price
            target_price = candidate.htf_target_price

            if stop_price is None or target_price is None:
                candidate.transition_to(CandidateState.REJECTED)
                candidate.invalidation_reason = "REJECT_MISSING_STRUCTURAL_ANCHORS"
                return TelemetryHelper.reject(
                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                    ltf_payload.timestamp, "REJECT_MISSING_STRUCTURAL_ANCHORS",
                    structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                )
                
            if is_long and (stop_price >= entry_price or target_price <= entry_price):
                candidate.transition_to(CandidateState.REJECTED)
                candidate.invalidation_reason = "REJECT_INVALID_ANCHOR_GEOMETRY"
                return TelemetryHelper.reject(
                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                    ltf_payload.timestamp, "REJECT_INVALID_ANCHOR_GEOMETRY",
                    structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                )
            elif not is_long and (stop_price <= entry_price or target_price >= entry_price):
                candidate.transition_to(CandidateState.REJECTED)
                candidate.invalidation_reason = "REJECT_INVALID_ANCHOR_GEOMETRY"
                return TelemetryHelper.reject(
                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                    ltf_payload.timestamp, "REJECT_INVALID_ANCHOR_GEOMETRY",
                    structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                )

            is_valid_rr, raw_rr = RRValidator.validate_rr(entry_price, stop_price, target_price, min_rr=4.0)
            if not is_valid_rr:
                candidate.transition_to(CandidateState.REJECTED)
                candidate.invalidation_reason = "REJECT_RR_BELOW_4R"
                return TelemetryHelper.reject(
                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                    ltf_payload.timestamp, "REJECT_RR_BELOW_4R",
                    structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                )

            account_equity = 10000.0
            sizing_result = PositionSizer.calculate_position_size(
                account_equity=account_equity,
                entry_price=entry_price,
                stop_loss_price=stop_price,
                risk_fraction=0.01,
                min_stop_floor_pct=0.0010,
                max_leverage=10.0,
                step_size=0.0001
            )
            
            if not sizing_result.is_valid:
                candidate.transition_to(CandidateState.REJECTED)
                candidate.invalidation_reason = f"REJECT_SIZING_FAILED: {sizing_result.rejection_reason}"
                return TelemetryHelper.reject(
                    candidate.candidate_id, self.hypothesis_id, candidate.symbol, candidate.directional_permission,
                    ltf_payload.timestamp, candidate.invalidation_reason,
                    structural_provenance=candidate.to_provenance_dict(), source_timeframes=timeframes
                )

            candidate.transition_to(CandidateState.ENTERED)
            return TelemetryHelper.accept(
                candidate_id=candidate.candidate_id,
                hypothesis_id=self.hypothesis_id,
                symbol=candidate.symbol,
                directional_permission=candidate.directional_permission,
                timestamp=ltf_payload.timestamp,
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                raw_rr=raw_rr,
                position_units=sizing_result.position_units,
                dollar_risk=sizing_result.actual_dollar_risk,
                candidate=candidate,
                source_timeframes=timeframes
            )

        return None
