"""
DAY 35 — GATE 2: Complete Economic Baseline Forensic & Setup Age Diagnostics
Reconstructs the 14-trade ledger, exit attribution, economic metrics, and 219 setup-age distribution.
"""

import sys
import os
import json
import math
import numpy as np
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


def extract_kz_timestamp(zone_id: str, default_ts: Optional[int] = None) -> Optional[int]:
    """Extracts timestamp embedded in zone_id like OB_BEARISH_OB_1598342400_SW_LOW_60 or FVG_BEARISH_1592971200_99."""
    if not zone_id:
        return default_ts
    parts = zone_id.split('_')
    for p in parts:
        if p.isdigit() and len(p) >= 9:
            try:
                return int(p)
            except ValueError:
                pass
    return default_ts


def main():
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

    _htf_cache = {"key": None, "state": None}
    _mtf_cache = {"key": None, "state": None}

    active_candidate: Optional[CandidateSetup] = None

    # Track creation timestamp of MTF keyzones mapped to candidates
    candidate_kz_creation_map: Dict[str, int] = {}
    geometrically_valid_candidates: List[Dict[str, Any]] = []

    for i in range(min_lookback_bars, len(ltf_candles)):
        current_bar = ltf_candles[i]
        decision_timestamp = current_bar.timestamp

        # Process orders in execution simulator
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
        is_long_obs = bias == DirectionalPermission.PERMIT_LONG
        phase_str = str(getattr(htf_state, 'phase_state', ''))
        is_pullback = "PULLBACK" in phase_str

        # Find HTF interacting KeyZone
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

        # Candidate Creation
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

        if active_candidate is not None:
            cand_is_long = active_candidate.directional_permission == DirectionalPermission.PERMIT_LONG
            pre_state = active_candidate.state

            # Track MTF keyzone creation timestamp during WAIT_MTF_RETEST
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

                for kz in causal_zones:
                    is_mitigated = "MITIGATED" in str(getattr(kz, 'status', ''))
                    high_bound = getattr(kz, 'high_boundary', getattr(kz, 'high', None))
                    low_bound = getattr(kz, 'low_boundary', getattr(kz, 'low', None))
                    price_in_zone = False
                    if high_bound is not None and low_bound is not None:
                        if mtf_state.current_candle:
                            price_in_zone = (mtf_state.current_candle.low <= high_bound and mtf_state.current_candle.high >= low_bound)
                        else:
                            price_in_zone = (low_bound <= mtf_state.current_price <= high_bound)
                    if is_mitigated or price_in_zone:
                        cand_kz_ts = getattr(kz, 'creation_timestamp', None) or extract_kz_timestamp(getattr(kz, 'zone_id', ''))
                        if cand_kz_ts:
                            candidate_kz_creation_map[active_candidate.candidate_id] = cand_kz_ts
                        break

            # Evaluate hypothesis
            plan = hypothesis.evaluate(active_candidate, htf_state, mtf_state, ltf_state)

            if plan is not None:
                # Terminal state reached
                # Check if geometrically valid
                if plan.rejection_reason not in ["REJECT_INVALID_ANCHOR_GEOMETRY", "REJECT_MISSING_STRUCTURAL_ANCHORS"]:
                    kz_creation_ts = candidate_kz_creation_map.get(active_candidate.candidate_id)
                    if not kz_creation_ts:
                        kz_creation_ts = extract_kz_timestamp(active_candidate.mtf_keyzone_id, default_ts=active_candidate.mtf_alignment_timestamp)

                    age_seconds = (decision_timestamp - kz_creation_ts) if (kz_creation_ts and kz_creation_ts > 0) else None

                    geom_cand = {
                        "candidate_id": active_candidate.candidate_id,
                        "timestamp": decision_timestamp,
                        "timestamp_str": format_ts(decision_timestamp),
                        "direction": plan.directional_permission,
                        "entry_price": plan.entry_price,
                        "stop_price": plan.stop_invalidation_price,
                        "target_price": plan.target_price,
                        "raw_rr": plan.raw_rr,
                        "rejection_reason": plan.rejection_reason,
                        "mtf_alignment_timestamp": active_candidate.mtf_alignment_timestamp,
                        "mtf_keyzone_id": active_candidate.mtf_keyzone_id,
                        "mtf_kz_creation_ts": kz_creation_ts,
                        "setup_age_seconds": age_seconds,
                        "setup_age_hours": (age_seconds / 3600.0) if age_seconds is not None else None,
                        "setup_age_days": (age_seconds / 86400.0) if age_seconds is not None else None,
                    }
                    geometrically_valid_candidates.append(geom_cand)

                    # If RR >= 4.0, evaluate risk
                    if plan.status == CandidateState.ENTERED.value:
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

            # Cycle management
            if active_candidate and active_candidate.state in [CandidateState.REJECTED, CandidateState.EXPIRED, CandidateState.ENTERED]:
                active_candidate = None

    # Step 2: Extract the closed trades
    closed_trades = ledger.closed_trades

    trade_ledger_reconstruction: List[Dict[str, Any]] = []
    cumulative_r = 0.0
    running_equity = 10000.0
    peak_equity = 10000.0

    for idx, t in enumerate(closed_trades, 1):
        r_realized = t.realized_rr if t.realized_rr is not None else 0.0
        cumulative_r += r_realized
        running_equity += t.realized_pnl if t.realized_pnl is not None else 0.0
        if running_equity > peak_equity:
            peak_equity = running_equity
        drawdown_pct = ((peak_equity - running_equity) / peak_equity * 100.0) if peak_equity > 0 else 0.0

        rec = {
            "trade_num": idx,
            "trade_id": t.trade_id,
            "entry_timestamp": t.entry_timestamp,
            "entry_timestamp_str": format_ts(t.entry_timestamp) if t.entry_timestamp else "N/A",
            "direction": t.directional_permission,
            "entry_price": round(t.fill_entry_price, 2),
            "initial_sl": round(t.initial_stop_price, 2),
            "htf_tp": round(t.target_price, 2),
            "mtf_trailing_state": "TRAILED" if abs(t.current_stop_price - t.initial_stop_price) > 1e-4 else "INITIAL_SL",
            "exit_timestamp": t.exit_timestamp,
            "exit_timestamp_str": format_ts(t.exit_timestamp) if t.exit_timestamp else "N/A",
            "exit_price": round(t.exit_price, 2) if t.exit_price is not None else None,
            "exit_reason": t.exit_reason,
            "dollar_risk": round(t.dollar_risk, 2),
            "realized_pnl": round(t.realized_pnl, 2) if t.realized_pnl is not None else 0.0,
            "realized_r": round(r_realized, 2),
            "cumulative_r": round(cumulative_r, 2),
            "running_equity": round(running_equity, 2),
            "drawdown_pct": round(drawdown_pct, 2)
        }
        trade_ledger_reconstruction.append(rec)

    # Step 3: Exit Attribution
    categories = ["HTF_TP", "MTF_STRUCTURAL_TRAIL", "INITIAL_LTF_SL"]
    exit_attribution = {}
    for cat in categories:
        matching = [t for t in closed_trades if t.exit_reason == cat]
        count = len(matching)
        pct = (count / len(closed_trades) * 100.0) if closed_trades else 0.0
        r_list = [t.realized_rr for t in matching if t.realized_rr is not None]
        avg_r = float(np.mean(r_list)) if r_list else 0.0
        med_r = float(np.median(r_list)) if r_list else 0.0
        exit_attribution[cat] = {
            "count": count,
            "percentage": round(pct, 2),
            "average_r": round(avg_r, 2),
            "median_r": round(med_r, 2),
            "r_multiples": [round(r, 2) for r in r_list]
        }

    # Step 4: Economic Metrics
    r_multiples = [t.realized_rr for t in closed_trades if t.realized_rr is not None]
    pnls = [t.realized_pnl for t in closed_trades if t.realized_pnl is not None]
    wins = [r for r in r_multiples if r > 0]
    losses = [r for r in r_multiples if r < 0]
    win_rate = len(wins) / len(closed_trades) if closed_trades else 0.0
    avg_r = float(np.mean(r_multiples)) if r_multiples else 0.0
    median_r = float(np.median(r_multiples)) if r_multiples else 0.0
    avg_win_r = float(np.mean(wins)) if wins else 0.0
    avg_loss_r = float(np.mean([abs(l) for l in losses])) if losses else 0.0
    loss_rate = len(losses) / len(closed_trades) if closed_trades else 0.0
    expectancy_r = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)
    gross_profit = sum([p for p in pnls if p > 0])
    gross_loss = abs(sum([p for p in pnls if p < 0]))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else ("INFINITE" if gross_profit > 0 else 0.0)

    # Max consecutive losses
    max_consec_losses = 0
    curr_consec = 0
    for r in r_multiples:
        if r < 0:
            curr_consec += 1
            if curr_consec > max_consec_losses:
                max_consec_losses = curr_consec
        else:
            curr_consec = 0

    max_dd = ledger.max_drawdown_pct * 100.0

    economic_metrics = {
        "total_trades": len(closed_trades),
        "win_rate_pct": round(win_rate * 100.0, 2),
        "loss_rate_pct": round(loss_rate * 100.0, 2),
        "average_r": round(avg_r, 2),
        "median_r": round(median_r, 2),
        "expectancy_r": round(expectancy_r, 2),
        "profit_factor": round(profit_factor, 2) if isinstance(profit_factor, float) else profit_factor,
        "maximum_drawdown_pct": round(max_dd, 2),
        "max_consecutive_losses": max_consec_losses,
        "cumulative_r": round(cumulative_r, 2),
        "gross_profit_usd": round(gross_profit, 2),
        "gross_loss_usd": round(gross_loss, 2),
        "net_pnl_usd": round(gross_profit - gross_loss, 2),
        "friction_model": {
            "maker_fee_rate": execution_simulator.maker_fee_rate,
            "taker_fee_rate": execution_simulator.taker_fee_rate,
            "slippage_bps": execution_simulator.slippage_bps,
            "description": "Limit entries and limit TP filled as Maker (0.00% fee, 0.00 bps slippage). Market Stop Loss orders filled as Taker (0.05% fee, 5.0 bps adverse slippage)."
        }
    }

    # Step 5: Setup Age Forensics for 219 Geometrically Valid Candidates
    ages_days = [c["setup_age_days"] for c in geometrically_valid_candidates if c["setup_age_days"] is not None]

    setup_age_metrics = {
        "sample_size": len(ages_days),
        "min_days": round(float(np.min(ages_days)), 2) if ages_days else 0.0,
        "median_days": round(float(np.median(ages_days)), 2) if ages_days else 0.0,
        "mean_days": round(float(np.mean(ages_days)), 2) if ages_days else 0.0,
        "p90_days": round(float(np.percentile(ages_days, 90)), 2) if ages_days else 0.0,
        "p95_days": round(float(np.percentile(ages_days, 95)), 2) if ages_days else 0.0,
        "max_days": round(float(np.max(ages_days)), 2) if ages_days else 0.0,
        "exceeding_counts": {
            "exceed_1_day": len([d for d in ages_days if d > 1.0]),
            "exceed_3_days": len([d for d in ages_days if d > 3.0]),
            "exceed_7_days": len([d for d in ages_days if d > 7.0]),
            "exceed_14_days": len([d for d in ages_days if d > 14.0]),
            "exceed_30_days": len([d for d in ages_days if d > 30.0]),
            "exceed_90_days": len([d for d in ages_days if d > 90.0]),
        },
        "exceeding_pct": {
            "exceed_1_day_pct": round(len([d for d in ages_days if d > 1.0]) / len(ages_days) * 100.0, 2) if ages_days else 0.0,
            "exceed_3_days_pct": round(len([d for d in ages_days if d > 3.0]) / len(ages_days) * 100.0, 2) if ages_days else 0.0,
            "exceed_7_days_pct": round(len([d for d in ages_days if d > 7.0]) / len(ages_days) * 100.0, 2) if ages_days else 0.0,
            "exceed_14_days_pct": round(len([d for d in ages_days if d > 14.0]) / len(ages_days) * 100.0, 2) if ages_days else 0.0,
            "exceed_30_days_pct": round(len([d for d in ages_days if d > 30.0]) / len(ages_days) * 100.0, 2) if ages_days else 0.0,
            "exceed_90_days_pct": round(len([d for d in ages_days if d > 90.0]) / len(ages_days) * 100.0, 2) if ages_days else 0.0,
        }
    }

    output_payload = {
        "trade_ledger_reconstruction": trade_ledger_reconstruction,
        "exit_attribution": exit_attribution,
        "economic_metrics": economic_metrics,
        "setup_age_metrics": setup_age_metrics,
        "geometrically_valid_candidates": geometrically_valid_candidates
    }

    with open("scratch/gate2_forensic_results.json", "w") as f:
        json.dump(output_payload, f, indent=2)

    print("\n" + "="*80)
    print("                     GATE 2 FORENSIC RESULTS SUMMARY                     ")
    print("="*80)
    print(json.dumps({
        "exit_attribution": exit_attribution,
        "economic_metrics": economic_metrics,
        "setup_age_metrics": setup_age_metrics
    }, indent=2))


if __name__ == "__main__":
    main()
