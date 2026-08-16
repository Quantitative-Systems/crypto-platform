"""
Forensic Funnel Diagnostic Script for VS001 (BTCUSDT S3: 1D -> 4H -> 1H).
Instruments and traces every stage of the funnel causally without modifying production logic.
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.primitives import Candle, MarketStatePayload
from strategy_engine.contracts.trade_plan import DirectionalPermission, TradePlanPayload
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.classifiers.bias_classifier import BiasClassifier
from strategy_engine.entry.ltf_entry_model import LTFEntryModel
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup, CandidateTracker
from strategy_engine.hypotheses.pullback_riding import PullbackRidingHypothesis
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from research.replayer.timeframe_aligner import TimeframeAligner, TimeframeSet
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.simulation.execution_simulator import ExecutionSimulator

def format_ts(ts: int) -> str:
    return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S UTC')

def run_diagnostic():
    print("================================================================================")
    print("           DAY 34 — VS001 G4 FORENSIC FUNNEL DIAGNOSTIC RUN                     ")
    print("================================================================================")

    # 1. Load data
    loader = WarehouseLoader()
    htf_candles = loader.load_history("BTCUSDT", "1D", limit=50000)
    mtf_candles = loader.load_history("BTCUSDT", "4H", limit=50000)
    ltf_candles = loader.load_history("BTCUSDT", "1H", limit=50000)

    timeframe_set = TimeframeAligner.get_set("SET_3") # 1D -> 4H -> 1H
    symbol = "BTCUSDT"
    min_lookback_bars = 15

    language_coordinator = LanguageCoordinator(buffer_size=300)
    hypothesis = PullbackRidingHypothesis()
    execution_simulator = ExecutionSimulator()
    ledger = TradeLedger(initial_equity=10000.0)

    # State caches
    _htf_cache = {"key": None, "state": None}
    _mtf_cache = {"key": None, "state": None}

    # Tracking counters
    counts = {
        "1_total_replayed_1h_events": 0,
        "2_valid_htf_bias": 0,
        "3_htf_phase_recognized": 0,
        "4_htf_keyzone_interaction": 0,
        "5_mtf_structure_alignment": 0,
        "6_mtf_choch_confirmations": 0,
        "7_mtf_keyzone_candidates": 0,
        "8_mtf_keyzone_causal_valid": 0,
        "9_mtf_keyzone_retests": 0,
        "10_ltf_entry_model_candidates": 0,
        "11_ltf_liquidity_sweeps": 0,
        "12_ltf_displacement_confirmed": 0,
        "13_candidate_setups_created": 0,
        "14_planned_rr_calculations": 0,
        "15_rejected_by_rr_below_4": 0,
        "16_rejected_by_risk_firewall": 0,
        "17_risk_approved_plans": 0,
        "18_executed_trades": 0,
    }

    # Diagnostic tracking for near misses
    all_candidates_log: List[Dict[str, Any]] = []
    active_candidate: Optional[CandidateSetup] = None
    current_candidate_diagnostic: Optional[Dict[str, Any]] = None

    for i in range(min_lookback_bars, len(ltf_candles)):
        current_bar = ltf_candles[i]
        decision_timestamp = current_bar.timestamp

        # Process orders
        execution_simulator.process_candle(current_bar, ledger)

        counts["1_total_replayed_1h_events"] += 1

        # Visible slices
        ltf_slice = ltf_candles[max(0, i - 150):i + 1]
        mtf_slice = TimeframeAligner.filter_visible_candles(
            mtf_candles, decision_timestamp, timeframe_set.mtf, buffer_size=100
        )
        htf_slice = TimeframeAligner.filter_visible_candles(
            htf_candles, decision_timestamp, timeframe_set.htf, buffer_size=80
        )

        if len(htf_slice) < 5 or len(mtf_slice) < 5 or len(ltf_slice) < 5:
            continue

        # HTF State
        htf_key = htf_slice[-1].timestamp if htf_slice else None
        if _htf_cache["key"] != htf_key:
            htf_state = language_coordinator.run(htf_slice, symbol=symbol, timeframe=timeframe_set.htf)
            _htf_cache = {"key": htf_key, "state": htf_state}
        else:
            htf_state = _htf_cache["state"]

        # MTF State
        mtf_key = mtf_slice[-1].timestamp if mtf_slice else None
        if _mtf_cache["key"] != mtf_key:
            mtf_state = language_coordinator.run(mtf_slice, symbol=symbol, timeframe=timeframe_set.mtf)
            _mtf_cache = {"key": mtf_key, "state": mtf_state}
        else:
            mtf_state = _mtf_cache["state"]

        # LTF State
        ltf_state = language_coordinator.run(ltf_slice, symbol=symbol, timeframe=timeframe_set.ltf)

        # -------------------------------------------------------------
        # DIAGNOSTIC OBSERVATION OF P01/P02 STATE
        # -------------------------------------------------------------
        # 2. HTF Bias
        bias = BiasClassifier.evaluate(htf_state)
        is_bias_valid = bias != DirectionalPermission.NO_TRADE
        if is_bias_valid:
            counts["2_valid_htf_bias"] += 1

        is_long = bias == DirectionalPermission.PERMIT_LONG
        req_dir = "BULLISH" if is_long else "BEARISH"

        # 3. HTF Phase
        phase_str = str(getattr(htf_state, 'phase_state', ''))
        is_phase_recognized = bool(phase_str and "UNDEFINED" not in phase_str and "UNKNOWN" not in phase_str)
        is_pullback = "PULLBACK" in phase_str
        if is_phase_recognized:
            counts["3_htf_phase_recognized"] += 1

        # 4. HTF KeyZone Interaction
        htf_interacting_kz = None
        for kz in htf_state.keyzones:
            kz_type_str = str(getattr(kz, 'zone_type', ''))
            if is_long and ("BULLISH" not in kz_type_str): continue
            if (not is_long) and ("BEARISH" not in kz_type_str): continue
            
            is_mitigated = "MITIGATED" in str(getattr(kz, 'status', ''))
            high_bound = getattr(kz, 'high_boundary', getattr(kz, 'high', None))
            low_bound = getattr(kz, 'low_boundary', getattr(kz, 'low', None))
            price_in_zone = False
            if high_bound is not None and low_bound is not None:
                if htf_state.current_candle:
                    price_in_zone = (htf_state.current_candle.low <= high_bound and htf_state.current_candle.high >= low_bound)
                else:
                    price_in_zone = (low_bound <= htf_state.current_price <= high_bound)
            if is_mitigated or price_in_zone:
                htf_interacting_kz = kz
                break

        if htf_interacting_kz is not None:
            counts["4_htf_keyzone_interaction"] += 1

        # 5. MTF Structure Alignment & 6. MTF CHOCH
        mtf_events = getattr(mtf_state.structure_state, 'events', None) or mtf_state.events or []
        has_mtf_alignment = False
        has_mtf_choch = False
        for event in reversed(mtf_events):
            event_dir = getattr(event, 'direction', None) or (event.metadata.get('direction', '') if hasattr(event, 'metadata') else '')
            if req_dir in str(event_dir):
                has_mtf_alignment = True
                if "CHOCH" in str(event.event_type):
                    has_mtf_choch = True
                    break

        if has_mtf_alignment and is_bias_valid:
            counts["5_mtf_structure_alignment"] += 1
        if has_mtf_choch and is_bias_valid:
            counts["6_mtf_choch_confirmations"] += 1

        # 7. MTF KeyZone candidates (in direction of trade)
        dir_mtf_kzs = [
            kz for kz in mtf_state.keyzones 
            if (is_long and "BULLISH" in str(getattr(kz, 'zone_type', ''))) or ((not is_long) and "BEARISH" in str(getattr(kz, 'zone_type', '')))
        ]
        if dir_mtf_kzs and is_bias_valid:
            counts["7_mtf_keyzone_candidates"] += len(dir_mtf_kzs)

        # LTF primitives
        ltf_all_events = ltf_state.events or []
        sweeps = [
            e for e in ltf_all_events 
            if "LIQUIDITY_SWEEP" in str(e.event_type) and req_dir in str(getattr(e, 'direction', None) or (e.metadata.get('direction', '') if hasattr(e, 'metadata') else ''))
        ]
        if sweeps and is_bias_valid:
            counts["11_ltf_liquidity_sweeps"] += 1

        scorecard = ltf_state.scorecard or {}
        reasons = scorecard.get("reason_codes", [])
        if "DISPLACEMENT_CONFIRMED" in reasons and is_bias_valid:
            counts["12_ltf_displacement_confirmed"] += 1

        # -------------------------------------------------------------
        # STATE MACHINE SIMULATION & DIAGNOSTIC TRACKING
        # -------------------------------------------------------------
        # Candidate Creation Rule (same as StrategyCoordinator)
        if is_bias_valid and (htf_interacting_kz is not None or is_pullback):
            if active_candidate is None:
                active_candidate = CandidateSetup(
                    candidate_id=f"cand_{decision_timestamp}",
                    hypothesis_id="HYP_A_PULLBACK_RIDING",
                    symbol=symbol,
                    htf=timeframe_set.htf,
                    mtf=timeframe_set.mtf,
                    ltf=timeframe_set.ltf,
                    state=CandidateState.WAIT_MTF_ALIGNMENT,
                    directional_permission=bias,
                    htf_keyzone_id=getattr(htf_interacting_kz, 'zone_id', None),
                    htf_interaction_timestamp=htf_state.timestamp
                )
                counts["13_candidate_setups_created"] += 1
                current_candidate_diagnostic = {
                    "candidate_id": active_candidate.candidate_id,
                    "timestamp": decision_timestamp,
                    "timestamp_str": format_ts(decision_timestamp),
                    "direction": bias.value if hasattr(bias, 'value') else str(bias),
                    "htf_bias": bias.value if hasattr(bias, 'value') else str(bias),
                    "htf_phase": phase_str,
                    "htf_keyzone": getattr(htf_interacting_kz, 'zone_id', 'NONE (Phase Pullback)'),
                    "mtf_structure_state": str(getattr(mtf_state.structure_state, 'trend', 'UNKNOWN')),
                    "mtf_choch_ts": None,
                    "mtf_kz_creation_ts": None,
                    "kz_preceded_shift": False,
                    "retest_occurred": False,
                    "ltf_trigger_state": "NOT_REACHED",
                    "entry_price": None,
                    "structural_sl": None,
                    "htf_tp": None,
                    "planned_rr": None,
                    "deepest_stage": "WAIT_MTF_ALIGNMENT",
                    "deepest_stage_num": 1,
                    "rejection_reason": "PENDING",
                    "bars_alive": 0
                }

        if active_candidate is not None:
            current_candidate_diagnostic["bars_alive"] += 1

            # Candidate evaluation trace
            if active_candidate.state == CandidateState.WAIT_MTF_ALIGNMENT:
                mtf_events = getattr(mtf_state.structure_state, 'events', None) or mtf_state.events or []
                for event in reversed(mtf_events):
                    event_dir = getattr(event, 'direction', None) or (event.metadata.get('direction', '') if hasattr(event, 'metadata') else '')
                    if "CHOCH" in str(event.event_type) and req_dir in str(event_dir):
                        active_candidate.mtf_choch_id = getattr(event, 'broken_swing_id', None) or (event.metadata.get('broken_swing_id', '') if hasattr(event, 'metadata') else '')
                        active_candidate.mtf_alignment_timestamp = getattr(event, 'timestamp', mtf_state.timestamp)
                        active_candidate.transition_to(CandidateState.WAIT_MTF_RETEST)
                        
                        current_candidate_diagnostic["deepest_stage"] = "WAIT_MTF_RETEST"
                        current_candidate_diagnostic["deepest_stage_num"] = 2
                        current_candidate_diagnostic["mtf_choch_ts"] = active_candidate.mtf_alignment_timestamp
                        current_candidate_diagnostic["mtf_choch_ts_str"] = format_ts(active_candidate.mtf_alignment_timestamp)
                        break

            elif active_candidate.state == CandidateState.WAIT_MTF_RETEST:
                # Stage 8: MTF KeyZone causal valid candidates
                causal_zones = []
                for kz in mtf_state.keyzones:
                    kz_type_str = str(getattr(kz, 'zone_type', ''))
                    if is_long and ("BULLISH" not in kz_type_str): continue
                    if (not is_long) and ("BEARISH" not in kz_type_str): continue
                    
                    creation_ts = getattr(kz, 'creation_timestamp', None)
                    if active_candidate.mtf_alignment_timestamp and creation_ts is not None and creation_ts > 0:
                        if creation_ts < active_candidate.mtf_alignment_timestamp:
                            continue
                    causal_zones.append(kz)

                if causal_zones:
                    counts["8_mtf_keyzone_causal_valid"] += len(causal_zones)
                    current_candidate_diagnostic["mtf_kz_creation_ts"] = getattr(causal_zones[0], 'creation_timestamp', None)
                    current_candidate_diagnostic["kz_preceded_shift"] = True

                # Stage 9: MTF KeyZone Retests
                for kz in causal_zones:
                    is_mitigated = "MITIGATED" in str(getattr(kz, 'status', ''))
                    price_in_zone = False
                    high_bound = getattr(kz, 'high_boundary', getattr(kz, 'high', None))
                    low_bound = getattr(kz, 'low_boundary', getattr(kz, 'low', None))
                    if high_bound is not None and low_bound is not None:
                        if mtf_state.current_candle:
                            price_in_zone = (mtf_state.current_candle.low <= high_bound and mtf_state.current_candle.high >= low_bound)
                        else:
                            price_in_zone = (low_bound <= mtf_state.current_price <= high_bound)
                    
                    if is_mitigated or price_in_zone:
                        counts["9_mtf_keyzone_retests"] += 1
                        active_candidate.mtf_keyzone_id = getattr(kz, 'zone_id', '')
                        active_candidate.transition_to(CandidateState.WAIT_LTF_TRIGGER)
                        current_candidate_diagnostic["retest_occurred"] = True
                        current_candidate_diagnostic["deepest_stage"] = "WAIT_LTF_TRIGGER"
                        current_candidate_diagnostic["deepest_stage_num"] = 3
                        break

            elif active_candidate.state == CandidateState.WAIT_LTF_TRIGGER:
                counts["10_ltf_entry_model_candidates"] += 1
                current_candidate_diagnostic["ltf_trigger_state"] = f"Sweeps={len(sweeps)}, Displ={'DISPLACEMENT_CONFIRMED' in reasons}"
                
                if LTFEntryModel.evaluate(ltf_state, req_dir):
                    active_candidate.transition_to(CandidateState.RISK_GATE)
                    current_candidate_diagnostic["deepest_stage"] = "RISK_GATE"
                    current_candidate_diagnostic["deepest_stage_num"] = 4

            elif active_candidate.state == CandidateState.RISK_GATE:
                counts["14_planned_rr_calculations"] += 1
                entry_price = ltf_state.current_price
                current_candidate_diagnostic["entry_price"] = entry_price

                try:
                    if is_long:
                        stop_price = ltf_state.structure_state.protected_low.raw_swing.price
                        target_price = htf_state.structure_state.protected_high.raw_swing.price
                        raw_rr = (target_price - entry_price) / (entry_price - stop_price) if entry_price > stop_price else 0.0
                    else:
                        stop_price = ltf_state.structure_state.protected_high.raw_swing.price
                        target_price = htf_state.structure_state.protected_low.raw_swing.price
                        raw_rr = (entry_price - target_price) / (stop_price - entry_price) if stop_price > entry_price else 0.0

                    current_candidate_diagnostic["structural_sl"] = stop_price
                    current_candidate_diagnostic["htf_tp"] = target_price
                    current_candidate_diagnostic["planned_rr"] = round(raw_rr, 2)

                    if raw_rr < 4.0:
                        counts["15_rejected_by_rr_below_4"] += 1
                        current_candidate_diagnostic["rejection_reason"] = f"REJECT_RR_BELOW_4R (Planned RR: {raw_rr:.2f} < 4.0)"
                        active_candidate.transition_to(CandidateState.REJECTED)
                    else:
                        active_candidate.transition_to(CandidateState.ENTERED)
                        current_candidate_diagnostic["deepest_stage"] = "ENTERED"
                        current_candidate_diagnostic["deepest_stage_num"] = 5
                        
                        # Plan created
                        plan = TradePlanPayload(
                            trade_plan_id=active_candidate.candidate_id,
                            hypothesis_id="HYP_A_PULLBACK_RIDING",
                            symbol=symbol,
                            directional_permission=active_candidate.directional_permission.value,
                            setup_timestamp=ltf_state.timestamp,
                            entry_price=entry_price,
                            stop_invalidation_price=stop_price,
                            target_price=target_price,
                            raw_rr=raw_rr,
                            status=CandidateState.ENTERED.value
                        )

                        # Risk evaluation
                        account_state = AccountState(
                            current_equity=ledger.current_equity,
                            peak_equity=ledger.peak_equity,
                            daily_pnl=0.0,
                            weekly_pnl=0.0,
                            open_position_count=len(ledger.get_active_trades()),
                            active_assets={}
                        )
                        risk_res = RiskCoordinator.evaluate(plan, account_state)
                        if isinstance(risk_res, RiskApprovedPlan):
                            counts["17_risk_approved_plans"] += 1
                            current_candidate_diagnostic["rejection_reason"] = "APPROVED_BY_RISK"
                        else:
                            counts["16_rejected_by_risk_firewall"] += 1
                            current_candidate_diagnostic["rejection_reason"] = f"REJECTED_BY_RISK: {risk_res.reason if hasattr(risk_res, 'reason') else str(risk_res)}"

                except AttributeError as e:
                    current_candidate_diagnostic["rejection_reason"] = f"REJECT_MISSING_STRUCTURAL_ANCHORS: {str(e)}"
                    active_candidate.transition_to(CandidateState.REJECTED)

            # Check for candidate death / timeout or replacement
            # If candidate was rejected or reached dead state, log it and clear active_candidate
            if active_candidate and active_candidate.state in [CandidateState.REJECTED, CandidateState.EXPIRED, CandidateState.ENTERED]:
                all_candidates_log.append(current_candidate_diagnostic)
                active_candidate = None
                current_candidate_diagnostic = None
            elif active_candidate and current_candidate_diagnostic and current_candidate_diagnostic["bars_alive"] > 100:
                # Timeout stale candidate if it stayed alive too long without progression
                current_candidate_diagnostic["rejection_reason"] = f"EXPIRED_IN_STATE_{active_candidate.state.name}"
                all_candidates_log.append(current_candidate_diagnostic)
                active_candidate = None
                current_candidate_diagnostic = None

    if current_candidate_diagnostic is not None:
        all_candidates_log.append(current_candidate_diagnostic)

    # -------------------------------------------------------------
    # PRINT RESULTS
    # -------------------------------------------------------------
    print("\n" + "="*80)
    print("                  FUNNEL DIAGNOSTIC COUNTS (ABSOLUTE & RELATIVE)               ")
    print("="*80)

    funnel_keys = [
        ("1_total_replayed_1h_events", "1. Total Replayed 1H Decision Events"),
        ("2_valid_htf_bias", "2. Valid HTF Directional Bias"),
        ("3_htf_phase_recognized", "3. HTF Phase Recognized (Pullback/Cont)"),
        ("4_htf_keyzone_interaction", "4. HTF KeyZone Interaction"),
        ("5_mtf_structure_alignment", "5. MTF Structure Alignment toward HTF"),
        ("6_mtf_choch_confirmations", "6. MTF CHOCH Confirmations"),
        ("7_mtf_keyzone_candidates", "7. MTF KeyZone Candidates"),
        ("8_mtf_keyzone_causal_valid", "8. MTF KeyZone Causal-Valid Candidates"),
        ("9_mtf_keyzone_retests", "9. MTF KeyZone Retests"),
        ("10_ltf_entry_model_candidates", "10. LTF Entry-Model Candidates (WAIT_LTF)"),
        ("11_ltf_liquidity_sweeps", "11. LTF Liquidity Sweeps"),
        ("12_ltf_displacement_confirmed", "12. LTF Displacement Confirmations"),
        ("13_candidate_setups_created", "13. Candidate Setups Created"),
        ("14_planned_rr_calculations", "14. Planned RR Calculations (RISK_GATE)"),
        ("15_rejected_by_rr_below_4", "15. Candidates Rejected by RR < 4.0"),
        ("16_rejected_by_risk_firewall", "16. Candidates Rejected by Risk Firewall"),
        ("17_risk_approved_plans", "17. Risk-Approved Plans"),
        ("18_executed_trades", "18. Executed Trades")
    ]

    total_events = counts["1_total_replayed_1h_events"]
    prev_count = total_events

    print(f"{'Funnel Stage':<45} | {'Absolute':<10} | {'% Prev Stage':<14} | {'% Total Obs':<14}")
    print("-" * 90)

    for k, label in funnel_keys:
        cnt = counts[k]
        pct_prev = (cnt / prev_count * 100.0) if prev_count > 0 else 0.0
        pct_tot = (cnt / total_events * 100.0) if total_events > 0 else 0.0
        print(f"{label:<45} | {cnt:<10} | {pct_prev:>12.2f}% | {pct_tot:>12.4f}%")
        if cnt > 0:
            prev_count = cnt

    # Rank near misses by depth
    print("\n" + "="*80)
    print("                      TOP 10 DEEPEST NEAR-MISS CANDIDATES                       ")
    print("="*80)

    # Sort candidates by:
    # 1. deepest_stage_num (descending)
    # 2. bars_alive (descending)
    sorted_candidates = sorted(
        all_candidates_log, 
        key=lambda x: (x.get("deepest_stage_num", 0), x.get("planned_rr") or 0.0, x.get("bars_alive", 0)), 
        reverse=True
    )

    top_10 = sorted_candidates[:10]

    for idx, c in enumerate(top_10, 1):
        print(f"\n--- [NEAR-MISS #{idx}] ID: {c['candidate_id']} ---")
        print(f"  • Timestamp:                 {c['timestamp_str']} ({c['timestamp']})")
        print(f"  • Direction:                 {c['direction']}")
        print(f"  • HTF Bias:                  {c['htf_bias']}")
        print(f"  • HTF Phase:                 {c['htf_phase']}")
        print(f"  • HTF KeyZone:               {c['htf_keyzone']}")
        print(f"  • MTF Structure State:       {c['mtf_structure_state']}")
        print(f"  • MTF CHOCH Timestamp:       {c.get('mtf_choch_ts_str', 'NONE')} ({c.get('mtf_choch_ts', 'NONE')})")
        print(f"  • MTF KeyZone Creation TS:   {c.get('mtf_kz_creation_ts', 'NONE')}")
        print(f"  • Zone Preceded Shift:       {c['kz_preceded_shift']}")
        print(f"  • Retest Occurred:           {c['retest_occurred']}")
        print(f"  • LTF Trigger State:         {c['ltf_trigger_state']}")
        print(f"  • Entry Price:               {c['entry_price']}")
        print(f"  • Structural SL:             {c['structural_sl']}")
        print(f"  • HTF TP:                    {c['htf_tp']}")
        print(f"  • Planned RR:                {c['planned_rr']}")
        print(f"  • Deepest Stage Reached:     {c['deepest_stage']} (Stage {c['deepest_stage_num']})")
        print(f"  • Exact Rejection Reason:    {c['rejection_reason']}")

    # Output JSON summary for exact programmatic reporting
    with open("scratch/diagnostic_results.json", "w") as f:
        json.dump({
            "counts": counts,
            "top_10_near_misses": top_10
        }, f, indent=2)

    print("\n✅ Diagnostic run complete. Output saved to scratch/diagnostic_results.json")

if __name__ == "__main__":
    run_diagnostic()
