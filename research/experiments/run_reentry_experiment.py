"""
Product 04 — Research Laboratory: Root-Cause Re-Entry Experiment
A/B Empirical Evaluation of Competing Structural Re-Entry Hypotheses against Preserved Baseline.

Hypotheses Tested:
- VARIANT_0: Baseline Control (Unconstrained Lifespan)
- VARIANT_1: Keyzone Consumption (Exhausted zone cannot spawn repeated trades)
- VARIANT_2: Structural Invalidation Cooldown (K-bar MTF quiet period after stop-out)
- VARIANT_3: Fresh Structural Event Requirement (Must print new MTF BOS/CHOCH post-invalidation)
"""

import os
import sys
import time
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

from research.replayer.timeframe_aligner import TimeframeAligner, TIMEFRAME_DURATIONS_SEC
from research.replayer.causal_replayer import CausalReplayer
from research.simulation.trade_ledger import SimulatedTrade
from market_data.warehouse_loader import WarehouseLoader
from market_data.data_certifier import DataCertifier
from risk_engine.contracts.risk_config import RiskConfig
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.risk_coordinator import RiskCoordinator
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.classifiers.bias_classifier import BiasClassifier
from strategy_engine.context.htf_context_engine import HTFContextEngine, HTFContext
from strategy_engine.lifecycle.candidate_tracker import CandidateTracker, CandidateSetup
from strategy_engine.coordinator.strategy_coordinator import get_max_lifespan_seconds
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from research.experiments.experiment_schema import HypothesisSpec, ExperimentResult
from research.experiments.experiment_engine import ExperimentEngine


ASSETS = ["BTC", "ETH", "SOL"]
TF_SETS = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]


def run_stream_with_reentry_rule(
    asset: str,
    tf_set_id: str,
    variant_id: str,  # "BASELINE", "ZONE_CONSUMPTION", "COOLDOWN_6BARS", "FRESH_STRUCTURE"
    cooldown_bars: int = 6
) -> Dict[str, Any]:
    """
    Executes a single stream replay under an isolated re-entry hypothesis variant.
    """
    stream_id = f"{asset}_{tf_set_id}"
    symbol = f"{asset}/USDT"
    tf_set = TimeframeAligner.get_set(tf_set_id)
    
    ltf_start_time_ms = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end_time_ms = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    
    t0 = time.time()
    
    # Check SET_5 availability
    if tf_set_id == "SET_5":
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "market_data", "cache")
        binance_symbol = symbol.replace("/", "").upper()
        c_15m_file = os.path.join(cache_dir, f"binance_{binance_symbol}_15m.json")
        c_5m_file = os.path.join(cache_dir, f"binance_{binance_symbol}_5m.json")
        c_1m_file = os.path.join(cache_dir, f"binance_{binance_symbol}_1m.json")
        if not (os.path.exists(c_15m_file) and os.path.exists(c_5m_file) and os.path.exists(c_1m_file)):
            return {
                "stream_id": stream_id,
                "data": {"data_status": "INSUFFICIENT_HISTORY", "htf_candles": 35036, "mtf_candles": 0, "ltf_candles": 0},
                "performance": {
                    "total_trades": 0, "wins": 0, "losses": 0, "win_rate_pct": None,
                    "gross_realized_r": 0.0, "total_friction_r": 0.0, "net_realized_r": 0.0,
                    "expectancy_r": None, "net_pnl_usd": 0.0, "max_drawdown_pct": 0.0
                },
                "exit_attribution": {},
                "trade_ledger": []
            }

    try:
        htf_candles = WarehouseLoader.load_history(symbol, tf_set.htf, limit=1_000_000, start_time_ms=None, end_time_ms=end_time_ms)
        mtf_candles = WarehouseLoader.load_history(symbol, tf_set.mtf, limit=1_000_000, start_time_ms=None, end_time_ms=end_time_ms)
        ltf_candles = WarehouseLoader.load_history(symbol, tf_set.ltf, limit=1_000_000, start_time_ms=ltf_start_time_ms, end_time_ms=end_time_ms)
    except Exception as e:
        return {
            "stream_id": stream_id,
            "data": {"data_status": f"DATA_ERROR: {str(e)}", "htf_candles": 0, "mtf_candles": 0, "ltf_candles": 0},
            "performance": {
                "total_trades": 0, "wins": 0, "losses": 0, "win_rate_pct": None,
                "gross_realized_r": 0.0, "total_friction_r": 0.0, "net_realized_r": 0.0,
                "expectancy_r": None, "net_pnl_usd": 0.0, "max_drawdown_pct": 0.0
            },
            "exit_attribution": {},
            "trade_ledger": []
        }

    # Setup Causal Replayer
    risk_cfg = RiskConfig(max_risk_fraction=0.01, min_rr_floor=4.0, min_stop_distance_pct=0.001)
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

    hypothesis = UnifiedStrategy()
    candidate_tracker = CandidateTracker()
    
    # State tracking for re-entry hypotheses
    consumed_keyzones = set()
    last_stop_timestamp: Optional[int] = None
    last_invalidation_ts: Optional[int] = None

    mtf_bar_duration_sec = TIMEFRAME_DURATIONS_SEC.get(tf_set.mtf, 3600)
    cooldown_seconds = cooldown_bars * mtf_bar_duration_sec

    min_lookback_bars = 15
    if len(ltf_candles) < min_lookback_bars:
        return {
            "stream_id": stream_id,
            "data": {"data_status": "INSUFFICIENT_HISTORY", "htf_candles": len(htf_candles), "mtf_candles": len(mtf_candles), "ltf_candles": len(ltf_candles)},
            "performance": {
                "total_trades": 0, "wins": 0, "losses": 0, "win_rate_pct": None,
                "gross_realized_r": 0.0, "total_friction_r": 0.0, "net_realized_r": 0.0,
                "expectancy_r": None, "net_pnl_usd": 0.0, "max_drawdown_pct": 0.0
            },
            "exit_attribution": {},
            "trade_ledger": []
        }

    _htf_cache = {"key": None, "state": None}
    _mtf_cache = {"key": None, "state": None}

    # Replay Loop
    for i in range(min_lookback_bars, len(ltf_candles)):
        current_bar = ltf_candles[i]
        decision_ts = current_bar.timestamp
        
        # 1. Process simulated orders and check for stop-out events
        replayer.execution_simulator.process_candle(current_bar, replayer.ledger)
        
        # Check newly closed trades from ledger to update re-entry states
        for trade in replayer.ledger.closed_trades:
            if trade.exit_timestamp == decision_ts:
                if trade.exit_reason == "INITIAL_LTF_SL":
                    last_stop_timestamp = decision_ts
                    last_invalidation_ts = decision_ts
                    # If Variant 1: consume keyzone
                    kz_id = trade.metadata.get("structural_provenance", {}).get("mtf_keyzone_id") if trade.metadata else None
                    if kz_id:
                        consumed_keyzones.add(kz_id)

        # 2. Extract visible slices
        ltf_slice = ltf_candles[max(0, i - 150):i + 1]
        mtf_slice = TimeframeAligner.filter_visible_candles(mtf_candles, decision_ts, tf_set.mtf, buffer_size=100)
        htf_slice = TimeframeAligner.filter_visible_candles(htf_candles, decision_ts, tf_set.htf, buffer_size=80)
        
        if len(htf_slice) < 5 or len(mtf_slice) < 5 or len(ltf_slice) < 5:
            continue

        # 3. Compute Market State with caching
        htf_key = htf_slice[-1].timestamp if htf_slice else None
        if _htf_cache["key"] != htf_key:
            htf_state = replayer.language_coordinator.run(htf_slice, symbol=symbol, timeframe=tf_set.htf)
            _htf_cache = {"key": htf_key, "state": htf_state}
        else:
            htf_state = _htf_cache["state"]

        mtf_key = mtf_slice[-1].timestamp if mtf_slice else None
        if _mtf_cache["key"] != mtf_key:
            mtf_state = replayer.language_coordinator.run(mtf_slice, symbol=symbol, timeframe=tf_set.mtf)
            _mtf_cache = {"key": mtf_key, "state": mtf_state}
        else:
            mtf_state = _mtf_cache["state"]

        ltf_state = replayer.language_coordinator.run(ltf_slice, symbol=symbol, timeframe=tf_set.ltf)

        # 4. Trailing Stops on active trades
        if replayer.enable_mtf_trailing:
            for t_id, active_plan in replayer.strategy_coordinator.active_manager.active_trades.items():
                replayer.ledger.update_trailing_stop(t_id, active_plan.stop_invalidation_price)
        replayer.strategy_coordinator.active_manager.evaluate(htf_state, mtf_state, ltf_state)

        # 5. Candidate Opportunity Lifecycle
        bias = BiasClassifier.evaluate(htf_state)
        htf_context: HTFContext = HTFContextEngine.evaluate(htf_state)
        phase_str = str(htf_state.phase_state) if htf_state.phase_state is not None else ""
        max_lifespan = get_max_lifespan_seconds(mtf_state.timeframe)
        
        active_candidates = candidate_tracker.get_active_candidates(symbol, "UNIFIED_STRATEGY")
        
        # Check Re-entry Constraints for Spawning New Candidate
        can_spawn = (not active_candidates) and (bias != DirectionalPermission.NO_TRADE)
        
        if can_spawn:
            if variant_id == "COOLDOWN_6BARS" and last_stop_timestamp:
                if (decision_ts - last_stop_timestamp) < cooldown_seconds:
                    can_spawn = False
                    
            elif variant_id == "FRESH_STRUCTURE" and last_invalidation_ts:
                mtf_events = getattr(mtf_state.structure_state, 'events', None) or mtf_state.events or []
                latest_ev_ts = max([getattr(ev, 'timestamp', 0) for ev in mtf_events], default=0)
                if latest_ev_ts <= last_invalidation_ts:
                    can_spawn = False

        if can_spawn:
            is_bullish = htf_state.trend_state.value == "BULLISH" if hasattr(htf_state.trend_state, 'value') else str(htf_state.trend_state) == "BULLISH"
            
            # Keyzone check
            htf_kz = None
            for kz in (htf_state.keyzones or []):
                kz_type_str = str(getattr(kz, 'zone_type', ''))
                if is_bullish and ("BULLISH" not in kz_type_str): continue
                if (not is_bullish) and ("BEARISH" not in kz_type_str): continue
                if "MITIGATED" in str(getattr(kz, 'status', '')):
                    htf_kz = kz
                    break
                    
            htf_ctx_label = "PULLBACK" if ("PULLBACK" in phase_str or (htf_kz is not None and "PULLBACK" in phase_str)) else "CONTINUATION"
            
            new_cand = CandidateSetup(
                candidate_id=f"cand_{symbol}_{variant_id}_{decision_ts}",
                hypothesis_id="UNIFIED_STRATEGY",
                symbol=symbol,
                htf=htf_state.timeframe,
                mtf=mtf_state.timeframe,
                ltf=ltf_state.timeframe,
                state=CandidateState.WAIT_MTF_ALIGNMENT,
                directional_permission=DirectionalPermission.PERMIT_LONG if is_bullish else DirectionalPermission.PERMIT_SHORT,
                htf_context=htf_ctx_label,
                htf_context_id=htf_context.context_id,
                htf_context_timestamp=htf_context.timestamp,
                htf_macro_direction=htf_state.trend_state.value if hasattr(htf_state.trend_state, 'value') else str(htf_state.trend_state),
                htf_phase=str(htf_state.phase_state),
                htf_target_price=htf_context.target_anchor_price,
                htf_keyzone_id=getattr(htf_kz, 'zone_id', None) if htf_kz else None,
                htf_interaction_timestamp=htf_state.timestamp if htf_kz else None,
                creation_timestamp=decision_ts,
                max_lifespan_seconds=max_lifespan
            )
            candidate_tracker.add_candidate(new_cand)

        # 6. Progress active candidates
        for cand in candidate_tracker.get_active_candidates(symbol, "UNIFIED_STRATEGY"):
            # If Variant 1: Check if candidate aligned with a consumed keyzone
            if variant_id == "ZONE_CONSUMPTION" and cand.mtf_keyzone_id in consumed_keyzones:
                candidate_tracker.remove_candidate(cand.candidate_id)
                continue
                
            plan = hypothesis.evaluate(cand, htf_state, mtf_state, ltf_state)
            if plan:
                candidate_tracker.remove_candidate(cand.candidate_id)
                
                # Check Keyzone Consumption upon alignment
                if variant_id == "ZONE_CONSUMPTION" and cand.mtf_keyzone_id in consumed_keyzones:
                    continue
                    
                if plan.status == CandidateState.ENTERED.value:
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
                        replayer.strategy_coordinator.active_manager.register_trade(plan.trade_plan_id, plan)

    # 7. Close remaining open trades at simulation boundary
    final_bar = ltf_candles[-1]
    for trade in replayer.ledger.get_active_trades():
        replayer.execution_simulator.exit_trade(trade, final_bar.close, final_bar.timestamp, "SIMULATION_END", replayer.ledger)

    closed_trades = replayer.ledger.closed_trades
    pnls = [t.realized_pnl for t in closed_trades if t.realized_pnl is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    
    gross_realized_r = sum(t.realized_rr for t in closed_trades if t.realized_rr is not None)
    friction_r_total = 0.0
    net_realized_r = 0.0
    
    for t in closed_trades:
        fric_usd = t.total_friction_usd
        fric_r = (fric_usd / t.dollar_risk) if t.dollar_risk > 0 else 0.0
        friction_r_total += fric_r
        nr_r = (t.realized_rr - fric_r) if t.realized_rr is not None else 0.0
        net_realized_r += nr_r
        
    net_pnl = sum(pnls)
    n_trades = len(closed_trades)
    wr_pct = round((len(wins) / n_trades) * 100.0, 2) if n_trades > 0 else None
    exp_r = round(net_realized_r / n_trades, 4) if n_trades > 0 else None
    
    exit_attr = {}
    for t in closed_trades:
        reason = t.exit_reason or "UNKNOWN"
        exit_attr[reason] = exit_attr.get(reason, 0) + 1
        
    return {
        "stream_id": stream_id,
        "variant_id": variant_id,
        "data": {"data_status": "CERTIFIED", "htf_candles": len(htf_candles), "mtf_candles": len(mtf_candles), "ltf_candles": len(ltf_candles)},
        "performance": {
            "total_trades": n_trades,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": wr_pct,
            "gross_realized_r": round(gross_realized_r, 4),
            "total_friction_r": round(friction_r_total, 4),
            "net_realized_r": round(net_realized_r, 4),
            "expectancy_r": exp_r,
            "net_pnl_usd": round(net_pnl, 2),
            "max_drawdown_pct": round(replayer.ledger.max_drawdown_pct, 2)
        },
        "exit_attribution": exit_attr,
        "trade_ledger": [t.to_dict() for t in closed_trades]
    }


def execute_full_reentry_study():
    """
    Executes the comprehensive A/B Re-Entry study across all 4 variants.
    """
    print("=" * 100)
    print("PHASE 4: CAUSAL RE-ENTRY A/B RESEARCH STUDY (COMPARING 4 HYPOTHESIS VARIANTS)")
    print("=" * 100)
    
    variants = [
        ("VARIANT_0_BASELINE", "BASELINE", "Unconstrained re-entry within active lifespan (Control)"),
        ("VARIANT_1_ZONE_CONSUMPTION", "ZONE_CONSUMPTION", "MTF Keyzone is consumed upon initial SL; cannot spawn repeat entries"),
        ("VARIANT_2_COOLDOWN_6B", "COOLDOWN_6BARS", "6 MTF bar quiet period post-invalidation before new setups permitted"),
        ("VARIANT_3_FRESH_STRUCTURE", "FRESH_STRUCTURE", "Requires newly formed MTF BOS/CHOCH post-invalidation")
    ]
    
    study_results = {}
    
    for v_name, v_code, v_desc in variants:
        print(f"\n🔬 Running Replay Matrix for: {v_name}...")
        print(f"   Hypothesis: {v_desc}")
        
        stream_tasks = []
        for asset in ASSETS:
            for tf_set_id in TF_SETS:
                stream_tasks.append((asset, tf_set_id, v_code))
                
        stream_results = []
        with ProcessPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(run_stream_with_reentry_rule, a, tf, v): (a, tf)
                for (a, tf, v) in stream_tasks
            }
            for future in as_completed(futures):
                stream_results.append(future.result())
                
        # Sort streams consistently
        def sort_key(s):
            a_idx = ASSETS.index(s["stream_id"].split("_")[0])
            tf_idx = TF_SETS.index(s["stream_id"].split("_", 1)[1])
            return (a_idx, tf_idx)
            
        stream_results.sort(key=sort_key)
                
        spec = HypothesisSpec(
            hypothesis_id=v_name,
            hypothesis_name=v_name,
            mechanism_description=v_desc,
            variable_under_test=v_code,
            falsification_criteria={"min_trades": 5, "min_expectancy_r": -0.20, "require_better_net_r": False}
        )
        
        exp_res = ExperimentEngine.run_experiment(spec, stream_results)
        study_results[v_name] = exp_res
        
    print("\n" + "=" * 100)
    print("A/B EXPERIMENT COMPARISON SUMMARY (ACROSS 15 STREAMS)")
    print("=" * 100)
    print(f"| {'Variant Name':28s} | {'Trades':6s} | {'Wins':4s} | {'Losses':6s} | {'Win Rate':8s} | {'Net Realized R':14s} | {'Expectancy R':12s} | {'Net PnL ($)':11s} | {'Decision':16s} |")
    print("|" + "-" * 30 + "|" + "-" * 8 + "|" + "-" * 6 + "|" + "-" * 8 + "|" + "-" * 10 + "|" + "-" * 16 + "|" + "-" * 14 + "|" + "-" * 13 + "|" + "-" * 18 + "|")
    
    for v_name, res in study_results.items():
        tm = res.treatment_metrics
        wr_str = f"{tm['win_rate_pct']:.1f}%" if tm['win_rate_pct'] is not None else "  N/A  "
        exp_str = f"{tm['expectancy_r']:+.4f}R" if tm['expectancy_r'] is not None else "    N/A     "
        print(f"| {v_name:28s} | {tm['total_trades']:6d} | {tm['wins']:4d} | {tm['losses']:6d} | {wr_str:8s} | {tm['net_realized_r']:+13.4f}R | {exp_str:12s} | ${tm['net_pnl_usd']:+10.2f} | {res.decision:16s} |")

    # Save complete study report
    report_file = "/home/mrcn2/crypto-platform/scratch/reentry_ab_study_results.json"
    with open(report_file, "w") as f:
        json.dump({k: v.to_dict() for k, v in study_results.items()}, f, indent=2)
        
    print(f"\n✅ Full A/B Study Report saved to: {report_file}")


if __name__ == "__main__":
    execute_full_reentry_study()
