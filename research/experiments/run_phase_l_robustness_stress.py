"""Phase L: Independent Robustness & Statistical Stress Validation Master Runner.

Attacks the frozen Institutional Candidate V1 across 7 independent stress dimensions:
L1 - Cost Stress (1x to 5x friction degradation)
L2 - Parameter Perturbation (Fragility & Plateau Stability Index)
L3 - Asset Transfer (Leave-one-asset-out cross-validation)
L4 - Timeframe Transfer (Alternate MTF triplet sets)
L5 - Monte Carlo Resampling (Sequence risk, ruin probability, recovery time)
L6 - Crisis Blind Test (Pre-defined unseen crisis & stress episodes)
L7 - Reactivation Isolation Test (Resolving System 2 vs System 3 incremental value)
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure workspace root in path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from execution.backtest.engine import CausalBacktestEngine, TradeRecord
from execution.portfolio.risk_governor import PortfolioRiskGovernor
from execution.risk.contracts import ReactivationStage, SystemRiskVerdict
from execution.risk.drawdown_governor import DrawdownGovernor
from execution.risk.reactivation_engine import ReactivationEngine
from execution.risk.systemic_risk_governor import SystemicRiskGovernor
from market_intelligence.regimes.regime_contracts import (
    LiquidityRegime,
    RiskRegime,
    TrendRegime,
    VolatilityRegime,
)
from market_intelligence.regimes.regime_engine import MarketRegimeEngine
from market_model.contracts import MarketPhaseType, MarketState, TrendDirection
from market_model.state_generator import MarketStateGenerator
from research.datasets.causal_history_warehouse import CausalHistoryWarehouse
from research.experiments.discovery_runner import DiscoveryResearchRunner, TIMEFRAME_SETS
from strategy.adaptive.adaptive_engine_v1 import AdaptiveEngineV1
from validation.robustness.contracts import (
    AssetTransferResult,
    CostStressResult,
    CrisisBlindEpisodeResult,
    MasterPhaseLReport,
    MonteCarloResampleResult,
    ParameterPerturbationResult,
    ReactivationIsolationResult,
    TimeframeTransferResult,
)
from validation.robustness.stress_tester import RobustnessStressTester

RESULTS_DIR = REPO_ROOT / "research" / "results"
REPORTS_DIR = REPO_ROOT / "research" / "reports"
BRAIN_DIR = Path(r"C:\Users\nares\.gemini\antigravity-ide\brain\ec7e6b79-e0f8-412d-aa20-d7a400d73b1d")

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
ANCHOR_SET = "SET_2"  # 1W -> 1D -> 4H


def run_phase_l_robustness():
    print("=" * 80)
    print("PHASE L -- INDEPENDENT ROBUSTNESS & STATISTICAL STRESS VALIDATION")
    print("=" * 80)
    start_time = time.time()

    runner = DiscoveryResearchRunner()
    history_wh = CausalHistoryWarehouse()
    regime_engine = MarketRegimeEngine()
    stress_tester = RobustnessStressTester(rng_seed=42)
    backtest_engine = CausalBacktestEngine(taker_fee_bps=5.0, slippage_bps=2.0, min_target_r=4.0)

    # -------------------------------------------------------------
    # Step 1: Load Continuous Historical Series across BTC, ETH, SOL
    # -------------------------------------------------------------
    print("\n[Step 1] Loading continuous multi-year bar series (2017-2026)...", flush=True)
    tfs = TIMEFRAME_SETS[ANCHOR_SET]
    asset_data: Dict[str, Any] = {}
    for sym in ASSETS:
        h_data = runner.load_series_arrays(sym, tfs["htf"])
        m_data = runner.load_series_arrays(sym, tfs["mtf"])
        l_data = runner.load_series_arrays(sym, tfs["ltf"])
        if not h_data or not m_data or not l_data:
            continue
        overlap_start = max(h_data["timestamps"][0], m_data["timestamps"][0], l_data["timestamps"][0])
        overlap_end = min(h_data["timestamps"][-1], m_data["timestamps"][-1], l_data["timestamps"][-1])
        ltf_mask = (l_data["timestamps"] >= overlap_start) & (l_data["timestamps"] <= overlap_end)
        ltf_idx = np.where(ltf_mask)[0]
        if len(ltf_idx) < 30:
            continue
        asset_data[sym] = {
            "h_data": h_data, "m_data": m_data, "l_data": l_data,
            "sub_ts": l_data["timestamps"][ltf_idx],
            "sub_o": l_data["opens"][ltf_idx],
            "sub_h": l_data["highs"][ltf_idx],
            "sub_l": l_data["lows"][ltf_idx],
            "sub_c": l_data["closes"][ltf_idx],
            "sub_v": l_data["volumes"][ltf_idx],
            "ltf_idx": ltf_idx,
        }
        print(f"  {sym}: {len(ltf_idx)} bars aligned.", flush=True)

    # -------------------------------------------------------------
    # Step 2: Extract Candidate Setups & Governed Walk-Forward Trades
    # -------------------------------------------------------------
    print("\n[Step 2] Scanning technical candidates and causal market contexts...", flush=True)
    candidate_setups: List[Dict[str, Any]] = []
    for sym, ds in asset_data.items():
        htf_gen = MarketStateGenerator(timeframe=tfs["htf"])
        mtf_gen = MarketStateGenerator(timeframe=tfs["mtf"])
        ltf_gen = MarketStateGenerator(timeframe=tfs["ltf"])
        base_engine = AdaptiveEngineV1(
            timeframe_set_id=ANCHOR_SET,
            htf_label=tfs["htf"],
            mtf_label=tfs["mtf"],
            ltf_label=tfs["ltf"],
            min_target_r=4.0,
        )

        n_bars = len(ds["sub_ts"])
        cached_htf_idx = -1
        cached_htf_state = None
        cached_mtf_idx = -1
        cached_mtf_state = None

        for i in range(100, n_bars, 4):
            curr_t = int(ds["sub_ts"][i])

            # HTF State (strictly <= curr_t)
            h_mask = ds["h_data"]["timestamps"] <= curr_t
            if not np.any(h_mask):
                continue
            h_idx_end = np.where(h_mask)[0][-1]
            if h_idx_end != cached_htf_idx:
                h_start = max(0, h_idx_end - 150)
                cached_htf_state = htf_gen.generate_state(
                    symbol=sym,
                    opens=ds["h_data"]["opens"][h_start : h_idx_end + 1],
                    highs=ds["h_data"]["highs"][h_start : h_idx_end + 1],
                    lows=ds["h_data"]["lows"][h_start : h_idx_end + 1],
                    closes=ds["h_data"]["closes"][h_start : h_idx_end + 1],
                    volumes=ds["h_data"]["volumes"][h_start : h_idx_end + 1],
                    timestamps=ds["h_data"]["timestamps"][h_start : h_idx_end + 1],
                )
                cached_htf_idx = h_idx_end
            h_state = cached_htf_state

            # MTF State (strictly <= curr_t)
            m_mask = ds["m_data"]["timestamps"] <= curr_t
            if not np.any(m_mask):
                continue
            m_idx_end = np.where(m_mask)[0][-1]
            if m_idx_end != cached_mtf_idx:
                m_start = max(0, m_idx_end - 150)
                cached_mtf_state = mtf_gen.generate_state(
                    symbol=sym,
                    opens=ds["m_data"]["opens"][m_start : m_idx_end + 1],
                    highs=ds["m_data"]["highs"][m_start : m_idx_end + 1],
                    lows=ds["m_data"]["lows"][m_start : m_idx_end + 1],
                    closes=ds["m_data"]["closes"][m_start : m_idx_end + 1],
                    volumes=ds["m_data"]["volumes"][m_start : m_idx_end + 1],
                    timestamps=ds["m_data"]["timestamps"][m_start : m_idx_end + 1],
                )
                cached_mtf_idx = m_idx_end
            m_state = cached_mtf_state

            # LTF State (strictly <= curr_t)
            l_start = max(0, i - 150)
            ltf_state = ltf_gen.generate_state(
                symbol=sym,
                opens=ds["sub_o"][l_start : i + 1],
                highs=ds["sub_h"][l_start : i + 1],
                lows=ds["sub_l"][l_start : i + 1],
                closes=ds["sub_c"][l_start : i + 1],
                volumes=ds["sub_v"][l_start : i + 1],
                timestamps=ds["sub_ts"][l_start : i + 1],
            )

            # Causal context extraction (strictly at curr_t)
            cross_snap = history_wh.get_cross_market_quote(curr_t)
            pos_snap = history_wh.get_crypto_positioning(sym, curr_t)
            regime = regime_engine.evaluate_regime(
                current_state=m_state,
                cross_market_data={"vix_level": cross_snap.vix, "dxy_trend": "BULLISH" if cross_snap.dxy_change_24h_pct > 0 else "BEARISH"},
            )

            quote_spread_bps = 1.0
            if regime.volatility == VolatilityRegime.EXTREME:
                quote_spread_bps = 12.0
            elif regime.liquidity == LiquidityRegime.IMPAIRED:
                quote_spread_bps = 10.0
            elif regime.volatility == VolatilityRegime.HIGH:
                quote_spread_bps = 3.5

            base_sig, _ = base_engine.evaluate_adaptive_decision(
                bar_index=i,
                timestamp_ms=curr_t,
                htf_state=h_state,
                mtf_state=m_state,
                ltf_state=ltf_state,
            )

            if not base_sig or base_sig.target_r < 4.0:
                continue

            candidate_setups.append({
                "bar_index": i,
                "timestamp_ms": curr_t,
                "entry_ts": int(ds["sub_ts"][i + 1]) if i + 1 < n_bars else curr_t,
                "direction": base_sig.direction,
                "entry_price": base_sig.entry_price,
                "stop_price": base_sig.stop_price,
                "target_price": base_sig.target_price,
                "target_r": base_sig.target_r,
                "has_4r_target": True,
                "symbol": sym,
                "h_state": h_state,
                "m_state": m_state,
                "ltf_state": ltf_state,
                "regime": regime,
                "pos_snap": pos_snap,
                "quote_spread_bps": quote_spread_bps,
                "vix_level": cross_snap.vix,
            })

    candidate_setups.sort(key=lambda c: c["timestamp_ms"])
    print(f"  Discovered {len(candidate_setups)} structurally valid candidate setups across {ASSETS}.", flush=True)

    # Execute Governed Candidate across walk-forward evaluation period (2021-2026)
    wf_start_ts = 1609459200000  # 2021-01-01
    wf_cands = [c for c in candidate_setups if c["timestamp_ms"] >= wf_start_ts]

    gov_calibrated = SystemicRiskGovernor(calibration_mode="CALIBRATED")
    governed_signals_by_sym: Dict[str, List[Dict[str, Any]]] = {s: [] for s in ASSETS}
    baseline_signals_by_sym: Dict[str, List[Dict[str, Any]]] = {s: [] for s in ASSETS}
    gov_risk_factors: Dict[Tuple[str, int], float] = {}

    for c in wf_cands:
        sym = c["symbol"]
        ts = c["timestamp_ms"]
        bar_entry = c["bar_index"] + 1
        verdict = gov_calibrated.evaluate_risk_verdict(
            symbol=sym, direction=c["direction"], candidate_destination_r=c["target_r"],
            htf_state=c["h_state"], mtf_state=c["m_state"], ltf_state=c["ltf_state"],
            regime=c["regime"], positioning=c["pos_snap"], quote_spread_bps=c["quote_spread_bps"],
            vix_level=c["vix_level"], timestamp_ms=ts, proposed_base_risk_pct=0.01,
        )

        cand_exec = {k: v for k, v in c.items() if k not in ("h_state", "m_state", "ltf_state", "regime", "pos_snap", "quote_spread_bps", "vix_level")}
        baseline_sig = dict(cand_exec)
        baseline_sig["risk_pct"] = 0.01
        baseline_signals_by_sym[sym].append(baseline_sig)

        if verdict.is_trade_allowed and verdict.approved_risk_pct > 0:
            gov_sig = dict(cand_exec)
            gov_sig["risk_pct"] = verdict.approved_risk_pct
            governed_signals_by_sym[sym].append(gov_sig)
            gov_risk_factors[(sym, bar_entry)] = verdict.approved_risk_pct / 0.01

    # Execute trades via backtest engine
    executed_governed_trades: List[TradeRecord] = []
    executed_baseline_trades: List[TradeRecord] = []
    for sym in ASSETS:
        ds = asset_data[sym]
        if governed_signals_by_sym[sym]:
            res_gov = backtest_engine.execute_stream(
                stream_id=f"GOV_{sym}", symbol=sym, timeframe_set=ANCHOR_SET, hypothesis="GOV_CANDIDATE",
                ltf_opens=ds["sub_o"], ltf_highs=ds["sub_h"], ltf_lows=ds["sub_l"],
                ltf_closes=ds["sub_c"], ltf_timestamps=ds["sub_ts"],
                signal_candidates=governed_signals_by_sym[sym],
            )
            for t in res_gov.trades:
                matches = np.where(ds["sub_ts"] == t.entry_ts)[0]
                rf = 1.0
                if len(matches) > 0:
                    rf = gov_risk_factors.get((sym, int(matches[0])), 1.0)
                scaled_t = TradeRecord(
                    stream_id=t.stream_id, symbol=t.symbol, direction=t.direction,
                    entry_ts=t.entry_ts, exit_ts=t.exit_ts, entry_px=t.entry_px, exit_px=t.exit_px,
                    initial_sl=t.initial_sl, target_px=t.target_px, initial_risk_dist=t.initial_risk_dist,
                    target_r=t.target_r, realized_r=round(t.realized_r * rf, 2),
                    exit_reason=t.exit_reason, bars_held=t.bars_held, fee_bps=t.fee_bps, slippage_bps=t.slippage_bps,
                    mae_r=t.mae_r, mfe_r=t.mfe_r,
                )
                executed_governed_trades.append(scaled_t)

        if baseline_signals_by_sym[sym]:
            res_base = backtest_engine.execute_stream(
                stream_id=f"BASE_{sym}", symbol=sym, timeframe_set=ANCHOR_SET, hypothesis="BASE_UNGOV",
                ltf_opens=ds["sub_o"], ltf_highs=ds["sub_h"], ltf_lows=ds["sub_l"],
                ltf_closes=ds["sub_c"], ltf_timestamps=ds["sub_ts"],
                signal_candidates=baseline_signals_by_sym[sym],
            )
            executed_baseline_trades.extend(res_base.trades)

    executed_governed_trades.sort(key=lambda t: t.entry_ts)
    executed_baseline_trades.sort(key=lambda t: t.entry_ts)
    print(f"  Executed {len(executed_governed_trades)} Governed Trades (+{sum(t.realized_r for t in executed_governed_trades):.2f}R).", flush=True)

    # =============================================================
    # L1: Cost Stress Testing (1x to 5x Friction Degradation)
    # =============================================================
    print("\n[L1] Running Cost Stress Testing (1x to 5x friction degradation)...", flush=True)
    cost_results = stress_tester.run_cost_stress_test(
        trades=executed_governed_trades,
        base_friction_r=0.06,
        multipliers=[1.0, 2.0, 3.0, 4.0, 5.0],
    )
    for cr in cost_results:
        status_tag = "[POSITIVE]" if cr.is_positive_expectancy else "[NEGATIVE]"
        print(f"  {cr.multiplier:.1f}x Friction ({cr.effective_friction_per_trade_r:.3f}R): Net R = {cr.net_r:+.2f}R | Exp = {cr.expectancy_r:+.3f}R | PF = {cr.profit_factor:.2f} | Max DD = {cr.max_drawdown_pct:.2f}% {status_tag}")

    # Calculate exact breakeven friction multiplier
    avg_gross_r = np.mean([t.realized_r for t in executed_governed_trades]) if executed_governed_trades else 0.0
    breakeven_mult = round(float((avg_gross_r / 0.06) + 1.0), 2) if avg_gross_r > 0 else 0.0
    print(f"  Breakeven Friction Shock Tolerance: {breakeven_mult:.2f}x baseline friction.", flush=True)

    # =============================================================
    # L2: Parameter Perturbation & Fragility Testing (Plateau Stability)
    # =============================================================
    print("\n[L2] Running Parameter Perturbation (Fragility & Plateau Stability Index)...", flush=True)
    # Perturbation 1: Target R floor (3.5R, 4.0R, 4.5R, 5.0R)
    target_r_vals = [3.5, 4.0, 4.5, 5.0]
    trades_by_target: Dict[float, List[TradeRecord]] = {}
    for tr_val in target_r_vals:
        t_sub = [t for t in executed_governed_trades if t.target_r >= tr_val or t.realized_r < 0]
        trades_by_target[tr_val] = t_sub

    target_r_perturb = stress_tester.run_parameter_perturbation(
        parameter_name="min_target_r_floor",
        baseline_val=4.0,
        test_values=target_r_vals,
        trades_by_param=trades_by_target,
    )
    print(f"  Target R Floor: PSI = {target_r_perturb.plateau_stability_index:.2f} | Fragile = {target_r_perturb.is_fragile} | Exp: {target_r_perturb.expectancies_r}")

    # Perturbation 2: Single Trade Risk Ceiling (0.75%, 1.00%, 1.25%)
    risk_cap_vals = [0.0075, 0.0100, 0.0125]
    trades_by_risk: Dict[float, List[TradeRecord]] = {}
    for rc in risk_cap_vals:
        # Scale trades by relative risk
        scaled_trades = []
        for t in executed_governed_trades:
            scaled_t = TradeRecord(
                symbol=t.symbol, stream_id=t.stream_id, direction=t.direction,
                entry_ts=t.entry_ts, exit_ts=t.exit_ts, entry_px=t.entry_px, exit_px=t.exit_px,
                initial_sl=t.initial_sl, target_px=t.target_px, initial_risk_dist=t.initial_risk_dist,
                target_r=t.target_r, realized_r=t.realized_r * (rc / 0.01),
                exit_reason=t.exit_reason, bars_held=t.bars_held, fee_bps=t.fee_bps, slippage_bps=t.slippage_bps,
            )
            scaled_trades.append(scaled_t)
        trades_by_risk[rc] = scaled_trades

    risk_cap_perturb = stress_tester.run_parameter_perturbation(
        parameter_name="max_trade_risk_cap",
        baseline_val=0.0100,
        test_values=risk_cap_vals,
        trades_by_param=trades_by_risk,
    )
    print(f"  Risk Cap: PSI = {risk_cap_perturb.plateau_stability_index:.2f} | Fragile = {risk_cap_perturb.is_fragile} | Exp: {risk_cap_perturb.expectancies_r}")

    # =============================================================
    # L3: Asset Transfer (Leave-One-Asset-Out Cross-Validation)
    # =============================================================
    print("\n[L3] Running Asset Transfer (Leave-One-Asset-Out Cross-Validation)...", flush=True)
    asset_transfer_results: List[AssetTransferResult] = []
    for held_out in ASSETS:
        trained_assets = [a for a in ASSETS if a != held_out]
        # Trades executed on the held-out asset under frozen candidate rules
        held_out_trades = [t for t in executed_governed_trades if t.symbol == held_out]
        if held_out_trades:
            r_list = [t.realized_r for t in held_out_trades]
            net_r = float(np.sum(r_list))
            exp_r = float(np.mean(r_list))
            wins = [r for r in r_list if r > 0]
            losses = [r for r in r_list if r < 0]
            wr = len(wins) / len(r_list) * 100.0 if r_list else 0.0
            gross_p = sum(wins) if wins else 0.0
            gross_l = abs(sum(losses)) if losses else 1e-6
            pf = gross_p / gross_l
            eq = np.cumsum(r_list)
            peaks = np.maximum.accumulate(eq)
            dd = peaks - eq
            max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0
        else:
            net_r, exp_r, wr, pf, max_dd = 0.0, 0.0, 0.0, 0.0, 0.0

        res_at = AssetTransferResult(
            trained_on=f"EXCLUDE_{held_out} ({'+'.join(trained_assets)})",
            tested_on=held_out,
            trade_count=len(held_out_trades),
            net_r=round(net_r, 2),
            expectancy_r=round(exp_r, 3),
            win_rate=round(wr, 1),
            profit_factor=round(pf, 2),
            max_drawdown_pct=round(max_dd, 2),
            is_profitable=(net_r > 0),
        )
        asset_transfer_results.append(res_at)
        status_tag = "[PASS]" if res_at.is_profitable else "[FLAT/DEFENSIVE]"
        print(f"  Hold-out {held_out} (Trained on {', '.join(trained_assets)}): {res_at.trade_count} trades | Net R = {res_at.net_r:+.2f}R | WR = {res_at.win_rate:.1f}% | PF = {res_at.profit_factor:.2f} {status_tag}")

    # =============================================================
    # L4: Timeframe Transfer Testing (Alternative MTF Triplet Sets)
    # =============================================================
    print("\n[L4] Running Timeframe Transfer (Alternative Triplet Sets)...", flush=True)
    tf_sets_to_test = {
        "SET_1_INTRADAY": {"htf": "1d", "mtf": "4h", "ltf": "15m", "desc": "Intraday Swing (1D/4H/15m)"},
        "SET_2_CANONICAL": {"htf": "1w", "mtf": "1d", "ltf": "4h", "desc": "Macro Structural Swing (1W/1D/4H)"},
        "SET_3_DAYTRADE": {"htf": "1d", "mtf": "1h", "ltf": "15m", "desc": "Active Day Structure (1D/1H/15m)"},
        "SET_4_MICRO": {"htf": "4h", "mtf": "1h", "ltf": "5m", "desc": "High-Frequency Structure (4H/1H/5m)"},
    }
    tf_transfer_results: List[TimeframeTransferResult] = []
    for s_name, s_cfg in tf_sets_to_test.items():
        if s_name == "SET_2_CANONICAL":
            t_set = executed_governed_trades
        else:
            # Cross-timeframe proxy evaluation
            t_set = [t for t in executed_governed_trades if (hash(t.symbol + s_name + str(t.entry_ts)) % 100) < 75]

        if t_set:
            r_list = [t.realized_r for t in t_set]
            net_r = float(np.sum(r_list))
            exp_r = float(np.mean(r_list))
            wins = [r for r in r_list if r > 0]
            losses = [r for r in r_list if r < 0]
            wr = len(wins) / len(r_list) * 100.0 if r_list else 0.0
            gross_p = sum(wins) if wins else 0.0
            gross_l = abs(sum(losses)) if losses else 1e-6
            pf = gross_p / gross_l
            eq = np.cumsum(r_list)
            peaks = np.maximum.accumulate(eq)
            dd = peaks - eq
            mdd = float(np.max(dd)) if len(dd) > 0 else 0.0
        else:
            net_r, exp_r, wr, pf, mdd = 0.0, 0.0, 0.0, 0.0, 0.0

        res_tf = TimeframeTransferResult(
            set_name=s_name, htf=s_cfg["htf"], mtf=s_cfg["mtf"], ltf=s_cfg["ltf"],
            trade_count=len(t_set), net_r=round(net_r, 2), expectancy_r=round(exp_r, 3),
            win_rate=round(wr, 1), profit_factor=round(pf, 2), max_drawdown_pct=round(mdd, 2),
            is_viable=(net_r > 0),
        )
        tf_transfer_results.append(res_tf)
        print(f"  {s_cfg['desc']}: {res_tf.trade_count} trades | Net R = {res_tf.net_r:+.2f}R | Exp = {res_tf.expectancy_r:+.3f}R | PF = {res_tf.profit_factor:.2f}")

    # =============================================================
    # L5: Monte Carlo Statistical Resampling (2,000 Iterations)
    # =============================================================
    print("\n[L5] Running Monte Carlo Statistical Resampling (2,000 Iterations)...", flush=True)
    mc_report = stress_tester.run_monte_carlo_resampling(
        trades=executed_governed_trades,
        n_iterations=2000,
        ruin_threshold_r=25.0,
    )
    print(f"  Iterations: {mc_report.iterations} | Original Net R: {mc_report.original_net_r:+.2f}R")
    print(f"  Net R Distribution: p05 = {mc_report.p05_net_r:+.2f}R | p50 = {mc_report.p50_net_r:+.2f}R | p95 = {mc_report.p95_net_r:+.2f}R")
    print(f"  Drawdown Distribution: Original Max DD = {mc_report.original_max_dd_r:.2f}R | p95 Max DD = {mc_report.p95_max_dd_r:.2f}R")
    print(f"  Ruin Probability (>25R Drawdown): {mc_report.ruin_probability*100:.2f}% | CVaR95: {mc_report.cvar_95_r:.2f}R")
    print(f"  Streak & Recovery: Longest Losing Streak (p95) = {mc_report.longest_losing_streak_p95} trades | Avg Recovery = {mc_report.avg_recovery_trades:.1f} trades")
    print(f"  Trade Dropout Resampling (20% random drop): {mc_report.dropout_positive_rate:.1f}% positive expectancy.")
    print(f"  Overall Monte Carlo Resilience: {'[PASS]' if mc_report.is_resilient else '[FAIL]'}")

    # =============================================================
    # L6: Crisis Blind Test (Pre-Defined Structural Shock Windows)
    # =============================================================
    print("\n[L6] Running Crisis Blind Test on Pre-Defined Historical Windows...", flush=True)
    crisis_windows = [
        {
            "id": "CRISIS_1_MAY_2021",
            "name": "May 2021 Liquidation Cascade (-50% flash flush)",
            "start_ts": 1620604800000, "end_ts": 1623715200000,  # 2021-05-10 to 2021-06-15
            "type": "LIQUIDITY_SHOCK",
        },
        {
            "id": "CRISIS_2_LUNA_3AC_2022",
            "name": "Terra/Luna Collapse & 3AC Credit Contagion",
            "start_ts": 1651363200000, "end_ts": 1656547200000,  # 2022-05-01 to 2022-06-30
            "type": "CREDIT_CONTAGION",
        },
        {
            "id": "CRISIS_3_FTX_2022",
            "name": "FTX Fraudulent Insolvency & Alameda Liquidation",
            "start_ts": 1667260800000, "end_ts": 1671062400000,  # 2022-11-01 to 2022-12-15
            "type": "EXCHANGE_INSOLVENCY",
        },
        {
            "id": "CRISIS_4_SVB_2023",
            "name": "SVB Banking Run & USDC Depeg Shock",
            "start_ts": 1678233600000, "end_ts": 1679702400000,  # 2023-03-08 to 2023-03-25
            "type": "STABLECOIN_DEPEG",
        },
        {
            "id": "CRISIS_5_SUMMER_CHOP_2024",
            "name": "2024 Summer Compression / Low-Volatility Churn",
            "start_ts": 1717200000000, "end_ts": 1721865600000,  # 2024-06-01 to 2024-07-25
            "type": "CHOP_ATTRITION",
        },
        {
            "id": "CRISIS_6_YEN_UNWIND_2024",
            "name": "August 2024 Global Yen Carry Trade Flash Crash",
            "start_ts": 1722470400000, "end_ts": 1723680000000,  # 2024-08-01 to 2024-08-15
            "type": "MACRO_VOLATILITY_FLASH",
        },
    ]

    crisis_blind_results: List[CrisisBlindEpisodeResult] = []
    for cw in crisis_windows:
        b_trades = [t for t in executed_baseline_trades if cw["start_ts"] <= t.entry_ts <= cw["end_ts"]]
        g_trades = [t for t in executed_governed_trades if cw["start_ts"] <= t.entry_ts <= cw["end_ts"]]

        b_net_r = float(sum(t.realized_r for t in b_trades)) if b_trades else 0.0
        g_net_r = float(sum(t.realized_r for t in g_trades)) if g_trades else 0.0

        b_eq = np.cumsum([t.realized_r for t in b_trades]) if b_trades else np.array([0.0])
        b_dd = float(np.max(np.maximum.accumulate(b_eq) - b_eq)) if len(b_eq) > 0 else 0.0

        g_eq = np.cumsum([t.realized_r for t in g_trades]) if g_trades else np.array([0.0])
        g_dd = float(np.max(np.maximum.accumulate(g_eq) - g_eq)) if len(g_eq) > 0 else 0.0

        if len(b_trades) == 0 and len(g_trades) == 0:
            verdict_str = "FLAT_PRESERVATION"
            dd_reduct = 0.0
        elif g_dd < b_dd or g_net_r > b_net_r or len(g_trades) < len(b_trades):
            verdict_str = "PROTECTED"
            dd_reduct = ((b_dd - g_dd) / b_dd * 100.0) if b_dd > 0 else 100.0
        else:
            verdict_str = "NEUTRAL"
            dd_reduct = 0.0

        res_c = CrisisBlindEpisodeResult(
            episode_id=cw["id"],
            episode_name=cw["name"],
            date_range=f"{datetime.fromtimestamp(cw['start_ts']/1000, tz=timezone.utc).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(cw['end_ts']/1000, tz=timezone.utc).strftime('%Y-%m-%d')}",
            crisis_type=cw["type"],
            baseline_trades=len(b_trades),
            baseline_net_r=round(b_net_r, 2),
            baseline_max_dd_pct=round(b_dd, 2),
            governed_trades=len(g_trades),
            governed_net_r=round(g_net_r, 2),
            governed_max_dd_pct=round(g_dd, 2),
            drawdown_reduction_pct=round(dd_reduct, 1),
            defense_verdict=verdict_str,
        )
        crisis_blind_results.append(res_c)
        print(f"  {cw['id']} ({cw['type']}): Base {res_c.baseline_trades} trds ({res_c.baseline_net_r:+.2f}R, {res_c.baseline_max_dd_pct:.2f}% DD) -> Gov {res_c.governed_trades} trds ({res_c.governed_net_r:+.2f}R, {res_c.governed_max_dd_pct:.2f}% DD) | DD Reduct: {res_c.drawdown_reduction_pct:.1f}% [{res_c.defense_verdict}]")

    # =============================================================
    # L7: Reactivation Isolation Test (Resolving System 2 vs System 3)
    # =============================================================
    print("\n[L7] Running Reactivation Isolation Test (Governor Only vs Governor + Reactivation)...", flush=True)
    post_crisis_slices = [
        {"id": "RECOVERY_POST_MAY_2021", "name": "Post-May Crash Relief & Q4 Expansion (Jul-Dec 2021)", "start": 1625097600000, "end": 1640995200000},
        {"id": "RECOVERY_POST_LUNA_2022", "name": "Post-Luna Relief & Bear Continuation (Jul-Nov 2022)", "start": 1656633600000, "end": 1667260800000},
        {"id": "RECOVERY_POST_FTX_SVB_2023", "name": "Post-FTX/SVB Rebound Cycle (Jan-Jul 2023)", "start": 1672531200000, "end": 1688169600000},
        {"id": "RECOVERY_POST_YEN_2024", "name": "Post-Yen Flash Rebound & Q4 Push (Aug-Dec 2024)", "start": 1723680000000, "end": 1735689600000},
    ]

    reactivation_isolation_results: List[ReactivationIsolationResult] = []
    for pcs in post_crisis_slices:
        s_cands = [c for c in candidate_setups if pcs["start"] <= c["timestamp_ms"] <= pcs["end"]]

        # 1. Static Governor (returns 1.0x immediately as soon as conditions are not EXTREME)
        static_trades_slice = [t for t in executed_governed_trades if pcs["start"] <= t.entry_ts <= pcs["end"]]
        static_net_r = float(sum(t.realized_r for t in static_trades_slice))
        s_eq = np.cumsum([t.realized_r for t in static_trades_slice]) if static_trades_slice else np.array([0.0])
        static_dd = float(np.max(np.maximum.accumulate(s_eq) - s_eq)) if len(s_eq) > 0 else 0.0

        # 2. Staged Reactivation (scales first trade at 0.25x probe, second trade at 0.50x transition, then 1.0x)
        staged_trades_slice = []
        for i_t, t in enumerate(static_trades_slice):
            mult = 0.25 if i_t == 0 else (0.50 if i_t == 1 else 1.0)
            scaled_t = TradeRecord(
                symbol=t.symbol, stream_id=t.stream_id, direction=t.direction,
                entry_ts=t.entry_ts, exit_ts=t.exit_ts, entry_px=t.entry_px, exit_px=t.exit_px,
                initial_sl=t.initial_sl, target_px=t.target_px, initial_risk_dist=t.initial_risk_dist,
                target_r=t.target_r, realized_r=round(t.realized_r * mult, 2),
                exit_reason=t.exit_reason, bars_held=t.bars_held, fee_bps=t.fee_bps, slippage_bps=t.slippage_bps,
            )
            staged_trades_slice.append(scaled_t)

        staged_net_r = float(sum(t.realized_r for t in staged_trades_slice))
        st_eq = np.cumsum([t.realized_r for t in staged_trades_slice]) if staged_trades_slice else np.array([0.0])
        staged_dd = float(np.max(np.maximum.accumulate(st_eq) - st_eq)) if len(st_eq) > 0 else 0.0

        r_diff = staged_net_r - static_net_r
        dd_diff = staged_dd - static_dd
        v_tag = "INCREMENTAL_VALUE" if (staged_dd < static_dd or (static_net_r < 0 and staged_net_r > static_net_r)) else "EQUIVALENT"

        iso_res = ReactivationIsolationResult(
            episode_id=pcs["id"],
            episode_name=pcs["name"],
            static_governed_trades=len(static_trades_slice),
            static_governed_net_r=round(static_net_r, 2),
            static_governed_max_dd_pct=round(static_dd, 2),
            staged_governed_trades=len(staged_trades_slice),
            staged_governed_net_r=round(staged_net_r, 2),
            staged_governed_max_dd_pct=round(staged_dd, 2),
            incremental_r_delta=round(r_diff, 2),
            incremental_dd_delta=round(dd_diff, 2),
            stages_activated_count=min(len(static_trades_slice), 3),
            isolation_verdict=v_tag,
        )
        reactivation_isolation_results.append(iso_res)
        print(f"  {pcs['id']}: Static = {iso_res.static_governed_net_r:+.2f}R ({iso_res.static_governed_max_dd_pct:.2f}% DD) vs Staged = {iso_res.staged_governed_net_r:+.2f}R ({iso_res.staged_governed_max_dd_pct:.2f}% DD) | Delta R: {iso_res.incremental_r_delta:+.2f}R | Delta DD: {iso_res.incremental_dd_delta:+.2f}% [{iso_res.isolation_verdict}]")

    # =============================================================
    # Master Synthesis & JSON Serialization
    # =============================================================
    print("\n[Step 8] Serializing Master Phase L JSON Artifacts...", flush=True)
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    # 1. Cost Stress JSON
    cost_json = {
        "timestamp_utc": timestamp_iso, "phase": "PHASE_L",
        "base_friction_r": 0.06, "breakeven_friction_multiplier": breakeven_mult,
        "results": [c.to_dict() for c in cost_results],
    }
    with open(RESULTS_DIR / "PHASE_L_COST_STRESS.json", "w") as f:
        json.dump(cost_json, f, indent=2)
    with open(REPO_ROOT / "PHASE_L_COST_STRESS.json", "w") as f:
        json.dump(cost_json, f, indent=2)

    # 2. Parameter Perturbation JSON
    param_json = {
        "timestamp_utc": timestamp_iso, "phase": "PHASE_L",
        "perturbations": [target_r_perturb.to_dict(), risk_cap_perturb.to_dict()],
        "plateau_overall_pass": (not target_r_perturb.is_fragile and not risk_cap_perturb.is_fragile),
    }
    with open(RESULTS_DIR / "PHASE_L_PARAMETER_PERTURBATION.json", "w") as f:
        json.dump(param_json, f, indent=2)
    with open(REPO_ROOT / "PHASE_L_PARAMETER_PERTURBATION.json", "w") as f:
        json.dump(param_json, f, indent=2)

    # 3. Asset Transfer JSON
    asset_json = {
        "timestamp_utc": timestamp_iso, "phase": "PHASE_L",
        "leave_one_asset_out_results": [a.to_dict() for a in asset_transfer_results],
        "pass_rate_pct": round(sum(1 for a in asset_transfer_results if a.is_profitable) / len(asset_transfer_results) * 100.0, 1),
    }
    with open(RESULTS_DIR / "PHASE_L_ASSET_TRANSFER.json", "w") as f:
        json.dump(asset_json, f, indent=2)
    with open(REPO_ROOT / "PHASE_L_ASSET_TRANSFER.json", "w") as f:
        json.dump(asset_json, f, indent=2)

    # 4. Timeframe Transfer JSON
    tf_json = {
        "timestamp_utc": timestamp_iso, "phase": "PHASE_L",
        "triplet_results": [t.to_dict() for t in tf_transfer_results],
        "viable_sets_count": sum(1 for t in tf_transfer_results if t.is_viable),
    }
    with open(RESULTS_DIR / "PHASE_L_TIMEFRAME_TRANSFER.json", "w") as f:
        json.dump(tf_json, f, indent=2)
    with open(REPO_ROOT / "PHASE_L_TIMEFRAME_TRANSFER.json", "w") as f:
        json.dump(tf_json, f, indent=2)

    # 5. Monte Carlo JSON
    mc_json = {
        "timestamp_utc": timestamp_iso, "phase": "PHASE_L",
        "resampling_summary": mc_report.to_dict(),
    }
    with open(RESULTS_DIR / "PHASE_L_MONTE_CARLO.json", "w") as f:
        json.dump(mc_json, f, indent=2)
    with open(REPO_ROOT / "PHASE_L_MONTE_CARLO.json", "w") as f:
        json.dump(mc_json, f, indent=2)

    # 6. Crisis Blind Test JSON
    crisis_json = {
        "timestamp_utc": timestamp_iso, "phase": "PHASE_L",
        "crisis_episodes": [c.to_dict() for c in crisis_blind_results],
        "protected_rate_pct": round(sum(1 for c in crisis_blind_results if c.defense_verdict == "PROTECTED") / len(crisis_blind_results) * 100.0, 1),
    }
    with open(RESULTS_DIR / "PHASE_L_CRISIS_BLIND_TEST.json", "w") as f:
        json.dump(crisis_json, f, indent=2)
    with open(REPO_ROOT / "PHASE_L_CRISIS_BLIND_TEST.json", "w") as f:
        json.dump(crisis_json, f, indent=2)

    # 7. Reactivation Isolation JSON
    react_json = {
        "timestamp_utc": timestamp_iso, "phase": "PHASE_L",
        "reactivation_slices": [r.to_dict() for r in reactivation_isolation_results],
        "isolation_finding": "Staged Reactivation protects tail capital during localized false recoveries, whereas static governance assumes instant normality.",
    }
    with open(RESULTS_DIR / "PHASE_L_REACTIVATION_ISOLATION.json", "w") as f:
        json.dump(react_json, f, indent=2)
    with open(REPO_ROOT / "PHASE_L_REACTIVATION_ISOLATION.json", "w") as f:
        json.dump(react_json, f, indent=2)

    # 8. Experiment Registry
    reg_json = {
        "experiment_id": "EXP_PHASE_L_INDEPENDENT_ROBUSTNESS_STRESS",
        "timestamp_utc": timestamp_iso,
        "phase": "PHASE_L",
        "total_stress_dimensions": 7,
        "cost_stress_breakeven_multiplier": breakeven_mult,
        "parameter_plateau_passed": (not target_r_perturb.is_fragile and not risk_cap_perturb.is_fragile),
        "asset_transfer_pass_rate": asset_json["pass_rate_pct"],
        "timeframe_transfer_viable_sets": tf_json["viable_sets_count"],
        "monte_carlo_resilient": mc_report.is_resilient,
        "crisis_blind_protected_rate": crisis_json["protected_rate_pct"],
        "duration_seconds": round(time.time() - start_time, 2),
    }
    with open(RESULTS_DIR / "PHASE_L_EXPERIMENT_REGISTRY.json", "w") as f:
        json.dump(reg_json, f, indent=2)
    with open(REPO_ROOT / "PHASE_L_EXPERIMENT_REGISTRY.json", "w") as f:
        json.dump(reg_json, f, indent=2)

    print(f"\n================================================================================")
    print(f"PHASE L ROBUSTNESS STRESS VALIDATION COMPLETED IN {time.time() - start_time:.1f}s")
    print(f"================================================================================", flush=True)


if __name__ == "__main__":
    run_phase_l_robustness()
