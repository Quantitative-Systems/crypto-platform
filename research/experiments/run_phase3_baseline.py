"""
Product 04 — Research Laboratory: Phase 3 Empirical Baseline Replay & Research Gate
Executes a single controlled baseline stream for BTC/USDT on Set 1 (1M -> 1W -> 1D)
with full lifecycle funnel tracking, trade-level provenance, causality checks, and OOS partition.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
import numpy as np

from market_data.warehouse_loader import WarehouseLoader
from market_data.data_certifier import DataCertifier
from research.replayer.causal_replayer import CausalReplayer
from research.replayer.timeframe_aligner import TimeframeAligner
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.metrics.metrics_engine import MetricsEngine
from research.metrics.exit_attribution import ExitAttributionEngine
from research.analytics.failure_analyzer import FailureAnalyzer
from risk_engine.contracts.risk_config import RiskConfig
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.contracts.risk_rejection import RiskRejectionPayload, RiskRejectionReason
from risk_engine.risk_coordinator import RiskCoordinator
from strategy_engine.contracts.strategy_state import CandidateState


def run_single_stream_baseline(
    symbol: str = "BTC/USDT",
    timeframe_set_id: str = "SET_1",
    initial_balance: float = 10000.0,
    maker_fee_rate: float = 0.0000,
    taker_fee_rate: float = 0.0005,
    slippage_bps: float = 5.0,
    enable_mtf_trailing: bool = True,
    enable_profit_lock: bool = True,
    lockin_r: float = 1.0,
    giveback_r: float = 0.75,
) -> Dict[str, Any]:
    tf_set = TimeframeAligner.get_set(timeframe_set_id)
    
    # 1. Load certified historical datasets
    htf_candles = WarehouseLoader.load_history(symbol, tf_set.htf, limit=50000)
    mtf_candles = WarehouseLoader.load_history(symbol, tf_set.mtf, limit=50000)
    ltf_candles = WarehouseLoader.load_history(symbol, tf_set.ltf, limit=50000)
    
    # Certify datasets and overlap
    DataCertifier.certify_dataset(htf_candles, tf_set.htf, symbol, allow_gaps=True)
    DataCertifier.certify_dataset(mtf_candles, tf_set.mtf, symbol, allow_gaps=True)
    DataCertifier.certify_dataset(ltf_candles, tf_set.ltf, symbol, allow_gaps=True)
    
    # 2. Replay setup
    risk_cfg = RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=4.0,
        min_stop_distance_pct=0.001,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False
    )
    
    replayer = CausalReplayer(
        timeframe_set_id=timeframe_set_id,
        initial_balance=initial_balance,
        maker_fee_rate=maker_fee_rate,
        taker_fee_rate=taker_fee_rate,
        slippage_bps=slippage_bps,
        enable_mtf_trailing=enable_mtf_trailing,
        enable_profit_lock=enable_profit_lock,
        lockin_r=lockin_r,
        giveback_r=giveback_r,
        cache_htf_mtf=True,
        risk_config=risk_cfg
    )
    
    # 3. Custom event loop instrumentation for lifecycle funnel tracking
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
        "risk_approved_candidates": 0,
        "risk_rejected_candidates": 0,
        "submitted_orders": 0,
        "filled_trades": 0,
        "closed_trades": 0
    }
    rejection_breakdown: Dict[str, int] = {}
    detailed_trades: List[Dict[str, Any]] = []
    
    t0 = time.time()
    
    for i in range(min_lookback_bars, len(ltf_candles)):
        current_bar = ltf_candles[i]
        decision_timestamp = current_bar.timestamp
        
        # Step A: Execution Simulator processes forward candle
        replayer.execution_simulator.process_candle(current_bar, replayer.ledger)
        
        # Step B: Point-in-time candle slicing
        ltf_slice = ltf_candles[max(0, i - 150):i + 1]
        mtf_slice = TimeframeAligner.filter_visible_candles(
            mtf_candles, decision_timestamp, tf_set.mtf, buffer_size=100
        )
        htf_slice = TimeframeAligner.filter_visible_candles(
            htf_candles, decision_timestamp, tf_set.htf, buffer_size=80
        )
        
        if len(htf_slice) < 5 or len(mtf_slice) < 5 or len(ltf_slice) < 5:
            continue
            
        # Step C: Market Intelligence
        htf_key = htf_slice[-1].timestamp if htf_slice else None
        if replayer._htf_cache["key"] != htf_key:
            htf_state = replayer.language_coordinator.run(htf_slice, symbol=symbol, timeframe=tf_set.htf)
            replayer._htf_cache = {"key": htf_key, "state": htf_state}
        else:
            htf_state = replayer._htf_cache["state"]
            
        mtf_key = mtf_slice[-1].timestamp if mtf_slice else None
        if replayer._mtf_cache["key"] != mtf_key:
            mtf_state = replayer.language_coordinator.run(mtf_slice, symbol=symbol, timeframe=tf_set.mtf)
            replayer._mtf_cache = {"key": mtf_key, "state": mtf_state}
        else:
            mtf_state = replayer._mtf_cache["state"]
            
        ltf_state = replayer.language_coordinator.run(ltf_slice, symbol=symbol, timeframe=tf_set.ltf)
        
        # Step D: Strategy Evaluation
        trade_plans = replayer.strategy_coordinator.evaluate(htf_state, mtf_state, ltf_state)
        
        # Count active candidate tracking states for funnel telemetry
        active_cands = replayer.strategy_coordinator.candidate_tracker.get_active_candidates(symbol, "UNIFIED_STRATEGY")
        if active_cands:
            funnel_counts["htf_qualified_contexts"] += 1
            for cand in active_cands:
                if cand.state in [CandidateState.WAIT_MTF_RETEST, CandidateState.WAIT_LTF_TRIGGER]:
                    funnel_counts["mtf_structural_alignments"] += 1
                if cand.state == CandidateState.WAIT_LTF_TRIGGER:
                    funnel_counts["mtf_causal_retests"] += 1
                    
        # Step E: Process Trade Plans
        for plan in trade_plans:
            if plan.status == CandidateState.ENTERED.value:
                funnel_counts["ltf_triggers"] += 1
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
                    funnel_counts["risk_approved_candidates"] += 1
                    funnel_counts["submitted_orders"] += 1
                    
                    simulated_trade = SimulatedTrade(
                        trade_id=plan.trade_plan_id,
                        hypothesis_id=plan.hypothesis_id,
                        symbol=symbol,
                        timeframe_set=tf_set.set_id,
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
                        metadata={
                            "structural_provenance": plan.structural_provenance,
                            "htf_bias": htf_state.trend_state.value if htf_state.trend_state else "NEUTRAL",
                            "mtf_trend": mtf_state.structure_state.external_trend.value if mtf_state.structure_state else "NEUTRAL",
                            "ltf_trend": ltf_state.structure_state.external_trend.value if ltf_state.structure_state else "NEUTRAL"
                        }
                    )
                    replayer.ledger.record_pending_trade(simulated_trade)
                else:
                    funnel_counts["risk_rejected_candidates"] += 1
                    reason = risk_result.reason.value if hasattr(risk_result, "reason") else str(risk_result)
                    rejection_breakdown[reason] = rejection_breakdown.get(reason, 0) + 1
            else:
                if plan.status == CandidateState.REJECTED.value:
                    funnel_counts["risk_rejected_candidates"] += 1
                    reason = plan.rejection_reason or "REJECT_STRATEGY_RULE"
                    rejection_breakdown[reason] = rejection_breakdown.get(reason, 0) + 1
                    
    elapsed = time.time() - t0
    
    # 4. Extract closed trades & metrics
    closed_trades = replayer.ledger.closed_trades
    funnel_counts["filled_trades"] = len([t for t in replayer.ledger.trades.values() if t.status in ["ACTIVE", "CLOSED"]])
    funnel_counts["closed_trades"] = len(closed_trades)
    
    metrics = MetricsEngine.calculate_metrics(closed_trades, replayer.ledger)
    exit_attribution = ExitAttributionEngine.analyze(closed_trades)
    failure_modes = FailureAnalyzer.classify_failure_modes(closed_trades)
    
    # 5. In-Sample (70%) vs Out-of-Sample (30%) partitioning
    total_ltf = len(ltf_candles)
    split_idx = int(total_ltf * 0.70)
    split_timestamp = ltf_candles[split_idx].timestamp
    
    is_trades = [t for t in closed_trades if t.setup_timestamp < split_timestamp]
    oos_trades = [t for t in closed_trades if t.setup_timestamp >= split_timestamp]
    
    is_metrics = MetricsEngine.calculate_metrics(is_trades, replayer.ledger)
    oos_metrics = MetricsEngine.calculate_metrics(oos_trades, replayer.ledger)
    
    # Retention calculations
    is_pf = is_metrics["profit_factor"] if isinstance(is_metrics["profit_factor"], (int, float)) else 0.0
    oos_pf = oos_metrics["profit_factor"] if isinstance(oos_metrics["profit_factor"], (int, float)) else 0.0
    
    is_exp = is_metrics["expectancy_r"] if isinstance(is_metrics["expectancy_r"], (int, float)) else 0.0
    oos_exp = oos_metrics["expectancy_r"] if isinstance(oos_metrics["expectancy_r"], (int, float)) else 0.0
    
    wr_ret = (oos_metrics["win_rate"] / is_metrics["win_rate"]) if is_metrics["win_rate"] > 0 else 0.0
    pf_ret = (oos_pf / is_pf) if is_pf > 0 else 0.0
    exp_ret = (oos_exp / is_exp) if is_exp > 0 else 0.0
    
    # OOS Classification
    if oos_metrics["total_trades"] < 10:
        oos_status = "INSUFFICIENT_SAMPLE"
    elif oos_pf >= 1.20 and oos_exp > 0.0:
        oos_status = "OOS_SUPPORTED"
    elif oos_pf >= 1.0 and oos_exp >= 0.0:
        oos_status = "OOS_MARGINAL"
    else:
        oos_status = "OOS_FAILED"
        
    start_dt = datetime.fromtimestamp(ltf_candles[0].timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    split_dt = datetime.fromtimestamp(split_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    end_dt = datetime.fromtimestamp(ltf_candles[-1].timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    return {
        "symbol": symbol,
        "timeframe_set_id": timeframe_set_id,
        "timeframe_set": {
            "htf": tf_set.htf,
            "mtf": tf_set.mtf,
            "ltf": tf_set.ltf,
            "description": tf_set.description
        },
        "period": {
            "start": start_dt,
            "split": split_dt,
            "end": end_dt,
            "total_days": (ltf_candles[-1].timestamp - ltf_candles[0].timestamp) / 86400.0
        },
        "candles_processed": {
            "htf_1M": len(htf_candles),
            "mtf_1W": len(mtf_candles),
            "ltf_1D": len(ltf_candles),
            "replayed_ticks": len(ltf_candles) - min_lookback_bars
        },
        "execution_time_sec": elapsed,
        "funnel_counts": funnel_counts,
        "rejection_breakdown": rejection_breakdown,
        "baseline_metrics": metrics,
        "exit_attribution": exit_attribution,
        "failure_modes": failure_modes,
        "oos_partition": {
            "split_ratio": 0.70,
            "status": oos_status,
            "is_metrics": is_metrics,
            "oos_metrics": oos_metrics,
            "retention": {
                "wr_retention": round(wr_ret, 4),
                "pf_retention": round(pf_ret, 4),
                "exp_retention": round(exp_ret, 4)
            }
        },
        "closed_trades": [t.to_dict() for t in closed_trades],
        "equity_curve": replayer.ledger.equity_curve
    }


def main():
    print("=" * 90)
    print("PHASE 3: EMPIRICAL BASELINE REPLAY — BTC/USDT SET 1 (1M -> 1W -> 1D)")
    print("=" * 90)
    
    results = run_single_stream_baseline()
    
    # Pretty print summary
    print(f"\n[STREAM]: {results['symbol']} | {results['timeframe_set_id']} ({results['timeframe_set']['description']})")
    print(f"[PERIOD]: {results['period']['start']} -> {results['period']['end']} ({results['period']['total_days']:.1f} days)")
    print(f"[CANDLES]: HTF(1M): {results['candles_processed']['htf_1M']} | MTF(1W): {results['candles_processed']['mtf_1W']} | LTF(1D): {results['candles_processed']['ltf_1D']}")
    print(f"[EXECUTION TIME]: {results['execution_time_sec']:.2f}s")
    
    print("\n" + "=" * 50)
    print("LIFECYCLE FUNNEL TELEMETRY")
    print("=" * 50)
    for stage, cnt in results["funnel_counts"].items():
        print(f"  {stage:30s}: {cnt:5d}")
        
    print("\nREJECTION BREAKDOWN:")
    for reason, cnt in results["rejection_breakdown"].items():
        print(f"  {reason:40s}: {cnt:5d}")
        
    print("\n" + "=" * 50)
    print("BASELINE PERFORMANCE METRICS")
    print("=" * 50)
    m = results["baseline_metrics"]
    for k, v in m.items():
        if k != "r_multiples":
            print(f"  {k:30s}: {v}")
            
    print("\n" + "=" * 50)
    print("EXIT ATTRIBUTION")
    print("=" * 50)
    for cat, data in results["exit_attribution"].items():
        print(f"  {cat:25s} -> Count: {data['trade_count']:3d} ({data['percentage_of_total']*100:5.1f}%) | WR: {data['win_rate']*100:5.1f}% | Avg R: {data['avg_realized_r']:+5.2f}R | Total PnL: ${data['total_pnl_usd']:+8.2f}")
        
    print("\n" + "=" * 50)
    print("IN-SAMPLE (70%) VS OUT-OF-SAMPLE (30%)")
    print("=" * 50)
    oos_part = results["oos_partition"]
    is_m = oos_part["is_metrics"]
    oos_m = oos_part["oos_metrics"]
    ret = oos_part["retention"]
    print(f"  OOS Status: [{oos_part['status']}]")
    print(f"  IS  (70%) -> Trades: {is_m['total_trades']:3d} | WR: {is_m['win_rate']*100:5.1f}% | PF: {is_m['profit_factor']} | E[R]: {is_m['expectancy_r']}R | Net PnL: ${is_m['net_profit_usd']:+8.2f}")
    print(f"  OOS (30%) -> Trades: {oos_m['total_trades']:3d} | WR: {oos_m['win_rate']*100:5.1f}% | PF: {oos_m['profit_factor']} | E[R]: {oos_m['expectancy_r']}R | Net PnL: ${oos_m['net_profit_usd']:+8.2f}")
    print(f"  Retention -> WR: {ret['wr_retention']:.2f}x | PF: {ret['pf_retention']:.2f}x | Exp: {ret['exp_retention']:.2f}x")
    
    # Save output to scratch artifact
    os.makedirs("/home/mrcn2/crypto-platform/scratch", exist_ok=True)
    out_file = "/home/mrcn2/crypto-platform/scratch/phase3_baseline_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Saved full baseline replay artifact to {out_file}")


if __name__ == "__main__":
    main()
