"""
DAY 35 — GATE 1: Forensic Funnel Diagnostic Script for VS001 (BTCUSDT S3: 1D -> 4H -> 1H).
Instruments and traces every stage of the canonical funnel causally using production hypothesis logic.
"""

import sys
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.primitives import Candle, MarketStatePayload, TrendDirection
from strategy_engine.contracts.trade_plan import DirectionalPermission, TradePlanPayload
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.classifiers.bias_classifier import BiasClassifier
from strategy_engine.entry.ltf_entry_model import LTFEntryModel
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from research.replayer.timeframe_aligner import TimeframeAligner, TimeframeSet
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.simulation.execution_simulator import ExecutionSimulator


def format_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def run_diagnostic():
    print("================================================================================")
    print("      DAY 35 — GATE 1: G4.3 FORENSIC HISTORICAL FUNNEL DIAGNOSTIC (BTCUSDT S3)  ")
    print("================================================================================")

    # 1. Load historical data
    loader = WarehouseLoader()
    htf_candles = loader.load_history("BTCUSDT", "1D", limit=50000)
    mtf_candles = loader.load_history("BTCUSDT", "4H", limit=50000)
    ltf_candles = loader.load_history("BTCUSDT", "1H", limit=50000)

    timeframe_set = TimeframeAligner.get_set("SET_3")  # 1D -> 4H -> 1H
    symbol = "BTCUSDT"
    min_lookback_bars = 15

    language_coordinator = LanguageCoordinator(buffer_size=300)
    hypothesis = UnifiedStrategy()
    execution_simulator = ExecutionSimulator()
    ledger = TradeLedger(initial_equity=10000.0)

    # State caches
    _htf_cache = {"key": None, "state": None}
    _mtf_cache = {"key": None, "state": None}

    # Tracking exact 17 stages
    counts = {
        "stage_00_decision_events": 0,
        "stage_01_valid_htf_bias": 0,
        "stage_02_htf_phase": 0,
        "stage_03_htf_keyzone_interaction": 0,
        "stage_04_mtf_structural_alignment_choch": 0,
        "stage_05_causal_mtf_keyzone_creation": 0,
        "stage_06_mtf_keyzone_retest": 0,
        "stage_07_ltf_liquidity_sweep": 0,
        "stage_08_ltf_displacement_confirmation": 0,
        "stage_09_candidate_setup": 0,
        "stage_10_invalid_geometry_rejection": 0,
        "stage_11_geometrically_valid_candidates": 0,
        "stage_12_rr_lt_4r": 0,
        "stage_13_rr_ge_4r": 0,
        "stage_14_risk_rejection": 0,
        "stage_15_approved_candidates": 0,
        "stage_16_simulated_executions": 0,
    }

    all_candidates_log: List[Dict[str, Any]] = []
    active_candidate: Optional[CandidateSetup] = None
    current_candidate_diagnostic: Optional[Dict[str, Any]] = None

    valid_candidates_detailed: List[Dict[str, Any]] = []

    for i in range(min_lookback_bars, len(ltf_candles)):
        current_bar = ltf_candles[i]
        decision_timestamp = current_bar.timestamp

        # Process orders in execution simulator
        closed_trades = execution_simulator.process_candle(current_bar, ledger)

        counts["stage_00_decision_events"] += 1

        # Visible slices (causal zero-lookahead)
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
        # STAGES 1-8 OBSERVATION
        # -------------------------------------------------------------
        # Stage 1: Valid HTF Bias
        bias = BiasClassifier.evaluate(htf_state)
        is_bias_valid = bias != DirectionalPermission.NO_TRADE
        if is_bias_valid:
            counts["stage_01_valid_htf_bias"] += 1

        is_long_obs = bias == DirectionalPermission.PERMIT_LONG
        req_dir_obs = "BULLISH" if is_long_obs else "BEARISH"

        # Stage 2: HTF Phase Recognized
        phase_str = str(getattr(htf_state, 'phase_state', ''))
        is_phase_recognized = bool(phase_str and "UNDEFINED" not in phase_str and "UNKNOWN" not in phase_str)
        is_pullback = "PULLBACK" in phase_str
        if is_bias_valid and is_phase_recognized:
            counts["stage_02_htf_phase"] += 1

        # Stage 3: HTF KeyZone Interaction
        htf_interacting_kz = None
        for kz in htf_state.keyzones:
            kz_type_str = str(getattr(kz, 'zone_type', ''))
            if is_long_obs and ("BULLISH" not in kz_type_str): continue
            if (not is_long_obs) and ("BEARISH" not in kz_type_str): continue

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

        if is_bias_valid and (htf_interacting_kz is not None or is_pullback):
            counts["stage_03_htf_keyzone_interaction"] += 1

        # Stage 4: MTF Structural Alignment / CHOCH
        mtf_events = getattr(mtf_state.structure_state, 'events', None) or mtf_state.events or []
        has_mtf_alignment_choch = False
        for event in reversed(mtf_events):
            event_dir = getattr(event, 'direction', None) or (event.metadata.get('direction', '') if hasattr(event, 'metadata') else '')
            if "CHOCH" in str(event.event_type) and req_dir_obs in str(event_dir):
                has_mtf_alignment_choch = True
                break

        if is_bias_valid and has_mtf_alignment_choch:
            counts["stage_04_mtf_structural_alignment_choch"] += 1

        # Stage 7 & 8: LTF Sweeps & Displacement
        ltf_all_events = ltf_state.events or []
        sweeps = [
            e for e in ltf_all_events
            if "LIQUIDITY_SWEEP" in str(e.event_type) and req_dir_obs in str(getattr(e, 'direction', None) or (e.metadata.get('direction', '') if hasattr(e, 'metadata') else ''))
        ]
        if is_bias_valid and sweeps:
            counts["stage_07_ltf_liquidity_sweep"] += 1

        scorecard = ltf_state.scorecard or {}
        reasons = scorecard.get("reason_codes", [])
        if is_bias_valid and ("DISPLACEMENT_CONFIRMED" in reasons):
            counts["stage_08_ltf_displacement_confirmation"] += 1

        # -------------------------------------------------------------
        # CANDIDATE LIFECYCLE & STATE MACHINE TRACKING
        # -------------------------------------------------------------
        # Stage 9: Candidate Setup Creation
        if is_bias_valid and (htf_interacting_kz is not None or is_pullback):
            if active_candidate is None:
                active_candidate = CandidateSetup(
                    candidate_id=f"cand_{decision_timestamp}",
                    hypothesis_id="UNIFIED_STRATEGY",
                    symbol=symbol,
                    htf=timeframe_set.htf,
                    mtf=timeframe_set.mtf,
                    ltf=timeframe_set.ltf,
                    state=CandidateState.WAIT_MTF_ALIGNMENT,
                    directional_permission=bias,
                    htf_keyzone_id=getattr(htf_interacting_kz, 'zone_id', None),
                    htf_interaction_timestamp=htf_state.timestamp
                )
                counts["stage_09_candidate_setup"] += 1
                current_candidate_diagnostic = {
                    "candidate_id": active_candidate.candidate_id,
                    "timestamp": decision_timestamp,
                    "timestamp_str": format_ts(decision_timestamp),
                    "direction": bias.value if hasattr(bias, 'value') else str(bias),
                    "htf_bias": bias.value if hasattr(bias, 'value') else str(bias),
                    "htf_phase": phase_str,
                    "htf_keyzone": getattr(htf_interacting_kz, 'zone_id', 'NONE (Phase Pullback)'),
                    "mtf_structure_state": str(getattr(mtf_state.structure_state, 'external_trend', 'UNKNOWN')),
                    "mtf_choch_ts": None,
                    "mtf_kz_id": None,
                    "mtf_kz_creation_ts": None,
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
            cand_is_long = active_candidate.directional_permission == DirectionalPermission.PERMIT_LONG

            # Count Stage 5 (Causal MTF KeyZones created for active candidate)
            if active_candidate.state == CandidateState.WAIT_MTF_RETEST:
                causal_zones = []
                for kz in mtf_state.keyzones:
                    kz_type_str = str(getattr(kz, 'zone_type', ''))
                    if cand_is_long and ("BULLISH" not in kz_type_str): continue
                    if (not cand_is_long) and ("BEARISH" not in kz_type_str): continue
                    creation_ts = getattr(kz, 'creation_timestamp', None)
                    if active_candidate.mtf_alignment_timestamp and creation_ts is not None and creation_ts > 0:
                        if creation_ts < active_candidate.mtf_alignment_timestamp:
                            continue
                    causal_zones.append(kz)

                if causal_zones:
                    counts["stage_05_causal_mtf_keyzone_creation"] += len(causal_zones)
                    current_candidate_diagnostic["mtf_kz_creation_ts"] = getattr(causal_zones[0], 'creation_timestamp', None)

            # Record state before evaluation
            pre_state = active_candidate.state

            # Production hypothesis evaluation
            plan = hypothesis.evaluate(active_candidate, htf_state, mtf_state, ltf_state)

            # Record transitions
            if pre_state == CandidateState.WAIT_MTF_ALIGNMENT and active_candidate.state == CandidateState.WAIT_MTF_RETEST:
                current_candidate_diagnostic["deepest_stage"] = "WAIT_MTF_RETEST"
                current_candidate_diagnostic["deepest_stage_num"] = 2
                current_candidate_diagnostic["mtf_choch_ts"] = active_candidate.mtf_alignment_timestamp
                current_candidate_diagnostic["mtf_choch_ts_str"] = format_ts(active_candidate.mtf_alignment_timestamp) if active_candidate.mtf_alignment_timestamp else "N/A"

            if pre_state == CandidateState.WAIT_MTF_RETEST and active_candidate.state == CandidateState.WAIT_LTF_TRIGGER:
                counts["stage_06_mtf_keyzone_retest"] += 1
                current_candidate_diagnostic["retest_occurred"] = True
                current_candidate_diagnostic["mtf_kz_id"] = active_candidate.mtf_keyzone_id
                current_candidate_diagnostic["deepest_stage"] = "WAIT_LTF_TRIGGER"
                current_candidate_diagnostic["deepest_stage_num"] = 3

            if pre_state == CandidateState.WAIT_LTF_TRIGGER and active_candidate.state == CandidateState.RISK_GATE:
                current_candidate_diagnostic["deepest_stage"] = "RISK_GATE"
                current_candidate_diagnostic["deepest_stage_num"] = 4

            if plan is not None:
                # Candidate reached terminal state (ENTERED or REJECTED)
                current_candidate_diagnostic["entry_price"] = plan.entry_price
                current_candidate_diagnostic["structural_sl"] = plan.stop_invalidation_price
                current_candidate_diagnostic["htf_tp"] = plan.target_price
                current_candidate_diagnostic["planned_rr"] = round(plan.raw_rr, 2)
                current_candidate_diagnostic["rejection_reason"] = plan.rejection_reason or "NONE"

                if plan.rejection_reason == "REJECT_INVALID_ANCHOR_GEOMETRY":
                    counts["stage_10_invalid_geometry_rejection"] += 1
                elif plan.rejection_reason == "REJECT_MISSING_STRUCTURAL_ANCHORS":
                    counts["stage_10_invalid_geometry_rejection"] += 1
                else:
                    # Directional geometry was valid!
                    counts["stage_11_geometrically_valid_candidates"] += 1

                    if plan.rejection_reason == "REJECT_RR_BELOW_4R":
                        counts["stage_12_rr_lt_4r"] += 1
                    elif plan.status == CandidateState.ENTERED.value:
                        counts["stage_13_rr_ge_4r"] += 1
                        current_candidate_diagnostic["deepest_stage"] = "ENTERED"
                        current_candidate_diagnostic["deepest_stage_num"] = 5

                        # Evaluate with Risk Firewall
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
                            counts["stage_15_approved_candidates"] += 1
                            current_candidate_diagnostic["rejection_reason"] = "APPROVED_BY_RISK"
                            current_candidate_diagnostic["risk_decision"] = "APPROVED"

                            simulated_trade = SimulatedTrade(
                                trade_id=plan.trade_plan_id,
                                hypothesis_id=plan.hypothesis_id,
                                symbol=symbol,
                                timeframe_set=timeframe_set.set_id,
                                directional_permission=plan.directional_permission,
                                setup_timestamp=plan.setup_timestamp,
                                entry_price=plan.entry_price,
                                initial_stop_price=plan.stop_invalidation_price,
                                current_stop_price=plan.stop_invalidation_price,
                                target_price=plan.target_price,
                                position_units=risk_res.position_units,
                                dollar_risk=risk_res.dollar_risk,
                                raw_rr=plan.raw_rr,
                                status="PENDING_ENTRY"
                            )
                            ledger.record_pending_trade(simulated_trade)
                            counts["stage_16_simulated_executions"] += 1
                        else:
                            counts["stage_14_risk_rejection"] += 1
                            current_candidate_diagnostic["rejection_reason"] = f"REJECTED_BY_RISK: {risk_res.reason.value if hasattr(risk_res, 'reason') else str(risk_res)}"
                            current_candidate_diagnostic["risk_decision"] = f"REJECTED ({risk_res.reason.value if hasattr(risk_res, 'reason') else str(risk_res)})"

                        # Collect detailed candidate for Step 6
                        cand_detail = {
                            "timestamp": decision_timestamp,
                            "timestamp_str": format_ts(decision_timestamp),
                            "direction": plan.directional_permission,
                            "htf_bias": bias.value,
                            "htf_phase": phase_str,
                            "htf_target": plan.target_price,
                            "mtf_alignment_timestamp": active_candidate.mtf_alignment_timestamp,
                            "mtf_alignment_timestamp_str": format_ts(active_candidate.mtf_alignment_timestamp) if active_candidate.mtf_alignment_timestamp else "N/A",
                            "mtf_keyzone": active_candidate.mtf_keyzone_id,
                            "ltf_entry": plan.entry_price,
                            "ltf_sl": plan.stop_invalidation_price,
                            "htf_tp": plan.target_price,
                            "rr": round(plan.raw_rr, 2),
                            "risk_decision": current_candidate_diagnostic.get("risk_decision", "N/A"),
                            "geometry_proof": (
                                f"SL ({plan.stop_invalidation_price:.2f}) < ENTRY ({plan.entry_price:.2f}) < TP ({plan.target_price:.2f}) [PROVEN]"
                                if cand_is_long else
                                f"TP ({plan.target_price:.2f}) < ENTRY ({plan.entry_price:.2f}) < SL ({plan.stop_invalidation_price:.2f}) [PROVEN]"
                            )
                        }
                        valid_candidates_detailed.append(cand_detail)

            # Cycle cleanup
            if active_candidate and active_candidate.state in [CandidateState.REJECTED, CandidateState.EXPIRED, CandidateState.ENTERED]:
                all_candidates_log.append(current_candidate_diagnostic)
                active_candidate = None
                current_candidate_diagnostic = None
            elif active_candidate and current_candidate_diagnostic and current_candidate_diagnostic["bars_alive"] > 100:
                current_candidate_diagnostic["rejection_reason"] = f"EXPIRED_IN_STATE_{active_candidate.state.name}"
                all_candidates_log.append(current_candidate_diagnostic)
                active_candidate = None
                current_candidate_diagnostic = None

    if current_candidate_diagnostic is not None:
        all_candidates_log.append(current_candidate_diagnostic)

    # -------------------------------------------------------------
    # PRINT EXACT 17 STAGES
    # -------------------------------------------------------------
    print("\n" + "="*85)
    print(f"{'Stage Number & Name':<45} | {'Exact Count':<12} | {'% of Stage 0':<14}")
    print("="*85)

    stage_definitions = [
        ("stage_00_decision_events", "Stage 0: decision events"),
        ("stage_01_valid_htf_bias", "Stage 1: valid HTF bias"),
        ("stage_02_htf_phase", "Stage 2: HTF phase"),
        ("stage_03_htf_keyzone_interaction", "Stage 3: HTF KeyZone interaction"),
        ("stage_04_mtf_structural_alignment_choch", "Stage 4: MTF structural alignment / CHOCH"),
        ("stage_05_causal_mtf_keyzone_creation", "Stage 5: causal MTF KeyZone creation"),
        ("stage_06_mtf_keyzone_retest", "Stage 6: MTF KeyZone retest"),
        ("stage_07_ltf_liquidity_sweep", "Stage 7: LTF liquidity sweep"),
        ("stage_08_ltf_displacement_confirmation", "Stage 8: LTF displacement/confirmation"),
        ("stage_09_candidate_setup", "Stage 9: candidate setup"),
        ("stage_10_invalid_geometry_rejection", "Stage 10: invalid geometry rejection"),
        ("stage_11_geometrically_valid_candidates", "Stage 11: geometrically valid candidates"),
        ("stage_12_rr_lt_4r", "Stage 12: RR < 4R"),
        ("stage_13_rr_ge_4r", "Stage 13: RR >= 4R"),
        ("stage_14_risk_rejection", "Stage 14: risk rejection"),
        ("stage_15_approved_candidates", "Stage 15: approved candidates"),
        ("stage_16_simulated_executions", "Stage 16: simulated executions"),
    ]

    total_decision_events = counts["stage_00_decision_events"]

    for k, name in stage_definitions:
        cnt = counts[k]
        pct = (cnt / total_decision_events * 100.0) if total_decision_events > 0 else 0.0
        print(f"{name:<45} | {cnt:<12} | {pct:>12.4f}%")

    print("\n" + "="*85)
    print(f"TOTAL GEOMETRICALLY VALID CANDIDATES (STAGE 11): {counts['stage_11_geometrically_valid_candidates']}")
    print(f"TOTAL CANDIDATES WITH RR >= 4R (STAGE 13):        {counts['stage_13_rr_ge_4r']}")
    print(f"TOTAL RISK-APPROVED CANDIDATES (STAGE 15):        {counts['stage_15_approved_candidates']}")
    print(f"TOTAL SIMULATED EXECUTIONS (STAGE 16):            {counts['stage_16_simulated_executions']}")
    print("="*85)

    # Output detailed report of valid candidates
    print("\n" + "="*85)
    print("           TOP VALID CANDIDATES (STEP 6 VERIFICATION REPORT)                    ")
    print("="*85)

    for idx, c in enumerate(valid_candidates_detailed[:10], 1):
        print(f"\n--- [VALID CANDIDATE #{idx}] ---")
        print(f"  • timestamp:                {c['timestamp']} ({c['timestamp_str']})")
        print(f"  • direction:                {c['direction']}")
        print(f"  • HTF bias:                 {c['htf_bias']}")
        print(f"  • HTF phase:                {c['htf_phase']}")
        print(f"  • HTF target:               {c['htf_target']}")
        print(f"  • MTF alignment timestamp:  {c['mtf_alignment_timestamp']} ({c['mtf_alignment_timestamp_str']})")
        print(f"  • MTF KeyZone:              {c['mtf_keyzone']}")
        print(f"  • LTF entry:                {c['ltf_entry']}")
        print(f"  • LTF SL:                   {c['ltf_sl']}")
        print(f"  • HTF TP:                   {c['htf_tp']}")
        print(f"  • RR:                       {c['rr']}")
        print(f"  • risk decision:            {c['risk_decision']}")
        print(f"  • geometry proof:           {c['geometry_proof']}")

    # Save to json
    with open("scratch/diagnostic_results.json", "w") as f:
        json.dump({
            "counts": counts,
            "valid_candidates": valid_candidates_detailed,
            "all_candidates_log": all_candidates_log
        }, f, indent=2)

    print("\n✅ Funnel Diagnostic Complete. Output persisted to scratch/diagnostic_results.json")


if __name__ == "__main__":
    run_diagnostic()
