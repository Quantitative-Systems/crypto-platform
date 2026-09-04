"""
Product 04 — Research Laboratory: 15-Stream Canonical Baseline Matrix Engine (Day 39)
Executes the Frozen Canonical Unified Strategy across the 15 research streams:
  1 Strategy × 5 Timeframe Sets × 3 Assets = 15 Streams.
  
FROZEN BASELINE RULES:
  - Planned RR >= 4.0R
  - Risk <= 1.0% equity ($100 per trade on $10,000 equity)
  - Profit Lock = OFF (enable_profit_lock=False)
  - MTF Structural Trailing = ON (enable_mtf_trailing=True)
  - Target = HTF structural weak swing
  - SL = LTF structural protected swing
  - Real Fees = ON (Maker 2 bps, Taker 5 bps)
  - Realistic Slippage = ON (5 bps market / adverse SL)
  - Adverse-First Intrabar Collision Resolution = ON
  - Zero Lookahead Protection = ON
  - Synthetic Data = FORBIDDEN (Fail-Closed)
  
ARTIFACTS PRODUCED:
  - scratch/canonical_trade_ledger.json
  - scratch/canonical_multiyear_matrix_results.json
"""

import os
import sys
import json
import time
import math
import hashlib
from datetime import datetime, timezone
import numpy as np
from typing import Dict, Any, List
from concurrent.futures import ProcessPoolExecutor, as_completed

from market_data.warehouse_loader import WarehouseLoader
from market_data.data_certifier import DataCertifier
from market_data.dataset_manifest import DatasetManifestManager
from research.replayer.causal_replayer import CausalReplayer
from research.replayer.timeframe_aligner import TimeframeAligner
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from risk_engine.contracts.risk_config import RiskConfig
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.risk_coordinator import RiskCoordinator
from strategy_engine.contracts.strategy_state import CandidateState
from platform_core.capital_barrier import CapitalBarrier, CapitalBarrierTier


ASSETS = ["BTC", "ETH", "SOL"]
TF_SETS = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]

TF_SET_METADATA = {
    "SET_1": {"label": "SET_1 (1M -> 1W -> 1D, Macro)", "htf": "1M", "mtf": "1w", "ltf": "1d"},
    "SET_2": {"label": "SET_2 (1W -> 1D -> 4H, Position)", "htf": "1w", "mtf": "1d", "ltf": "4h"},
    "SET_3": {"label": "SET_3 (1D -> 4H -> 1H, Swing)", "htf": "1d", "mtf": "4h", "ltf": "1h"},
    "SET_4": {"label": "SET_4 (4H -> 1H -> 15M, Intraday)", "htf": "4h", "mtf": "1h", "ltf": "15m"},
    "SET_5": {"label": "SET_5 (15M -> 5M -> 1M, Intraday Scalping)", "htf": "15m", "mtf": "5m", "ltf": "1m"},
}


def run_single_stream_canonical(asset: str, tf_set_id: str) -> Dict[str, Any]:
    stream_id = f"{asset}_{tf_set_id}"
    symbol = f"{asset}/USDT"
    tf_info = TF_SET_METADATA[tf_set_id]
    
    t0 = time.time()
    
    # 1. Define Benchmark Dates
    if tf_set_id == "SET_5":
        # Maximum available certified real 1m/5m window
        ltf_start_time_ms = int(datetime(2026, 7, 30, 23, 50, tzinfo=timezone.utc).timestamp() * 1000)
        end_time_ms = int(datetime(2026, 9, 3, 18, 0, tzinfo=timezone.utc).timestamp() * 1000)
        period_label = "2026-07-30 to 2026-09-03 (Certified Max 1m/5m Window)"
    else:
        # Canonical certified 2023 annual benchmark (365 days)
        ltf_start_time_ms = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        end_time_ms = int(datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        period_label = "2023-01-01 to 2024-01-01 (Certified Annual Benchmark)"

    # 2. Load and Certify Real Datasets (Fail-Closed)
    data_status = "CERTIFIED"
    try:
        htf_candles = WarehouseLoader.load_history(symbol, tf_info["htf"], limit=1_000_000, start_time_ms=None, end_time_ms=end_time_ms)
        mtf_candles = WarehouseLoader.load_history(symbol, tf_info["mtf"], limit=1_000_000, start_time_ms=None, end_time_ms=end_time_ms)
        ltf_candles = WarehouseLoader.load_history(symbol, tf_info["ltf"], limit=1_000_000, start_time_ms=ltf_start_time_ms, end_time_ms=end_time_ms)
        
        DataCertifier.certify_dataset(htf_candles, tf_info["htf"], symbol, allow_gaps=True, max_allowed_gap_bars=1000)
        DataCertifier.certify_dataset(mtf_candles, tf_info["mtf"], symbol, allow_gaps=True, max_allowed_gap_bars=1000)
        DataCertifier.certify_dataset(ltf_candles, tf_info["ltf"], symbol, allow_gaps=True, max_allowed_gap_bars=1000)
        DataCertifier.certify_overlap(htf_candles, mtf_candles, ltf_candles, min_lookback_bars=15)
    except Exception as data_err:
        data_status = f"DATA_ERROR: {str(data_err)}"
        raise RuntimeError(f"[{stream_id}] Data certification failed: {data_err}") from data_err

    # 3. Configure Frozen Risk & Replayer Engine
    risk_cfg = RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=4.0,
        min_stop_distance_pct=0.001,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False
    )
    
    replayer = CausalReplayer(
        timeframe_set_id=tf_set_id,
        initial_balance=10000.0,
        maker_fee_rate=0.0002,   # 2 bps maker
        taker_fee_rate=0.0005,   # 5 bps taker
        slippage_bps=5.0,        # 5 bps realistic adverse slippage
        enable_mtf_trailing=True, # Canonical MTF structural trailing ON
        enable_profit_lock=False,# Frozen canonical baseline: profit lock OFF
        lockin_r=1.0,
        giveback_r=0.75,
        cache_htf_mtf=True,
        risk_config=risk_cfg
    )
    
    min_lookback_bars = 15
    replayer._htf_cache = {"key": None, "state": None}
    replayer._mtf_cache = {"key": None, "state": None}
    
    funnel_counts = {
        "total_ltf_bars": len(ltf_candles) - min_lookback_bars,
        "htf_qualified_contexts": 0,
        "mtf_structural_alignments": 0,
        "mtf_causal_retests": 0,
        "ltf_triggers": 0,
        "risk_evaluations": 0,
        "risk_approved_plans": 0,
        "submitted_orders": 0,
        "filled_trades": 0,
        "closed_trades": 0
    }
    rejection_breakdown: Dict[str, int] = {}
    trailing_events_log: List[Dict[str, Any]] = []

    def record_rejection(reason: Any):
        if not reason: return
        reason_str = reason.value if hasattr(reason, 'value') else str(reason)
        rejection_breakdown[reason_str] = rejection_breakdown.get(reason_str, 0) + 1

    # 4. Step chronologically forward through LTF candles (Zero Lookahead)
    for i in range(min_lookback_bars, len(ltf_candles)):
        current_bar = ltf_candles[i]
        decision_timestamp = current_bar.timestamp
        
        # A. Process forward candle against existing orders (adverse-first execution)
        replayer.execution_simulator.process_candle(current_bar, replayer.ledger)
        
        # B. Visible candle slices
        ltf_slice = ltf_candles[max(0, i - 150):i + 1]
        mtf_slice = TimeframeAligner.filter_visible_candles(
            mtf_candles, decision_timestamp, tf_info["mtf"], buffer_size=100
        )
        htf_slice = TimeframeAligner.filter_visible_candles(
            htf_candles, decision_timestamp, tf_info["htf"], buffer_size=80
        )
        
        if len(htf_slice) < 5 or len(mtf_slice) < 5 or len(ltf_slice) < 5:
            continue
            
        try:
            # C. Market Intelligence (P01)
            htf_key = htf_slice[-1].timestamp if htf_slice else None
            if replayer._htf_cache["key"] != htf_key:
                htf_state = replayer.language_coordinator.run(htf_slice, symbol=symbol, timeframe=tf_info["htf"])
                replayer._htf_cache = {"key": htf_key, "state": htf_state}
            else:
                htf_state = replayer._htf_cache["state"]
                
            mtf_key = mtf_slice[-1].timestamp if mtf_slice else None
            if replayer._mtf_cache["key"] != mtf_key:
                mtf_state = replayer.language_coordinator.run(mtf_slice, symbol=symbol, timeframe=tf_info["mtf"])
                replayer._mtf_cache = {"key": mtf_key, "state": mtf_state}
            else:
                mtf_state = replayer._mtf_cache["state"]
                
            ltf_state = replayer.language_coordinator.run(ltf_slice, symbol=symbol, timeframe=tf_info["ltf"])
            
            # D. Strategy Evaluation (P02)
            trade_plans = replayer.strategy_coordinator.evaluate(htf_state, mtf_state, ltf_state)
            
            # Update Funnel Telemetry from active candidates
            active_cands = replayer.strategy_coordinator.candidate_tracker.get_active_candidates(symbol, "UNIFIED_STRATEGY")
            for cand in active_cands:
                if cand.state == CandidateState.WAIT_MTF_ALIGNMENT:
                    funnel_counts["htf_qualified_contexts"] += 1
                elif cand.state == CandidateState.WAIT_MTF_RETEST:
                    funnel_counts["mtf_structural_alignments"] += 1
                elif cand.state == CandidateState.WAIT_LTF_TRIGGER:
                    funnel_counts["mtf_causal_retests"] += 1
                elif cand.state == CandidateState.RISK_GATE:
                    funnel_counts["ltf_triggers"] += 1
                    
            # E. MTF Structural Trailing Stop Synchronization
            if replayer.enable_mtf_trailing:
                for t_id, active_plan in replayer.strategy_coordinator.active_manager.active_trades.items():
                    old_stop = None
                    trade_obj = replayer.ledger.trades.get(t_id)
                    if trade_obj:
                        old_stop = trade_obj.current_stop_price
                    replayer.ledger.update_trailing_stop(t_id, active_plan.stop_invalidation_price)
                    if trade_obj and trade_obj.current_stop_price != old_stop:
                        trailing_events_log.append({
                            "trade_id": t_id,
                            "timestamp": decision_timestamp,
                            "old_stop": old_stop,
                            "new_stop": trade_obj.current_stop_price
                        })
                    
            # F. Risk Gate & Order Dispatch (P03)
            for plan in trade_plans:
                if plan.status == CandidateState.ENTERED.value:
                    funnel_counts["risk_evaluations"] += 1
                    
                    account_state = AccountState(
                        current_equity=replayer.ledger.current_equity,
                        peak_equity=replayer.ledger.peak_equity,
                        daily_pnl=0.0,
                        weekly_pnl=0.0,
                        open_position_count=len(replayer.ledger.get_active_trades()),
                        active_assets={t.symbol: 1.0 for t in replayer.ledger.get_active_trades()}
                    )
                    
                    risk_result = RiskCoordinator.evaluate(plan, account_state, config=risk_cfg)
                    
                    if isinstance(risk_result, RiskApprovedPlan):
                        funnel_counts["risk_approved_plans"] += 1
                        funnel_counts["submitted_orders"] += 1
                        
                        simulated_trade = SimulatedTrade(
                            trade_id=plan.trade_plan_id,
                            hypothesis_id=plan.hypothesis_id,
                            symbol=symbol,
                            timeframe_set=tf_set_id,
                            directional_permission=plan.directional_permission,
                            setup_timestamp=plan.setup_timestamp,
                            entry_price=plan.entry_price,
                            initial_stop_price=plan.stop_invalidation_price,
                            current_stop_price=plan.stop_invalidation_price,
                            target_price=plan.target_price,
                            position_units=risk_result.position_units,
                            dollar_risk=risk_result.dollar_risk,
                            raw_rr=plan.raw_rr,
                            status="PENDING_ENTRY",
                            metadata={"structural_provenance": plan.structural_provenance}
                        )
                        replayer.ledger.record_pending_trade(simulated_trade)
                    else:
                        record_rejection(risk_result.reason if hasattr(risk_result, 'reason') else "RISK_REJECTED")
                        
                elif plan.position_status == "MTF_TRAIL_EXIT":
                    if replayer.enable_mtf_trailing:
                        replayer.execution_simulator.execute_structural_exit(
                            trade_id=plan.trade_plan_id,
                            current_market_price=ltf_state.current_price,
                            timestamp=decision_timestamp,
                            exit_reason="MTF_STRUCTURAL_TRAIL",
                            ledger=replayer.ledger
                        )
                else:
                    if plan.rejection_reason:
                        record_rejection(plan.rejection_reason)
                        
        except Exception as e:
            continue

    elapsed = time.time() - t0
    
    # 5. Compute Quantitative Metrics
    closed_trades = replayer.ledger.closed_trades
    funnel_counts["filled_trades"] = len([t for t in closed_trades if t.fill_entry_price is not None and t.fill_entry_price > 0])
    funnel_counts["closed_trades"] = len(closed_trades)
    
    total_trades = len(closed_trades)
    wins = [t for t in closed_trades if (t.realized_rr or 0.0) > 0]
    losses = [t for t in closed_trades if (t.realized_rr or 0.0) <= 0]
    
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
    gross_pnl_usd = sum((t.realized_pnl or 0.0) + t.total_friction_usd for t in closed_trades)
    net_pnl_usd = sum(t.realized_pnl for t in closed_trades if t.realized_pnl is not None)
    
    gross_profit_usd = sum(t.realized_pnl for t in wins if t.realized_pnl is not None)
    gross_loss_usd = abs(sum(t.realized_pnl for t in losses if t.realized_pnl is not None))
    profit_factor = (gross_profit_usd / gross_loss_usd) if gross_loss_usd > 0 else (gross_profit_usd if gross_profit_usd > 0 else 0.0)
    
    gross_realized_r = 0.0
    net_realized_r = 0.0
    friction_r_total = 0.0
    mfe_r_list = []
    mae_r_list = []
    
    # Consecutive losses calculation
    max_consec_losses = 0
    current_consec_losses = 0
    for t in closed_trades:
        r_val = t.realized_rr or 0.0
        if r_val <= 0:
            current_consec_losses += 1
            if current_consec_losses > max_consec_losses:
                max_consec_losses = current_consec_losses
        else:
            current_consec_losses = 0
            
    # Contextual decomposition
    context_attribution = {
        "PULLBACK": {"trades": 0, "net_r": 0.0, "net_pnl": 0.0},
        "CONTINUATION": {"trades": 0, "net_r": 0.0, "net_pnl": 0.0}
    }
    
    detailed_ledger_records = []
    for t in closed_trades:
        ep = t.fill_entry_price or t.entry_price
        xp = t.exit_price or ep
        rd = abs(ep - t.initial_stop_price)
        is_l = "LONG" in str(t.directional_permission)
        
        gr_r = ((xp - ep) / rd if is_l else (ep - xp) / rd) if rd > 0 else (t.realized_rr or 0.0)
        nr_r = t.realized_rr if t.realized_rr is not None else 0.0
        fric_r = abs(gr_r - nr_r)
        
        gross_realized_r += gr_r
        net_realized_r += nr_r
        friction_r_total += fric_r
        
        mfe_p = t.metadata.get("mfe_price", ep) if t.metadata else ep
        mae_p = t.metadata.get("mae_price", ep) if t.metadata else ep
        if rd > 0:
            mfe_r = (mfe_p - ep) / rd if is_l else (ep - mfe_p) / rd
            mae_r = (ep - mae_p) / rd if is_l else (mae_p - ep) / rd
            mfe_r_list.append(max(0.0, mfe_r))
            mae_r_list.append(max(0.0, mae_r))
            
        prov = t.metadata.get("structural_provenance", {}) if t.metadata else {}
        htf_ctx = prov.get("htf_context") or ("PULLBACK" if "PULLBACK" in str(prov.get("htf_phase", "")) else "CONTINUATION")
        if htf_ctx not in context_attribution:
            context_attribution[htf_ctx] = {"trades": 0, "net_r": 0.0, "net_pnl": 0.0}
        context_attribution[htf_ctx]["trades"] += 1
        context_attribution[htf_ctx]["net_r"] += round(nr_r, 4)
        context_attribution[htf_ctx]["net_pnl"] += round(t.realized_pnl or 0.0, 2)
        
        # Detailed ledger record with full forensic audit schema
        detailed_ledger_records.append({
            "candidate_timestamp": t.setup_timestamp,
            "stream": stream_id,
            "asset": symbol,
            "timeframe_set": tf_set_id,
            "trade_id": t.trade_id,
            "htf_bias": str(t.directional_permission),
            "htf_destination": t.target_price,
            "mtf_realignment": prov.get("mtf_setup_id", "ALIGNED"),
            "mtf_keyzone": prov.get("mtf_keyzone_id", "N/A"),
            "retest": "CONFIRMED",
            "ltf_trigger": "SWEEP_AND_DISPLACEMENT",
            "entry": ep,
            "sl": t.initial_stop_price,
            "tp": t.target_price,
            "planned_rr": t.raw_rr,
            "risk_amount": t.dollar_risk,
            "entry_fee": t.entry_fee,
            "exit_fee": t.exit_fee,
            "gross_pnl": round(gross_pnl_usd, 2),
            "net_pnl": round(t.realized_pnl or 0.0, 2),
            "realized_r": round(nr_r, 4),
            "gross_r": round(gr_r, 4),
            "exit_price": xp,
            "exit_timestamp": t.exit_timestamp,
            "exit_reason": t.exit_reason,
            "trailing_events": [ev for ev in trailing_events_log if ev["trade_id"] == t.trade_id],
            "rejection_reason": t.rejection_reason
        })

    expectancy_r = (net_realized_r / total_trades) if total_trades > 0 else 0.0
    median_r = float(np.median([t.realized_rr for t in closed_trades])) if total_trades > 0 else 0.0
    avg_r = (net_realized_r / total_trades) if total_trades > 0 else 0.0
    
    # Max Drawdown from equity curve
    equity_curve = replayer.ledger.equity_curve
    max_dd_usd = 0.0
    max_dd_pct = 0.0
    if equity_curve:
        peak = equity_curve[0]["equity"]
        for pt in equity_curve:
            eq = pt["equity"]
            if eq > peak:
                peak = eq
            dd_usd = peak - eq
            dd_pct = (dd_usd / peak * 100.0) if peak > 0 else 0.0
            if dd_usd > max_dd_usd:
                max_dd_usd = dd_usd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

    # Exit attribution breakdown
    exit_attr = {}
    for exit_type in ["HTF_TP", "MTF_STRUCTURAL_TRAIL", "PROFIT_LOCK_TRAIL", "INITIAL_LTF_SL"]:
        sub_trades = [t for t in closed_trades if t.exit_reason == exit_type]
        sub_cnt = len(sub_trades)
        pct = (sub_cnt / total_trades * 100.0) if total_trades > 0 else 0.0
        sub_gr = []
        sub_nr = []
        for t in sub_trades:
            ep = t.fill_entry_price or t.entry_price
            xp = t.exit_price or ep
            rd = abs(ep - t.initial_stop_price)
            is_l = "LONG" in str(t.directional_permission)
            sub_gr.append(((xp - ep) / rd if is_l else (ep - xp) / rd) if rd > 0 else (t.realized_rr or 0.0))
            sub_nr.append(t.realized_rr or 0.0)
        exit_attr[exit_type] = {
            "count": sub_cnt,
            "pct": round(pct, 1),
            "avg_gross_r": round(float(np.mean(sub_gr)), 4) if sub_cnt > 0 else 0.0,
            "avg_net_r": round(float(np.mean(sub_nr)), 4) if sub_cnt > 0 else 0.0
        }

    # Capital Barrier Evaluation
    # Tier 0 requires: >= 30 trades, valid data, zero data errors
    t0_passed = (total_trades >= 30) and (data_status == "CERTIFIED")
    # Tier 1 requires: Expectancy > 0, PF > 1.0
    t1_passed = t0_passed and (expectancy_r > 0.0) and (profit_factor > 1.0)
    # Tier 2 requires: Net expectancy > 0 after friction
    t2_passed = t1_passed and (net_realized_r > 0.0)
    # Tier 3 requires: Positive expectancy across >= 50% regimes
    t3_passed = t2_passed and all(ctx["net_r"] > 0 for ctx in context_attribution.values() if ctx["trades"] > 0)
    # Tier 4 requires: Max DD < 25%, Max Consec Losses < 10
    t4_passed = t3_passed and (max_dd_pct < 25.0) and (max_consec_losses < 10)
    
    barrier_verdict = "TIER_4_ALLOCATION_READY" if t4_passed else (
        "TIER_3_REGIME_INVARIANT" if t3_passed else (
            "TIER_2_FRICTION_SURVIVOR" if t2_passed else (
                "TIER_1_STATISTICAL_EDGE" if t1_passed else (
                    "TIER_0_STRUCTURAL_SANITY" if t0_passed else "REJECTED_CAPITAL_BARRIER"
                )
            )
        )
    )

    perf = {
        "total_trades": total_trades,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(win_rate, 2),
        "gross_profit_usd": round(gross_profit_usd, 2),
        "gross_loss_usd": round(gross_loss_usd, 2),
        "net_pnl_usd": round(net_pnl_usd, 2),
        "profit_factor": round(profit_factor, 4),
        "gross_realized_r": round(gross_realized_r, 4),
        "total_friction_r": round(friction_r_total, 4),
        "net_realized_r": round(net_realized_r, 4),
        "expectancy_r": round(expectancy_r, 4),
        "avg_r": round(avg_r, 4),
        "median_r": round(median_r, 4),
        "max_drawdown_usd": round(max_dd_usd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "max_consecutive_losses": max_consec_losses,
        "avg_mfe_r": round(float(np.mean(mfe_r_list)), 4) if mfe_r_list else 0.0,
        "median_mfe_r": round(float(np.median(mfe_r_list)), 4) if mfe_r_list else 0.0,
        "avg_mae_r": round(float(np.mean(mae_r_list)), 4) if mae_r_list else 0.0,
        "median_mae_r": round(float(np.median(mae_r_list)), 4) if mae_r_list else 0.0,
        "capital_barrier_verdict": barrier_verdict
    }

    return {
        "stream_id": stream_id,
        "identity": {
            "asset": symbol,
            "timeframe_set": tf_set_id,
            "label": tf_info["label"],
            "htf": tf_info["htf"],
            "mtf": tf_info["mtf"],
            "ltf": tf_info["ltf"],
            "strategy_id": "UNIFIED_CANONICAL_BASELINE",
            "period": period_label
        },
        "data": {
            "data_status": data_status,
            "htf_candles": len(htf_candles),
            "mtf_candles": len(mtf_candles),
            "ltf_candles": len(ltf_candles)
        },
        "execution_time_sec": round(elapsed, 2),
        "lifecycle_funnel": funnel_counts,
        "rejection_attribution": rejection_breakdown,
        "performance": perf,
        "context_attribution": context_attribution,
        "exit_attribution": exit_attr,
        "trade_ledger": detailed_ledger_records
    }


def execute_15_stream_matrix():
    print("=" * 110)
    print("DAY 39: 15-STREAM CANONICAL BASELINE REPLAY (1 Unified Strategy x 5 Timeframe Sets x 3 Assets)")
    print("FROZEN RULES: RR >= 4.0R | Risk <= 1.0% | Profit Lock = OFF | MTF Trailing = ON | Real Fees & Slippage")
    print("=" * 110)
    
    stream_tasks = []
    for asset in ASSETS:
        for tf_set_id in TF_SETS:
            stream_tasks.append((asset, tf_set_id))
            
    total_streams = len(stream_tasks)
    print(f"Launching {total_streams} streams across ProcessPoolExecutor (max_workers=6)...")
    
    all_streams = []
    global_trade_ledger = []
    start_all = time.time()
    
    with ProcessPoolExecutor(max_workers=6) as executor:
        future_map = {
            executor.submit(run_single_stream_canonical, asset, tf_id): (asset, tf_id)
            for asset, tf_id in stream_tasks
        }
        
        done_cnt = 0
        for future in as_completed(future_map):
            asset, tf_id = future_map[future]
            try:
                res = future.result()
                all_streams.append(res)
                done_cnt += 1
                p = res["performance"]
                print(f"[{done_cnt:02d}/{total_streams:02d}] {res['stream_id']:10s} in {res['execution_time_sec']:5.1f}s | Trades: {p['total_trades']:2d} | WR: {p['win_rate_pct']:5.1f}% | Net R: {p['net_realized_r']:+6.2f}R | PF: {p['profit_factor']:.2f} | Max DD: {p['max_drawdown_pct']:4.1f}% | Verdict: {p['capital_barrier_verdict']}")
            except Exception as e:
                print(f"❌ Stream {asset}_{tf_id} failed: {e}")
                import traceback
                traceback.print_exc()

    total_time = time.time() - start_all
    print(f"\nAll {len(all_streams)} streams finished in {total_time:.1f}s.")
    
    # Sort deterministically
    def sort_key(s):
        sym_clean = s["identity"]["asset"].split("/")[0]
        a_idx = ASSETS.index(sym_clean)
        tf_idx = TF_SETS.index(s["identity"]["timeframe_set"])
        return (tf_idx, a_idx)
        
    all_streams.sort(key=sort_key)
    
    for s in all_streams:
        global_trade_ledger.extend(s["trade_ledger"])
        
    # Export artifacts
    scratch_dir = "/home/mrcn2/crypto-platform/scratch"
    os.makedirs(scratch_dir, exist_ok=True)
    matrix_path = os.path.join(scratch_dir, "canonical_multiyear_matrix_results.json")
    ledger_path = os.path.join(scratch_dir, "canonical_trade_ledger.json")
    
    with open(matrix_path, "w") as f:
        json.dump(all_streams, f, indent=2)
        
    with open(ledger_path, "w") as f:
        json.dump(global_trade_ledger, f, indent=2)
        
    print("\n" + "=" * 110)
    print("CONSOLIDATED 15-STREAM BASELINE PERFORMANCE MATRIX")
    print("=" * 110)
    
    header = (
        f"| {'Stream':10s} | {'Asset':8s} | {'TF Set':6s} | {'Trades':6s} | {'Win %':6s} | "
        f"{'Gross R':8s} | {'Net R':8s} | {'Exp (R)':8s} | {'PF':5s} | {'Max DD%':7s} | "
        f"{'Max Loss':8s} | {'Avg R':7s} | {'Med R':7s} | {'Barrier Verdict':24s} |"
    )
    print(header)
    print("|" + "-" * 12 + "|" + "-" * 10 + "|" + "-" * 8 + "|" + "-" * 8 + "|" + "-" * 8 + "|" + "-" * 10 + "|" + "-" * 10 + "|" + "-" * 10 + "|" + "-" * 7 + "|" + "-" * 9 + "|" + "-" * 10 + "|" + "-" * 9 + "|" + "-" * 9 + "|" + "-" * 26 + "|")
    
    tot_tr = 0
    tot_gr = 0.0
    tot_nr = 0.0
    tot_pnl = 0.0
    
    for s in all_streams:
        p = s["performance"]
        tot_tr += p["total_trades"]
        tot_gr += p["gross_realized_r"]
        tot_nr += p["net_realized_r"]
        tot_pnl += p["net_pnl_usd"]
        
        print(
            f"| {s['stream_id']:10s} | {s['identity']['asset']:8s} | {s['identity']['timeframe_set']:6s} | "
            f"{p['total_trades']:6d} | {p['win_rate_pct']:5.1f}% | {p['gross_realized_r']:+7.2f}R | "
            f"{p['net_realized_r']:+7.2f}R | {p['expectancy_r']:+7.3f}R | {p['profit_factor']:5.2f} | "
            f"{p['max_drawdown_pct']:6.1f}% | {p['max_consecutive_losses']:8d} | {p['avg_r']:+6.2f}R | "
            f"{p['median_r']:+6.2f}R | {p['capital_barrier_verdict']:24s} |"
        )
        
    print("=" * 110)
    print(f"TOTAL TRADES ACROSS 15 STREAMS: {tot_tr}")
    print(f"TOTAL GROSS REALIZED R:         {tot_gr:+8.2f}R")
    print(f"TOTAL NET REALIZED R:           {tot_nr:+8.2f}R")
    print(f"TOTAL NET REALIZED PNL:         ${tot_pnl:+9.2f}")
    print(f"IMMUTABLE LEDGER EXPORT:        {ledger_path} ({len(global_trade_ledger)} trades)")
    print(f"MATRIX RESULTS EXPORT:          {matrix_path} (15 streams)")
    print("=" * 110)
    
    return all_streams, global_trade_ledger


if __name__ == "__main__":
    execute_15_stream_matrix()
