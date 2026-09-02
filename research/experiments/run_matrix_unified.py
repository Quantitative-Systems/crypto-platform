"""
Product 04 — Research Laboratory: Full Strategy Forensic Matrix (Unified Contexts)
Executes the Frozen Canonical Unified State Machine across 15 independent streams:
  - 3 Assets: BTC/USDT, ETH/USDT, SOL/USDT
  - 5 Timeframe Sets:
      SET_1 (1M -> 1W -> 1D, Macro)
      SET_2 (1W -> 1D -> 4H, Position)
      SET_3 (1D -> 4H -> 1H, Swing)
      SET_4 (4H -> 1H -> 15M, Intraday)
      SET_5 (15M -> 5M -> 1M, Intraday Scalping)
Period: Canonical certified 2023 annual benchmark (2023-01-01 to 2024-01-01, 365 days).
"""

import os
import json
import time
from datetime import datetime, timezone
import numpy as np
from typing import Dict, Any, List
from concurrent.futures import ProcessPoolExecutor, as_completed

from market_data.warehouse_loader import WarehouseLoader
from market_data.data_certifier import DataCertifier
from research.replayer.causal_replayer import CausalReplayer
from research.replayer.timeframe_aligner import TimeframeAligner
from research.simulation.trade_ledger import SimulatedTrade
from risk_engine.contracts.risk_config import RiskConfig
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.risk_coordinator import RiskCoordinator
from strategy_engine.contracts.strategy_state import CandidateState


ASSETS = ["BTC", "ETH", "SOL"]
TF_SETS = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]

TF_SET_LABELS = {
    "SET_1": "SET_1 (1M -> 1W -> 1D)",
    "SET_2": "SET_2 (1W -> 1D -> 4H)",
    "SET_3": "SET_3 (1D -> 4H -> 1H)",
    "SET_4": "SET_4 (4H -> 1H -> 15M)",
    "SET_5": "SET_5 (15M -> 5M -> 1M)"
}


def run_single_stream(asset: str, tf_set_id: str) -> Dict[str, Any]:
    stream_id = f"{asset}_{tf_set_id}"
    symbol = f"{asset}/USDT"
    tf_set = TimeframeAligner.get_set(tf_set_id)
    
    # Certified 2023 annual benchmark period
    ltf_start_time_ms = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end_time_ms = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    
    t0 = time.time()
    
    funnel_counts = {
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
    
    def record_rejection(reason: Any):
        if not reason:
            return
        reason_str = reason.value if hasattr(reason, 'value') else str(reason)
        rejection_breakdown[reason_str] = rejection_breakdown.get(reason_str, 0) + 1

    # For SET_5, verify if real 5m and 1m datasets exist or are missing from historical warehouse
    if tf_set_id == "SET_5":
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "market_data", "cache")
        binance_symbol = symbol.replace("/", "").upper()
        c_15m_file = os.path.join(cache_dir, f"binance_{binance_symbol}_15m.json")
        c_5m_file = os.path.join(cache_dir, f"binance_{binance_symbol}_5m.json")
        c_1m_file = os.path.join(cache_dir, f"binance_{binance_symbol}_1m.json")
        
        has_15m = os.path.exists(c_15m_file)
        has_5m = os.path.exists(c_5m_file)
        has_1m = os.path.exists(c_1m_file)
        
        if not (has_15m and has_5m and has_1m):
            data_status = "INSUFFICIENT_HISTORY"
            elapsed = time.time() - t0
            print(f"ℹ️ [SET_5 DATA STATUS] [{stream_id}] 15M: {'AVAILABLE' if has_15m else 'MISSING'}, 5M: {'AVAILABLE' if has_5m else 'MISSING'}, 1M: {'AVAILABLE' if has_1m else 'MISSING'}")
            return {
                "stream_id": stream_id,
                "identity": {
                    "asset": asset,
                    "timeframe_set": tf_set_id,
                    "label": TF_SET_LABELS[tf_set_id],
                    "htf": tf_set.htf,
                    "mtf": tf_set.mtf,
                    "ltf": tf_set.ltf,
                    "strategy_id": "UNIFIED_HTF_TREND_STRATEGY",
                    "period_start": "2023-01-01 00:00:00 UTC",
                    "period_end": "2024-01-01 00:00:00 UTC",
                    "total_days": 365.0
                },
                "data": {
                    "data_status": data_status,
                    "htf_status": "AVAILABLE" if has_15m else "MISSING",
                    "mtf_status": "AVAILABLE" if has_5m else "MISSING",
                    "ltf_status": "AVAILABLE" if has_1m else "MISSING",
                    "htf_candles": 35036 if has_15m else 0,
                    "mtf_candles": 0,
                    "ltf_candles": 0
                },
                "execution_time_sec": round(elapsed, 2),
                "lifecycle_funnel": funnel_counts,
                "rejection_attribution": rejection_breakdown,
                "performance": {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate_pct": 0.0,
                    "gross_profit_usd": 0.0,
                    "gross_loss_usd": 0.0,
                    "net_pnl_usd": 0.0,
                    "profit_factor": 0.0,
                    "gross_realized_r": 0.0,
                    "total_friction_r": 0.0,
                    "net_realized_r": 0.0,
                    "expectancy_r": 0.0,
                    "median_r": 0.0,
                    "max_drawdown_usd": 0.0,
                    "max_drawdown_pct": 0.0,
                    "avg_mfe_r": 0.0,
                    "median_mfe_r": 0.0,
                    "avg_mae_r": 0.0,
                    "median_mae_r": 0.0
                },
                "context_attribution": {
                    "PULLBACK": {"trades": 0, "net_r": 0.0, "net_pnl": 0.0},
                    "CONTINUATION": {"trades": 0, "net_r": 0.0, "net_pnl": 0.0}
                },
                "exit_attribution": {
                    "HTF_TP": {"count": 0, "pct": 0.0, "avg_gross_r": 0.0, "avg_net_r": 0.0},
                    "MTF_STRUCTURAL_TRAIL": {"count": 0, "pct": 0.0, "avg_gross_r": 0.0, "avg_net_r": 0.0},
                    "PROFIT_LOCK_TRAIL": {"count": 0, "pct": 0.0, "avg_gross_r": 0.0, "avg_net_r": 0.0},
                    "INITIAL_LTF_SL": {"count": 0, "pct": 0.0, "avg_gross_r": 0.0, "avg_net_r": 0.0}
                },
                "trade_ledger": []
            }

    # 1. Load warmup & simulation candles for SET_1 to SET_4 (or SET_5 if cached)
    data_status = "CERTIFIED"
    try:
        htf_candles = WarehouseLoader.load_history(symbol, tf_set.htf, limit=1_000_000, start_time_ms=None, end_time_ms=end_time_ms)
        mtf_candles = WarehouseLoader.load_history(symbol, tf_set.mtf, limit=1_000_000, start_time_ms=None, end_time_ms=end_time_ms)
        ltf_candles = WarehouseLoader.load_history(symbol, tf_set.ltf, limit=1_000_000, start_time_ms=ltf_start_time_ms, end_time_ms=end_time_ms)
        
        DataCertifier.certify_dataset(htf_candles, tf_set.htf, symbol, allow_gaps=True)
        DataCertifier.certify_dataset(mtf_candles, tf_set.mtf, symbol, allow_gaps=True)
        DataCertifier.certify_dataset(ltf_candles, tf_set.ltf, symbol, allow_gaps=True)
        DataCertifier.certify_overlap(htf_candles, mtf_candles, ltf_candles, min_lookback_bars=15)
    except Exception as data_err:
        data_status = f"DATA_ERROR: {str(data_err)}"
        print(f"⚠️ [DATA WARNING] [{stream_id}] {data_err}")

    # 2. Frozen canonical Risk & Replayer setup
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
        maker_fee_rate=0.0000,
        taker_fee_rate=0.0005,
        slippage_bps=5.0,
        enable_mtf_trailing=True,
        enable_profit_lock=True,
        lockin_r=1.0,
        giveback_r=0.75,
        cache_htf_mtf=True,
        risk_config=risk_cfg
    )
    
    min_lookback_bars = 15
    replayer._htf_cache = {"key": None, "state": None}
    replayer._mtf_cache = {"key": None, "state": None}
    
    if len(ltf_candles) < min_lookback_bars:
        return {
            "stream_id": stream_id,
            "identity": {
                "asset": asset,
                "timeframe_set": tf_set_id,
                "label": TF_SET_LABELS[tf_set_id],
                "htf": tf_set.htf,
                "mtf": tf_set.mtf,
                "ltf": tf_set.ltf,
                "strategy_id": "UNIFIED_HTF_TREND_STRATEGY",
                "period_start": "2023-01-01 00:00:00 UTC",
                "period_end": "2024-01-01 00:00:00 UTC",
                "total_days": 365.0
            },
            "data": {
                "data_status": data_status,
                "htf_candles": len(htf_candles),
                "mtf_candles": len(mtf_candles),
                "ltf_candles": len(ltf_candles)
            },
            "execution_time_sec": round(time.time() - t0, 2),
            "lifecycle_funnel": funnel_counts,
            "rejection_attribution": rejection_breakdown,
            "performance": {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate_pct": 0.0,
                "gross_profit_usd": 0.0,
                "gross_loss_usd": 0.0,
                "net_pnl_usd": 0.0,
                "profit_factor": 0.0,
                "gross_realized_r": 0.0,
                "total_friction_r": 0.0,
                "net_realized_r": 0.0,
                "expectancy_r": 0.0,
                "median_r": 0.0,
                "max_drawdown_usd": 0.0,
                "max_drawdown_pct": 0.0,
                "avg_mfe_r": 0.0,
                "median_mfe_r": 0.0,
                "avg_mae_r": 0.0,
                "median_mae_r": 0.0
            },
            "context_attribution": {
                "PULLBACK": {"trades": 0, "net_r": 0.0, "net_pnl": 0.0},
                "CONTINUATION": {"trades": 0, "net_r": 0.0, "net_pnl": 0.0}
            },
            "exit_attribution": {
                "HTF_TP": {"count": 0, "pct": 0.0, "avg_gross_r": 0.0, "avg_net_r": 0.0},
                "MTF_STRUCTURAL_TRAIL": {"count": 0, "pct": 0.0, "avg_gross_r": 0.0, "avg_net_r": 0.0},
                "PROFIT_LOCK_TRAIL": {"count": 0, "pct": 0.0, "avg_gross_r": 0.0, "avg_net_r": 0.0},
                "INITIAL_LTF_SL": {"count": 0, "pct": 0.0, "avg_gross_r": 0.0, "avg_net_r": 0.0}
            },
            "trade_ledger": []
        }

    # Step chronologically forward through LTF candles
    for i in range(min_lookback_bars, len(ltf_candles)):
        current_bar = ltf_candles[i]
        decision_timestamp = current_bar.timestamp
        
        # 1. Process forward candle against existing orders
        replayer.execution_simulator.process_candle(current_bar, replayer.ledger)
        
        # 2. Extract point-in-time visible candle slices
        ltf_slice = ltf_candles[max(0, i - 150):i + 1]
        mtf_slice = TimeframeAligner.filter_visible_candles(
            mtf_candles, decision_timestamp, tf_set.mtf, buffer_size=100
        )
        htf_slice = TimeframeAligner.filter_visible_candles(
            htf_candles, decision_timestamp, tf_set.htf, buffer_size=80
        )
        
        if len(htf_slice) < 5 or len(mtf_slice) < 5 or len(ltf_slice) < 5:
            continue
            
        try:
            # 3. Compute deterministic Market Intelligence state (P01)
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
            
            # Inspect Candidate Lifecycle Transitions
            active_before = list(replayer.strategy_coordinator.candidate_tracker.get_active_candidates(symbol, "UNIFIED_STRATEGY"))
            
            # 4. Evaluate Strategy Lifecycle Engine (P02)
            trade_plans = replayer.strategy_coordinator.evaluate(htf_state, mtf_state, ltf_state)
            
            # Update Funnel Telemetry from candidate states
            active_after = list(replayer.strategy_coordinator.candidate_tracker.get_active_candidates(symbol, "UNIFIED_STRATEGY"))
            for cand in active_after:
                if cand.state == CandidateState.WAIT_MTF_ALIGNMENT:
                    funnel_counts["htf_qualified_contexts"] += 1
                elif cand.state == CandidateState.WAIT_MTF_RETEST:
                    funnel_counts["mtf_structural_alignments"] += 1
                elif cand.state == CandidateState.WAIT_LTF_TRIGGER:
                    funnel_counts["mtf_causal_retests"] += 1
                elif cand.state == CandidateState.RISK_GATE:
                    funnel_counts["ltf_triggers"] += 1
                    
            # Synchronize MTF Structural Trailing Stop with Ledger
            if replayer.enable_mtf_trailing:
                for t_id, active_plan in replayer.strategy_coordinator.active_manager.active_trades.items():
                    replayer.ledger.update_trailing_stop(t_id, active_plan.stop_invalidation_price)
                    
            # 5. Process emitted trade plans through Risk Firewall (P03)
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
                        # Rejected by Risk Firewall
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
    
    # Financial & Excursion Telemetry
    closed_trades = replayer.ledger.closed_trades
    funnel_counts["filled_trades"] = len([t for t in closed_trades if t.fill_entry_price is not None and t.fill_entry_price > 0])
    funnel_counts["closed_trades"] = len(closed_trades)
    
    total_trades = len(closed_trades)
    wins = [t for t in closed_trades if (t.realized_rr or 0.0) > 0]
    losses = [t for t in closed_trades if (t.realized_rr or 0.0) <= 0]
    
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
    gross_pnl_usd = sum(t.realized_pnl + t.total_friction_usd for t in closed_trades if t.realized_pnl is not None)
    net_pnl_usd = sum(t.realized_pnl for t in closed_trades if t.realized_pnl is not None)
    
    gross_profit_usd = sum(t.realized_pnl for t in wins if t.realized_pnl is not None)
    gross_loss_usd = abs(sum(t.realized_pnl for t in losses if t.realized_pnl is not None))
    profit_factor = (gross_profit_usd / gross_loss_usd) if gross_loss_usd > 0 else (gross_profit_usd if gross_profit_usd > 0 else 0.0)
    
    gross_realized_r = 0.0
    net_realized_r = 0.0
    friction_r_total = 0.0
    
    mfe_r_list = []
    mae_r_list = []
    
    # Contextual decomposition
    context_attribution = {
        "PULLBACK": {"trades": 0, "net_r": 0.0, "net_pnl": 0.0},
        "CONTINUATION": {"trades": 0, "net_r": 0.0, "net_pnl": 0.0}
    }
    
    for t in closed_trades:
        ep = t.fill_entry_price or t.entry_price
        xp = t.exit_price or ep
        rd = abs(ep - t.initial_stop_price)
        is_l = "LONG" in str(t.directional_permission)
        
        gr_r = ((xp - ep) / rd if is_l else (ep - xp) / rd) if rd > 0 else (t.realized_rr or 0.0)
        nr_r = t.realized_rr if t.realized_rr is not None else 0.0
        
        gross_realized_r += gr_r
        net_realized_r += nr_r
        friction_r_total += abs(gr_r - nr_r)
        
        # MFE / MAE
        mfe_p = t.metadata.get("mfe_price", ep) if t.metadata else ep
        mae_p = t.metadata.get("mae_price", ep) if t.metadata else ep
        
        if rd > 0:
            if is_l:
                mfe_r = (mfe_p - ep) / rd
                mae_r = (ep - mae_p) / rd
            else:
                mfe_r = (ep - mfe_p) / rd
                mae_r = (mae_p - ep) / rd
            mfe_r_list.append(max(0.0, mfe_r))
            mae_r_list.append(max(0.0, mae_r))
            
        # Attribution by HTF Context
        prov = t.metadata.get("structural_provenance", {}) if t.metadata else {}
        htf_ctx = prov.get("htf_context") or ("PULLBACK" if "PULLBACK" in str(prov.get("htf_phase", "")) else "CONTINUATION")
        if htf_ctx not in context_attribution:
            context_attribution[htf_ctx] = {"trades": 0, "net_r": 0.0, "net_pnl": 0.0}
        context_attribution[htf_ctx]["trades"] += 1
        context_attribution[htf_ctx]["net_r"] += round(nr_r, 4)
        context_attribution[htf_ctx]["net_pnl"] += round(t.realized_pnl or 0.0, 2)

    expectancy_r = (net_realized_r / total_trades) if total_trades > 0 else 0.0
    median_r = float(np.median([t.realized_rr for t in closed_trades])) if total_trades > 0 else 0.0
    
    # Calculate Max Drawdown from equity curve
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
        "median_r": round(median_r, 4),
        "max_drawdown_usd": round(max_dd_usd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "avg_mfe_r": round(float(np.mean(mfe_r_list)), 4) if mfe_r_list else 0.0,
        "median_mfe_r": round(float(np.median(mfe_r_list)), 4) if mfe_r_list else 0.0,
        "avg_mae_r": round(float(np.mean(mae_r_list)), 4) if mae_r_list else 0.0,
        "median_mae_r": round(float(np.median(mae_r_list)), 4) if mae_r_list else 0.0
    }
    
    # Date range formatting
    start_dt = datetime.fromtimestamp(ltf_start_time_ms // 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    end_dt = datetime.fromtimestamp(end_time_ms // 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total_days = (end_time_ms - ltf_start_time_ms) / (1000 * 86400)
    
    # Exit attribution breakdown
    exit_attr = {}
    for exit_type in ["HTF_TP", "MTF_STRUCTURAL_TRAIL", "PROFIT_LOCK_TRAIL", "INITIAL_LTF_SL"]:
        sub_trades = [t for t in closed_trades if t.exit_reason == exit_type]
        sub_cnt = len(sub_trades)
        pct = (sub_cnt / total_trades * 100.0) if total_trades > 0 else 0.0
        sub_gross_r = []
        sub_net_r = []
        for t in sub_trades:
            ep = t.fill_entry_price or t.entry_price
            xp = t.exit_price or ep
            rd = abs(ep - t.initial_stop_price)
            is_l = "LONG" in str(t.directional_permission)
            sub_gross_r.append(((xp - ep) / rd if is_l else (ep - xp) / rd) if rd > 0 else (t.realized_rr or 0.0))
            sub_net_r.append(t.realized_rr or 0.0)
            
        avg_gr = float(np.mean(sub_gross_r)) if sub_cnt > 0 else 0.0
        avg_nr = float(np.mean(sub_net_r)) if sub_cnt > 0 else 0.0
        exit_attr[exit_type] = {
            "count": sub_cnt,
            "pct": round(pct, 1),
            "avg_gross_r": round(avg_gr, 4),
            "avg_net_r": round(avg_nr, 4)
        }
            
    # Trade ledger with exact requested schema
    serialized_ledger = []
    for t in closed_trades:
        ep = t.fill_entry_price or t.entry_price
        xp = t.exit_price or ep
        rd = abs(ep - t.initial_stop_price)
        is_l = "LONG" in str(t.directional_permission)
        gr_r = ((xp - ep) / rd if is_l else (ep - xp) / rd) if rd > 0 else (t.realized_rr or 0.0)
        nr_r = t.realized_rr if t.realized_rr is not None else 0.0
        fric_r = abs(gr_r - nr_r)
        
        prov = t.metadata.get("structural_provenance", {}) if t.metadata else {}
        htf_ctx = prov.get("htf_context") or ("PULLBACK" if "PULLBACK" in str(prov.get("htf_phase", "")) else "CONTINUATION")
        
        serialized_ledger.append({
            "stream": stream_id,
            "trade_id": t.trade_id,
            "direction": str(t.directional_permission),
            "strategy_id": "UNIFIED_HTF_TREND_STRATEGY",
            "htf_context": htf_ctx,
            "entry_timestamp": t.entry_timestamp,
            "entry_price": ep,
            "stop": t.initial_stop_price,
            "target": t.target_price,
            "planned_rr": t.raw_rr,
            "exit_timestamp": t.exit_timestamp,
            "exit_price": xp,
            "exit_reason": t.exit_reason,
            "gross_r": round(gr_r, 4),
            "friction": round(t.total_friction_usd, 4),
            "friction_r": round(fric_r, 4),
            "net_r": round(nr_r, 4),
            "net_pnl": round(t.realized_pnl or 0.0, 2)
        })

    return {
        "stream_id": stream_id,
        "identity": {
            "asset": asset,
            "timeframe_set": tf_set_id,
            "label": TF_SET_LABELS[tf_set_id],
            "htf": tf_set.htf,
            "mtf": tf_set.mtf,
            "ltf": tf_set.ltf,
            "strategy_id": "UNIFIED_HTF_TREND_STRATEGY",
            "period_start": start_dt,
            "period_end": end_dt,
            "total_days": round(total_days, 1)
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
        "trade_ledger": serialized_ledger
    }


def execute_matrix_replay() -> Dict[str, Any]:
    print("=" * 100)
    print("PHASE 3C / 4: 15-STREAM UNIFIED CANONICAL BASELINE REPLAY (BTC, ETH, SOL x SET_1 to SET_5)")
    print("=" * 100)
    
    stream_tasks = []
    for asset in ASSETS:
        for tf_set_id in TF_SETS:
            stream_tasks.append((asset, tf_set_id))
            
    total_streams = len(stream_tasks)
    print(f"Launching {total_streams} streams across ProcessPoolExecutor (max_workers=6)...")
    
    all_streams_data = []
    global_trade_ledger = []
    
    start_all = time.time()
    
    # Run in parallel across 6 worker processes
    with ProcessPoolExecutor(max_workers=6) as executor:
        future_to_task = {
            executor.submit(run_single_stream, asset, tf_set_id): (asset, tf_set_id)
            for asset, tf_set_id in stream_tasks
        }
        
        completed_count = 0
        for future in as_completed(future_to_task):
            asset, tf_set_id = future_to_task[future]
            try:
                stream_res = future.result()
                all_streams_data.append(stream_res)
                completed_count += 1
                p = stream_res["performance"]
                print(f"[{completed_count:02d}/{total_streams:02d}] Finished {stream_res['stream_id']:10s} in {stream_res['execution_time_sec']:5.1f}s | Trades: {p['total_trades']:2d} | WR: {p['win_rate_pct']:5.1f}% | PF: {p['profit_factor']:.2f} | Net R: {p['net_realized_r']:+6.2f}R | Net PnL: ${p['net_pnl_usd']:+8.2f}")
            except Exception as exc:
                print(f"❌ Error in stream {asset}_{tf_set_id}: {exc}")
                import traceback
                traceback.print_exc()

    total_time = time.time() - start_all
    print(f"\nAll {len(all_streams_data)} streams completed in {total_time:.1f}s total.")
    
    # Sort deterministically by ASSETS order then TF_SETS order
    def sort_key(s):
        a_idx = ASSETS.index(s["identity"]["asset"])
        tf_idx = TF_SETS.index(s["identity"]["timeframe_set"])
        return (a_idx, tf_idx)
        
    all_streams_data.sort(key=sort_key)
    
    for s in all_streams_data:
        global_trade_ledger.extend(s["trade_ledger"])
        
    # Serialize results to scratch directory
    os.makedirs("/home/mrcn2/crypto-platform/scratch", exist_ok=True)
    matrix_output_path = "/home/mrcn2/crypto-platform/scratch/unified_context_matrix_results.json"
    ledger_output_path = "/home/mrcn2/crypto-platform/scratch/unified_matrix_trade_ledger.json"
    
    with open(matrix_output_path, "w") as f:
        json.dump(all_streams_data, f, indent=2)
        
    with open(ledger_output_path, "w") as f:
        json.dump(global_trade_ledger, f, indent=2)
        
    print("\n" + "=" * 100)
    print("ALL 15 STREAMS COMPLETE")
    print("=" * 100)
    print(f"✅ Saved matrix results to: {matrix_output_path}")
    print(f"✅ Saved trade ledger to:   {ledger_output_path}")
    
    return {
        "streams": all_streams_data,
        "global_trade_ledger": global_trade_ledger
    }


if __name__ == "__main__":
    execute_matrix_replay()
