"""
Product 04 — Research Forensic Validation: Zero-Trade Root-Cause Audit
Performs candidate-level instrumentation, state-transition tracking, LTF trigger decomposition,
anchor forensics, TTL diagnostics, and terminal-state reconciliation.
"""

import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from market_data.warehouse_loader import WarehouseLoader
from market_data.data_certifier import DataCertifier
from market_intelligence.primitives import MarketStatePayload, TrendDirection
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.contracts.trade_plan import DirectionalPermission, TradePlanPayload
from strategy_engine.classifiers.bias_classifier import BiasClassifier
from strategy_engine.context.htf_context_engine import HTFContextEngine, HTFContext
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup, CandidateTracker
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.entry.ltf_entry_model import LTFEntryModel
from research.replayer.timeframe_aligner import TimeframeAligner


def run_forensic_candidate_audit(
    symbol: str = "BTC/USDT",
    timeframe_set_id: str = "SET_1"
) -> Dict[str, Any]:
    tf_set = TimeframeAligner.get_set(timeframe_set_id)
    
    # 1. Load data
    htf_candles = WarehouseLoader.load_history(symbol, tf_set.htf, limit=50000)
    mtf_candles = WarehouseLoader.load_history(symbol, tf_set.mtf, limit=50000)
    ltf_candles = WarehouseLoader.load_history(symbol, tf_set.ltf, limit=50000)
    
    language_coord = LanguageCoordinator(buffer_size=300)
    hypothesis = UnifiedStrategy()
    candidate_tracker = CandidateTracker()
    
    min_lookback_bars = 15
    htf_cache = {"key": None, "state": None}
    mtf_cache = {"key": None, "state": None}
    
    # Forensic records
    all_candidates_spawned: List[Dict[str, Any]] = []
    active_candidate_records: Dict[str, Dict[str, Any]] = {}
    completed_candidate_ledger: List[Dict[str, Any]] = []
    
    funnel = {
        "total_ltf_bars": len(ltf_candles) - min_lookback_bars,
        "htf_contexts_evaluated": 0,
        "candidates_spawned": 0,
        "reached_mtf_alignment": 0,
        "reached_mtf_retest": 0,
        "reached_ltf_trigger_model": 0,
        "ltf_sweep_detected": 0,
        "ltf_displacement_detected": 0,
        "ltf_trigger_complete": 0,
        "reached_risk_gate": 0,
        "anchor_valid": 0,
        "rr_valid": 0,
        "risk_evaluation": 0,
        "trade_plan_entered": 0,
        "orders_submitted": 0,
        "fills": 0
    }
    
    for i in range(min_lookback_bars, len(ltf_candles)):
        current_bar = ltf_candles[i]
        decision_ts = current_bar.timestamp
        
        ltf_slice = ltf_candles[max(0, i - 150):i + 1]
        mtf_slice = TimeframeAligner.filter_visible_candles(mtf_candles, decision_ts, tf_set.mtf, buffer_size=100)
        htf_slice = TimeframeAligner.filter_visible_candles(htf_candles, decision_ts, tf_set.htf, buffer_size=80)
        
        if len(htf_slice) < 5 or len(mtf_slice) < 5 or len(ltf_slice) < 5:
            continue
            
        # P01 Market Intelligence
        htf_key = htf_slice[-1].timestamp if htf_slice else None
        if htf_cache["key"] != htf_key:
            htf_state = language_coord.run(htf_slice, symbol=symbol, timeframe=tf_set.htf)
            htf_cache = {"key": htf_key, "state": htf_state}
        else:
            htf_state = htf_cache["state"]
            
        mtf_key = mtf_slice[-1].timestamp if mtf_slice else None
        if mtf_cache["key"] != mtf_key:
            mtf_state = language_coord.run(mtf_slice, symbol=symbol, timeframe=tf_set.mtf)
            mtf_cache = {"key": mtf_key, "state": mtf_state}
        else:
            mtf_state = mtf_cache["state"]
            
        ltf_state = language_coord.run(ltf_slice, symbol=symbol, timeframe=tf_set.ltf)
        
        # Step 1: Bias & Candidate Spawning
        bias = BiasClassifier.evaluate(htf_state)
        htf_context = HTFContextEngine.evaluate(htf_state)
        
        active = candidate_tracker.get_active_candidates(symbol, "UNIFIED_STRATEGY")
        if bias != DirectionalPermission.NO_TRADE and not active:
            funnel["htf_contexts_evaluated"] += 1
            is_bullish = htf_state.trend_state == TrendDirection.BULLISH
            
            # Spawn candidate
            cid = f"cand_{symbol}_UNIFIED_{decision_ts}"
            cand = CandidateSetup(
                candidate_id=cid,
                hypothesis_id="UNIFIED_STRATEGY",
                symbol=symbol,
                htf=tf_set.htf,
                mtf=tf_set.mtf,
                ltf=tf_set.ltf,
                state=CandidateState.WAIT_MTF_ALIGNMENT,
                directional_permission=DirectionalPermission.PERMIT_LONG if is_bullish else DirectionalPermission.PERMIT_SHORT,
                htf_context_id=htf_context.context_id,
                htf_context_timestamp=htf_context.timestamp,
                htf_macro_direction=htf_state.trend_state.value if hasattr(htf_state.trend_state, "value") else str(htf_state.trend_state),
                htf_phase=str(htf_state.phase_state),
                htf_target_price=htf_context.target_anchor_price,
                creation_timestamp=decision_ts,
                max_lifespan_seconds=60 * 86400  # 60 days on 1W MTF
            )
            candidate_tracker.add_candidate(cand)
            funnel["candidates_spawned"] += 1
            
            active_candidate_records[cid] = {
                "candidate_id": cid,
                "hypothesis_id": "UNIFIED_STRATEGY",
                "symbol": symbol,
                "timeframe_set": tf_set.set_id,
                "direction": cand.directional_permission.value,
                "htf_context_timestamp": cand.htf_context_timestamp,
                "creation_timestamp": cand.creation_timestamp,
                "mtf_alignment_timestamp": None,
                "mtf_keyzone_id": None,
                "mtf_retest_timestamp": None,
                "ltf_activation_timestamp": None,
                "ltf_eval_bars_count": 0,
                "ltf_sweep_detected": False,
                "ltf_displacement_detected": False,
                "ltf_trigger_completed": False,
                "risk_gate_reached": False,
                "terminal_state": None,
                "exact_rejection_reason": None,
                "entry_price": None,
                "stop_price": None,
                "target_price": None,
                "raw_rr": None,
                "protected_low": None,
                "protected_high": None,
                "anchor_details": {}
            }
            
        # Step 2: Evaluate active candidates
        for cand in candidate_tracker.get_active_candidates(symbol, "UNIFIED_STRATEGY"):
            cid = cand.candidate_id
            rec = active_candidate_records.get(cid)
            prev_state = cand.state
            
            if prev_state == CandidateState.WAIT_LTF_TRIGGER:
                rec["ltf_eval_bars_count"] += 1
                
                # Check micro-trigger conditions independently for telemetry
                req_dir = "BULLISH" if cand.directional_permission == DirectionalPermission.PERMIT_LONG else "BEARISH"
                sweeps = [
                    e for e in ltf_state.events 
                    if "LIQUIDITY_SWEEP" in str(e.event_type) and req_dir in str(getattr(e, 'direction', None) or (e.metadata.get('direction', '') if hasattr(e, 'metadata') else ''))
                ]
                if sweeps:
                    rec["ltf_sweep_detected"] = True
                    
                scorecard = ltf_state.scorecard or {}
                reasons = scorecard.get("reason_codes", [])
                if "DISPLACEMENT_CONFIRMED" in reasons:
                    rec["ltf_displacement_detected"] = True
                    
                if sweeps and ("DISPLACEMENT_CONFIRMED" in reasons):
                    rec["ltf_trigger_completed"] = True
            
            plan = hypothesis.evaluate(cand, htf_state, mtf_state, ltf_state)
            
            # Record state transitions
            if prev_state == CandidateState.WAIT_MTF_ALIGNMENT and cand.state != CandidateState.WAIT_MTF_ALIGNMENT:
                rec["mtf_alignment_timestamp"] = cand.mtf_alignment_timestamp
                funnel["reached_mtf_alignment"] += 1
                
            if prev_state == CandidateState.WAIT_MTF_RETEST and cand.state != CandidateState.WAIT_MTF_RETEST:
                rec["mtf_retest_timestamp"] = cand.mtf_retest_timestamp
                rec["mtf_keyzone_id"] = cand.mtf_keyzone_id
                rec["ltf_activation_timestamp"] = cand.mtf_retest_timestamp
                funnel["reached_mtf_retest"] += 1
                funnel["reached_ltf_trigger_model"] += 1
                
            if cand.state == CandidateState.RISK_GATE or (plan and plan.status == CandidateState.ENTERED.value):
                rec["risk_gate_reached"] = True
                funnel["reached_risk_gate"] += 1
                funnel["ltf_trigger_complete"] += 1
                
            if plan:
                candidate_tracker.remove_candidate(cid)
                rec["terminal_state"] = plan.status
                rec["exact_rejection_reason"] = plan.rejection_reason if hasattr(plan, "rejection_reason") else (plan.status if plan.status != CandidateState.ENTERED.value else "APPROVED")
                rec["entry_price"] = plan.entry_price
                rec["stop_price"] = plan.stop_invalidation_price
                rec["target_price"] = plan.target_price
                rec["raw_rr"] = plan.raw_rr
                
                # Anchor telemetry
                p_low = getattr(ltf_state.structure_state, 'protected_low', None)
                p_high = getattr(ltf_state.structure_state, 'protected_high', None)
                rec["protected_low"] = p_low.raw_swing.price if p_low and hasattr(p_low, 'raw_swing') else None
                rec["protected_high"] = p_high.raw_swing.price if p_high and hasattr(p_high, 'raw_swing') else None
                
                rec["anchor_details"] = {
                    "htf_target_price": cand.htf_target_price,
                    "ltf_current_price": ltf_state.current_price,
                    "ltf_protected_low_price": rec["protected_low"],
                    "ltf_protected_high_price": rec["protected_high"],
                    "ltf_external_trend": str(ltf_state.structure_state.external_trend) if ltf_state.structure_state else None,
                    "ltf_swings_count": len(ltf_state.swings)
                }
                
                if plan.status == CandidateState.ENTERED.value:
                    funnel["anchor_valid"] += 1
                    funnel["rr_valid"] += 1
                    funnel["risk_evaluation"] += 1
                    funnel["trade_plan_entered"] += 1
                    funnel["orders_submitted"] += 1
                    funnel["fills"] += 1
                    
                completed_candidate_ledger.append(rec)
                
    # Collect any still active at end of stream
    for cand in candidate_tracker.get_active_candidates(symbol, "UNIFIED_STRATEGY"):
        rec = active_candidate_records.get(cand.candidate_id)
        rec["terminal_state"] = "UNFINALIZED_AT_END_OF_STREAM"
        rec["exact_rejection_reason"] = "STREAM_TERMINATED"
        completed_candidate_ledger.append(rec)
        
    out_data = {
        "symbol": symbol,
        "timeframe_set": timeframe_set_id,
        "funnel": funnel,
        "candidates_ledger": completed_candidate_ledger
    }
    
    import os
    os.makedirs("/home/mrcn2/crypto-platform/scratch", exist_ok=True)
    with open("/home/mrcn2/crypto-platform/scratch/forensic_candidate_ledger.json", "w") as f:
        json.dump(out_data, f, indent=2)
        
    return out_data


if __name__ == "__main__":
    res = run_forensic_candidate_audit()
    print("Forensic audit complete. Total ledger entries:", len(res["candidates_ledger"]))
    print("Funnel:", res["funnel"])
