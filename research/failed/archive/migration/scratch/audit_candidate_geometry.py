"""
Comprehensive forensic script for G4.2 Trade Geometry and Anchor Audit.
Audits all candidate TradePlans, anchor semantics, directional geometry, 
telemetry semantics, and execution fills across the historical dataset.
"""

import sys
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.primitives import (
    Candle, MarketStatePayload, SwingType, SequenceLabel
)
from strategy_engine.contracts.trade_plan import DirectionalPermission, TradePlanPayload
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.classifiers.bias_classifier import BiasClassifier
from strategy_engine.entry.ltf_entry_model import LTFEntryModel
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.hypotheses.pullback_riding import PullbackRidingHypothesis
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from research.replayer.timeframe_aligner import TimeframeAligner
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.simulation.execution_simulator import ExecutionSimulator

def format_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

def main():
    loader = WarehouseLoader()
    htf_candles = loader.load_history("BTCUSDT", "1D", limit=50000)
    mtf_candles = loader.load_history("BTCUSDT", "4H", limit=50000)
    ltf_candles = loader.load_history("BTCUSDT", "1H", limit=50000)

    timeframe_set = TimeframeAligner.get_set("SET_3")
    symbol = "BTCUSDT"
    min_lookback_bars = 15

    language_coordinator = LanguageCoordinator(buffer_size=300)
    execution_simulator = ExecutionSimulator()
    ledger = TradeLedger(initial_equity=10000.0)

    _htf_cache = {"key": None, "state": None}
    _mtf_cache = {"key": None, "state": None}

    # Tracking candidates reaching RISK_GATE
    total_candidates_reached_risk_gate = 0
    geometrically_valid_candidates = 0
    geometrically_invalid_candidates = 0
    valid_rr_ge_4 = 0
    valid_rr_lt_4 = 0

    all_risk_gate_evaluations: List[Dict[str, Any]] = []
    risk_approved_plans: List[Dict[str, Any]] = []

    active_candidate: Optional[CandidateSetup] = None
    current_candidate_diagnostic: Optional[Dict[str, Any]] = None

    for i in range(min_lookback_bars, len(ltf_candles)):
        current_bar = ltf_candles[i]
        decision_timestamp = current_bar.timestamp

        # Check pending limit fills in execution simulator
        closed_this_bar = execution_simulator.process_candle(current_bar, ledger)

        ltf_slice = ltf_candles[max(0, i - 150):i + 1]
        mtf_slice = TimeframeAligner.filter_visible_candles(mtf_candles, decision_timestamp, timeframe_set.mtf, buffer_size=100)
        htf_slice = TimeframeAligner.filter_visible_candles(htf_candles, decision_timestamp, timeframe_set.htf, buffer_size=80)

        if len(htf_slice) < 5 or len(mtf_slice) < 5 or len(ltf_slice) < 5:
            continue

        htf_key = htf_slice[-1].timestamp if htf_slice else None
        if _htf_cache["key"] != htf_key:
            htf_state = language_coordinator.run(htf_slice, symbol=symbol, timeframe=timeframe_set.htf)
            _htf_cache = {"key": htf_key, "state": htf_state}
        else:
            htf_state = _htf_cache["state"]

        mtf_key = mtf_slice[-1].timestamp if mtf_slice else None
        if _mtf_cache["key"] != mtf_key:
            mtf_state = language_coordinator.run(mtf_slice, symbol=symbol, timeframe=timeframe_set.mtf)
            _mtf_cache = {"key": mtf_key, "state": mtf_state}
        else:
            mtf_state = _mtf_cache["state"]

        ltf_state = language_coordinator.run(ltf_slice, symbol=symbol, timeframe=timeframe_set.ltf)

        bias = BiasClassifier.evaluate(htf_state)
        is_bias_valid = bias != DirectionalPermission.NO_TRADE
        is_long = bias == DirectionalPermission.PERMIT_LONG
        req_dir = "BULLISH" if is_long else "BEARISH"
        phase_str = str(getattr(htf_state, 'phase_state', ''))
        is_pullback = "PULLBACK" in phase_str

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

        # Spawn Candidate
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
                current_candidate_diagnostic = {
                    "candidate_id": active_candidate.candidate_id,
                    "timestamp": decision_timestamp,
                    "timestamp_str": format_ts(decision_timestamp),
                    "direction": bias.value,
                    "htf_bias": bias.value,
                    "htf_phase": phase_str,
                    "htf_keyzone": getattr(htf_interacting_kz, 'zone_id', 'NONE (Pullback Phase)'),
                    "mtf_structure_state": str(getattr(mtf_state.structure_state, 'external_trend', 'UNKNOWN')),
                    "mtf_choch_ts": None,
                    "mtf_kz_id": None,
                    "mtf_kz_creation_ts": None,
                    "bars_alive": 0
                }

        if active_candidate is not None:
            current_candidate_diagnostic["bars_alive"] += 1

            if active_candidate.state == CandidateState.WAIT_MTF_ALIGNMENT:
                mtf_events = getattr(mtf_state.structure_state, 'events', None) or mtf_state.events or []
                for event in reversed(mtf_events):
                    event_dir = getattr(event, 'direction', None) or (event.metadata.get('direction', '') if hasattr(event, 'metadata') else '')
                    if "CHOCH" in str(event.event_type) and req_dir in str(event_dir):
                        active_candidate.mtf_choch_id = getattr(event, 'broken_swing_id', None) or (event.metadata.get('broken_swing_id', '') if hasattr(event, 'metadata') else '')
                        active_candidate.mtf_alignment_timestamp = getattr(event, 'timestamp', mtf_state.timestamp)
                        active_candidate.transition_to(CandidateState.WAIT_MTF_RETEST)
                        current_candidate_diagnostic["mtf_choch_ts"] = active_candidate.mtf_alignment_timestamp
                        current_candidate_diagnostic["mtf_choch_ts_str"] = format_ts(active_candidate.mtf_alignment_timestamp)
                        break

            elif active_candidate.state == CandidateState.WAIT_MTF_RETEST:
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
                        active_candidate.mtf_keyzone_id = getattr(kz, 'zone_id', '')
                        active_candidate.transition_to(CandidateState.WAIT_LTF_TRIGGER)
                        current_candidate_diagnostic["mtf_kz_id"] = active_candidate.mtf_keyzone_id
                        current_candidate_diagnostic["mtf_kz_creation_ts"] = getattr(kz, 'creation_timestamp', None)
                        break

            elif active_candidate.state == CandidateState.WAIT_LTF_TRIGGER:
                if LTFEntryModel.evaluate(ltf_state, req_dir):
                    active_candidate.transition_to(CandidateState.RISK_GATE)

            elif active_candidate.state == CandidateState.RISK_GATE:
                total_candidates_reached_risk_gate += 1
                entry_price = ltf_state.current_price
                direction = active_candidate.directional_permission.value
                is_long_trade = direction == "PERMIT_LONG"

                # Extract LTF and HTF structural objects
                ltf_prot_low = getattr(ltf_state.structure_state, 'protected_low', None)
                ltf_prot_high = getattr(ltf_state.structure_state, 'protected_high', None)
                ltf_weak_low = getattr(ltf_state.structure_state, 'weak_low', None)
                ltf_weak_high = getattr(ltf_state.structure_state, 'weak_high', None)

                htf_prot_low = getattr(htf_state.structure_state, 'protected_low', None)
                htf_prot_high = getattr(htf_state.structure_state, 'protected_high', None)
                htf_weak_low = getattr(htf_state.structure_state, 'weak_low', None)
                htf_weak_high = getattr(htf_state.structure_state, 'weak_high', None)

                # Exactly what current code uses:
                curr_sl = None
                curr_tp = None
                curr_sl_src = ""
                curr_tp_src = ""

                try:
                    if is_long_trade:
                        curr_sl = ltf_prot_low.raw_swing.price if ltf_prot_low and ltf_prot_low.raw_swing else None
                        curr_sl_src = f"ltf.structure_state.protected_low (id={ltf_prot_low.raw_swing.swing_id if ltf_prot_low else 'None'})"
                        curr_tp = htf_prot_high.raw_swing.price if htf_prot_high and htf_prot_high.raw_swing else None
                        curr_tp_src = f"htf.structure_state.protected_high (id={htf_prot_high.raw_swing.swing_id if htf_prot_high else 'None'})"
                    else:
                        curr_sl = ltf_prot_high.raw_swing.price if ltf_prot_high and ltf_prot_high.raw_swing else None
                        curr_sl_src = f"ltf.structure_state.protected_high (id={ltf_prot_high.raw_swing.swing_id if ltf_prot_high else 'None'})"
                        curr_tp = htf_prot_low.raw_swing.price if htf_prot_low and htf_prot_low.raw_swing else None
                        curr_tp_src = f"htf.structure_state.protected_low (id={htf_prot_low.raw_swing.swing_id if htf_prot_low else 'None'})"
                except Exception as ex:
                    pass

                # Directional Geometry Check
                # LONG: SL < Entry < TP
                # SHORT: TP < Entry < SL
                is_geom_valid = False
                genuine_rr = None
                geom_status = "INVALID_GEOMETRY"

                if curr_sl is not None and curr_tp is not None:
                    if is_long_trade:
                        if curr_sl < entry_price < curr_tp:
                            is_geom_valid = True
                            genuine_rr = (curr_tp - entry_price) / (entry_price - curr_sl)
                            geom_status = "VALID_GEOMETRY"
                        else:
                            geom_status = f"INVALID_GEOMETRY (Expected SL < Entry < TP, Got SL={curr_sl:.2f}, Entry={entry_price:.2f}, TP={curr_tp:.2f})"
                    else:
                        if curr_tp < entry_price < curr_sl:
                            is_geom_valid = True
                            genuine_rr = (entry_price - curr_tp) / (curr_sl - entry_price)
                            geom_status = "VALID_GEOMETRY"
                        else:
                            geom_status = f"INVALID_GEOMETRY (Expected TP < Entry < SL, Got TP={curr_tp:.2f}, Entry={entry_price:.2f}, SL={curr_sl:.2f})"
                else:
                    geom_status = f"INVALID_GEOMETRY (Missing Anchors: SL={curr_sl}, TP={curr_tp})"

                if is_geom_valid:
                    geometrically_valid_candidates += 1
                    if genuine_rr >= 4.0:
                        valid_rr_ge_4 += 1
                    else:
                        valid_rr_lt_4 += 1
                else:
                    geometrically_invalid_candidates += 1

                # Legacy raw_rr calculation (what code currently does):
                legacy_rr = None
                try:
                    if is_long_trade:
                        legacy_rr = (curr_tp - entry_price) / (entry_price - curr_sl) if entry_price > curr_sl else 0.0
                    else:
                        legacy_rr = (entry_price - curr_tp) / (curr_sl - entry_price) if curr_sl > entry_price else 0.0
                except Exception:
                    pass

                eval_record = {
                    "candidate_id": active_candidate.candidate_id,
                    "timestamp": decision_timestamp,
                    "timestamp_str": format_ts(decision_timestamp),
                    "candle_index": i,
                    "direction": direction,
                    "entry_price": entry_price,
                    "curr_sl": curr_sl,
                    "curr_tp": curr_tp,
                    "curr_sl_src": curr_sl_src,
                    "curr_tp_src": curr_tp_src,
                    "is_geom_valid": is_geom_valid,
                    "geom_status": geom_status,
                    "genuine_rr": round(genuine_rr, 2) if genuine_rr is not None else None,
                    "legacy_rr": round(legacy_rr, 2) if legacy_rr is not None else None,
                    "htf_bias": bias.value,
                    "htf_phase": phase_str,
                    "htf_kz": current_candidate_diagnostic["htf_keyzone"],
                    "mtf_choch_ts": current_candidate_diagnostic["mtf_choch_ts"],
                    "mtf_kz_id": current_candidate_diagnostic["mtf_kz_id"],
                    "ltf_sweeps_count": len([e for e in ltf_state.events or [] if "LIQUIDITY_SWEEP" in str(e.event_type)]),
                    "ltf_displacement": "DISPLACEMENT_CONFIRMED" in (ltf_state.scorecard or {}).get("reason_codes", []),
                    "ltf_prot_low": ltf_prot_low.raw_swing.price if ltf_prot_low and ltf_prot_low.raw_swing else None,
                    "ltf_prot_high": ltf_prot_high.raw_swing.price if ltf_prot_high and ltf_prot_high.raw_swing else None,
                    "ltf_weak_low": ltf_weak_low.raw_swing.price if ltf_weak_low and ltf_weak_low.raw_swing else None,
                    "ltf_weak_high": ltf_weak_high.raw_swing.price if ltf_weak_high and ltf_weak_high.raw_swing else None,
                    "htf_prot_low": htf_prot_low.raw_swing.price if htf_prot_low and htf_prot_low.raw_swing else None,
                    "htf_prot_high": htf_prot_high.raw_swing.price if htf_prot_high and htf_prot_high.raw_swing else None,
                    "htf_weak_low": htf_weak_low.raw_swing.price if htf_weak_low and htf_weak_low.raw_swing else None,
                    "htf_weak_high": htf_weak_high.raw_swing.price if htf_weak_high and htf_weak_high.raw_swing else None,
                }
                all_risk_gate_evaluations.append(eval_record)

                # If legacy logic passed to ENTERED
                if legacy_rr is not None and legacy_rr >= 4.0:
                    plan = TradePlanPayload(
                        trade_plan_id=active_candidate.candidate_id,
                        hypothesis_id="HYP_A_PULLBACK_RIDING",
                        symbol=symbol,
                        directional_permission=active_candidate.directional_permission.value,
                        setup_timestamp=ltf_state.timestamp,
                        entry_price=entry_price,
                        stop_invalidation_price=curr_sl,
                        target_price=curr_tp,
                        raw_rr=legacy_rr,
                        status=CandidateState.ENTERED.value
                    )
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
                        # Register trade plan in trade ledger for execution tracking
                        sim_trade = SimulatedTrade(
                            trade_id=plan.trade_plan_id,
                            hypothesis_id=plan.hypothesis_id,
                            symbol=symbol,
                            timeframe_set=timeframe_set.set_id,
                            directional_permission=plan.directional_permission,
                            setup_timestamp=plan.setup_timestamp,
                            entry_price=plan.entry_price,
                            stop_invalidation_price=plan.stop_invalidation_price,
                            target_price=plan.target_price,
                            planned_rr=plan.raw_rr,
                            position_size_usd=risk_res.position_size_usd,
                            position_size_units=risk_res.position_size_units,
                            risk_amount_usd=risk_res.risk_amount_usd
                        )
                        ledger.record_entry_order(sim_trade)

                        # Check subsequent bars to see if entry was touched
                        future_bars = ltf_candles[i+1:min(len(ltf_candles), i+100)]
                        entry_touched = False
                        touch_idx = None
                        touch_bar_str = None
                        for fb_idx, fb in enumerate(future_bars):
                            if is_long_trade:
                                if fb.low <= entry_price:
                                    entry_touched = True
                                    touch_idx = fb_idx + 1
                                    touch_bar_str = format_ts(fb.timestamp)
                                    break
                            else:
                                if fb.high >= entry_price:
                                    entry_touched = True
                                    touch_idx = fb_idx + 1
                                    touch_bar_str = format_ts(fb.timestamp)
                                    break

                        approved_record = {
                            **eval_record,
                            "position_size_usd": risk_res.position_size_usd,
                            "position_size_units": risk_res.position_size_units,
                            "risk_amount_usd": risk_res.risk_amount_usd,
                            "entry_touched_in_next_100_bars": entry_touched,
                            "touch_bar_offset": touch_idx,
                            "touch_bar_timestamp": touch_bar_str,
                            "order_type": "LIMIT_ORDER (Pending at entry_price)"
                        }
                        risk_approved_plans.append(approved_record)

                active_candidate.transition_to(CandidateState.EXPIRED)
                active_candidate = None
                current_candidate_diagnostic = None

            if active_candidate and current_candidate_diagnostic and current_candidate_diagnostic["bars_alive"] > 100:
                active_candidate = None
                current_candidate_diagnostic = None

    # Print Full Audit Summary
    print("\n" + "="*80)
    print("                 1. TRADE GEOMETRY VALIDATION AUDIT                             ")
    print("="*80)
    print(f"Total Candidates Reaching RISK_GATE:       {total_candidates_reached_risk_gate}")
    print(f"Geometrically Valid Candidates:             {geometrically_valid_candidates} ({(geometrically_valid_candidates/total_candidates_reached_risk_gate*100.0) if total_candidates_reached_risk_gate else 0:.2f}%)")
    print(f"Geometrically Invalid Candidates:           {geometrically_invalid_candidates} ({(geometrically_invalid_candidates/total_candidates_reached_risk_gate*100.0) if total_candidates_reached_risk_gate else 0:.2f}%)")
    print(f"  • Valid Candidates with Genuine RR >= 4.0: {valid_rr_ge_4}")
    print(f"  • Valid Candidates with Genuine RR < 4.0:  {valid_rr_lt_4}")

    print("\n" + "="*80)
    print("                 2. AUDIT OF THE 7 RISK-APPROVED PLANS                         ")
    print("="*80)
    for idx, p in enumerate(risk_approved_plans, 1):
        print(f"\n--- [RISK APPROVED PLAN #{idx}] ID: {p['candidate_id']} ---")
        print(f"  • Timestamp:          {p['timestamp_str']}")
        print(f"  • Direction:          {p['direction']}")
        print(f"  • Entry Price:        ${p['entry_price']:,.2f}")
        print(f"  • Selected SL:        ${p['curr_sl'] if p['curr_sl'] is not None else 0:,.2f} | Source: {p['curr_sl_src']}")
        print(f"  • Selected TP:        ${p['curr_tp'] if p['curr_tp'] is not None else 0:,.2f} | Source: {p['curr_tp_src']}")
        print(f"  • Geometry Status:    {p['geom_status']}")
        print(f"  • Legacy Math RR:     {p['legacy_rr']}")
        print(f"  • Genuine Strict RR:  {p['genuine_rr']}")
        print(f"  • LTF Prot Low / High: Low={p['ltf_prot_low']}, High={p['ltf_prot_high']}")
        print(f"  • HTF Prot Low / High: Low={p['htf_prot_low']}, High={p['htf_prot_high']}")
        print(f"  • HTF Weak Low / High: Low={p['htf_weak_low']}, High={p['htf_weak_high']}")
        print(f"  • Order Type:         {p['order_type']}")
        print(f"  • Entry Touched Next: {p['entry_touched_in_next_100_bars']} (at bar offset +{p['touch_bar_offset']}, {p['touch_bar_timestamp']})")

    # Sample of Rejected Candidates
    print("\n" + "="*80)
    print("                 3. SAMPLE OF REJECTED CANDIDATES AT RISK GATE                 ")
    print("="*80)
    sample_rejected = [r for r in all_risk_gate_evaluations if not r['is_geom_valid']][:5]
    for idx, r in enumerate(sample_rejected, 1):
        print(f"\n--- [REJECTED CANDIDATE #{idx}] ID: {r['candidate_id']} ---")
        print(f"  • Timestamp:          {r['timestamp_str']}")
        print(f"  • Direction:          {r['direction']}")
        print(f"  • Entry Price:        ${r['entry_price']:,.2f}")
        print(f"  • Selected SL:        {r['curr_sl']} | Source: {r['curr_sl_src']}")
        print(f"  • Selected TP:        {r['curr_tp']} | Source: {r['curr_tp_src']}")
        print(f"  • Geometry Status:    {r['geom_status']}")
        print(f"  • LTF Prot Low/High:  Low={r['ltf_prot_low']}, High={r['ltf_prot_high']}")
        print(f"  • HTF Prot Low/High:  Low={r['htf_prot_low']}, High={r['htf_prot_high']}")
        print(f"  • HTF Weak Low/High:  Low={r['htf_weak_low']}, High={r['htf_weak_high']}")

    with open("scratch/geometry_audit_results.json", "w") as f:
        json.dump({
            "total_candidates": total_candidates_reached_risk_gate,
            "geometrically_valid": geometrically_valid_candidates,
            "geometrically_invalid": geometrically_invalid_candidates,
            "valid_rr_ge_4": valid_rr_ge_4,
            "valid_rr_lt_4": valid_rr_lt_4,
            "risk_approved_plans": risk_approved_plans,
            "sample_rejected": sample_rejected
        }, f, indent=2)

if __name__ == "__main__":
    main()
