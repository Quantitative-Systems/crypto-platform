"""
PROJECT TOP1 — Autonomous Quantitative Strategy Discovery & Qualification Engine.

Executes autonomous Development research across 8 strategy families:
1. Trend Following
2. Trend + Pullback
3. Breakout (Donchian)
4. Momentum
5. Mean Reversion (Bollinger Exhaustion)
6. Volatility Expansion (Squeeze Breakout)
7. Multi-Timeframe Continuation
8. Regime-Adaptive Systems

Enforces multi-dimensional qualification gates:
- Minimum Trade Frequency: >= 100 trades per individual asset/set instance in Development (2021-2022)
- Positive Expectancy after realistic fees and slippage
- Controlled Drawdown (Max DD <= 25R)
- Profit Concentration Firewall (Top 1 trade <= 50% Net R, Net R without Top 1 > 0, Net R without Top 5 > 0)
- Cost Stress Test (2x friction: taker fee 0.15%, slippage 0.06%, spread 0.02%)
- Parameter Perturbation (+-20% parameter stability)
"""

import os
import sys
import json
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_intelligence.primitives import Candle
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, ASSETS, load_candles
from research.discovery_lab.oos_manager import OOSManager
from research.discovery_lab.strategy_generator import StrategyExecutor
from research.discovery_lab.strategy_registry import StrategyRegistry, StrategyStatus
from research.analytics.r_accounting import RAccountingEngine
from backtesting.friction_model import FrictionModel


class AutonomousResearcher:
    """Orchestrates autonomous multi-family strategy discovery, falsification, and qualification."""

    def __init__(self, registry_path: Optional[str] = None):
        self.registry = StrategyRegistry(registry_path)
        self.target_assets = ASSETS  # BTC/USDT, ETH/USDT, SOL/USDT
        self.target_sets = ["Set 1", "Set 2", "Set 3", "Set 4"]  # Sets with full 2021-2022 coverage
        self.families = [
            ("FAM-01-TREND", "Trend Following", "run_family_1_trend_following"),
            ("FAM-02-PULLBACK", "Trend + Pullback", "run_family_2_trend_pullback"),
            ("FAM-03-BREAKOUT", "Breakout (Donchian)", "run_family_3_breakout"),
            ("FAM-04-MOMENTUM", "Momentum Continuation", "run_family_4_momentum"),
            ("FAM-05-MEANREV", "Mean Reversion", "run_family_5_mean_reversion"),
            ("FAM-06-VOLEXP", "Volatility Expansion", "run_family_6_volatility_expansion"),
            ("FAM-07-MTFCONT", "MTF Continuation", "run_family_7_mtf_continuation"),
            ("FAM-08-REGIME", "Regime-Adaptive Systems", "run_family_8_regime_adaptive"),
        ]

    def run_cost_stress_test(
        self,
        executor: StrategyExecutor,
        family_method: str,
        base_net_r: float,
    ) -> Tuple[bool, float, float]:
        """
        Tests candidate resilience under 2x fees and slippage.
        Returns (passed, stressed_net_r, stressed_exp_r).
        """
        # Temporarily increase friction
        orig_friction = executor.friction
        executor.friction = FrictionModel(
            taker_fee_pct=0.0015,   # 2x taker fee (0.15%)
            slippage_pct=0.0006,    # 2x slippage (0.06%)
            spread_pct=0.0002,      # 2x spread (0.02%)
        )
        try:
            method = getattr(executor, family_method)
            res = method()
            m = res["metrics"]
            stressed_net_r = m["net_r"]
            stressed_exp_r = m["expectancy_r"]
            passed = stressed_net_r > 0.0 and stressed_exp_r > 0.0
            return passed, stressed_net_r, stressed_exp_r
        finally:
            executor.friction = orig_friction

    def run_parameter_perturbation_test(
        self,
        executor: StrategyExecutor,
        family_method: str,
    ) -> Tuple[bool, float, float]:
        """
        Tests candidate parameter stability under +-20% parameter shifts.
        Returns (passed, avg_perturbed_net_r, avg_perturbed_exp_r).
        """
        method = getattr(executor, family_method)
        # Test with 20% tighter TP (2.0R) and 20% wider TP (3.0R) or adjusted ATR mult
        try:
            res_low = method(tp_r=2.0)
            res_high = method(tp_r=3.2)
            m_low = res_low["metrics"]
            m_high = res_high["metrics"]

            avg_net_r = (m_low["net_r"] + m_high["net_r"]) / 2.0
            avg_exp_r = (m_low["expectancy_r"] + m_high["expectancy_r"]) / 2.0
            passed = m_low["expectancy_r"] > 0.0 and m_high["expectancy_r"] > 0.0
            return passed, avg_net_r, avg_exp_r
        except Exception:
            return False, 0.0, 0.0

    def run_discovery_cycle(self) -> List[Dict[str, Any]]:
        """Executes full autonomous discovery matrix."""
        print("=" * 90)
        print("PROJECT TOP1 — AUTONOMOUS MULTI-FAMILY STRATEGY DISCOVERY ENGINE")
        print("=" * 90)
        print("Horizon: Development 2021-2022 (UTC)")
        print(f"Target Assets: {', '.join(self.target_assets)}")
        print(f"Target Sets: {', '.join(self.target_sets)}")
        print(f"Strategy Families: {len(self.families)}")
        print("Evidence Requirement: >= 100 independently generated trades per asset x set instance")
        print("=" * 90)

        all_candidate_reports = []

        for fam_id, fam_name, fam_method in self.families:
            print(f"\n######################################################################")
            print(f"INVESTIGATING STRATEGY FAMILY: {fam_id} ({fam_name})")
            print(f"######################################################################")

            for symbol in self.target_assets:
                for set_name in self.target_sets:
                    sc = TIMEFRAME_SETS[set_name]
                    htf = load_candles(symbol, sc["HTF"])
                    mtf = load_candles(symbol, sc["MTF"])
                    ltf = load_candles(symbol, sc["LTF"])

                    if not htf or not mtf or not ltf:
                        print(f"  [{fam_id}] {symbol} {set_name}: MISSING CANDLE DATA")
                        continue

                    # Filter strictly up to DEV_END_TS
                    htf_dev = OOSManager.get_development_candles_by_date(htf, include_warmup=True)
                    mtf_dev = OOSManager.get_development_candles_by_date(mtf, include_warmup=True)
                    ltf_dev = OOSManager.get_development_candles_by_date(ltf, include_warmup=True)

                    executor = StrategyExecutor(symbol, set_name, htf_dev, mtf_dev, ltf_dev)
                    method = getattr(executor, fam_method)
                    res = method()

                    m = res["metrics"]
                    n_trades = res["total_trades_dev"]
                    net_r = m["net_r"]
                    exp_r = m["expectancy_r"]
                    max_dd = m["max_drawdown_r"]
                    pf = m["profit_factor_r"]
                    win_rate = m["win_rate"]
                    top_1_pct = m["top_1_pct_net_r"]
                    net_r_no_top1 = m["net_r_without_top_1"]
                    conc_status = m["profit_concentration_status"]

                    # Evaluate Qualification Gates
                    is_n_qualified = n_trades >= 100
                    is_exp_positive = exp_r > 0.0 and net_r > 0.0
                    is_dd_acceptable = max_dd <= 25.0
                    is_conc_acceptable = conc_status == "PASS"

                    status = StrategyStatus.FAILED
                    falsification_reasons = []

                    if not is_n_qualified:
                        falsification_reasons.append(f"INSUFFICIENT_N ({n_trades} < 100)")
                    if not is_exp_positive:
                        falsification_reasons.append(f"NEGATIVE_EXPECTANCY ({exp_r:+.2f}R)")
                    if not is_dd_acceptable:
                        falsification_reasons.append(f"EXCESSIVE_DD ({max_dd:.2f}R > 25R)")
                    if not is_conc_acceptable:
                        falsification_reasons.append(f"CONCENTRATION_VIOLATION ({conc_status})")

                    # If candidate passed initial gates, run stress and perturbation
                    cost_stress_passed = False
                    param_stability_passed = False
                    stressed_net_r = 0.0
                    stressed_exp_r = 0.0

                    if is_n_qualified and is_exp_positive and is_dd_acceptable and is_conc_acceptable:
                        cost_stress_passed, stressed_net_r, stressed_exp_r = self.run_cost_stress_test(
                            executor, fam_method, net_r
                        )
                        param_stability_passed, avg_pert_net, avg_pert_exp = self.run_parameter_perturbation_test(
                            executor, fam_method
                        )

                        if not cost_stress_passed:
                            falsification_reasons.append(f"COST_STRESS_FAILED (Stressed Exp: {stressed_exp_r:+.2f}R)")
                        if not param_stability_passed:
                            falsification_reasons.append("PARAMETER_INSTABILITY")

                        if cost_stress_passed and param_stability_passed:
                            status = StrategyStatus.PROMISING

                    candidate_id = f"{fam_id}_{symbol.replace('/', '')}_{set_name.replace(' ', '')}"
                    report = {
                        "candidate_id": candidate_id,
                        "family_id": fam_id,
                        "family_name": fam_name,
                        "symbol": symbol,
                        "set": set_name,
                        "style": sc["style"],
                        "n_trades": n_trades,
                        "net_r": net_r,
                        "expectancy_r": exp_r,
                        "profit_factor_r": pf,
                        "win_rate": win_rate,
                        "max_drawdown_r": max_dd,
                        "median_r": m["median_r"],
                        "mean_r": m["average_r"],
                        "top_1_r": m["top_1_r"],
                        "top_1_pct": top_1_pct,
                        "net_r_without_top_1": net_r_no_top1,
                        "profit_concentration_status": conc_status,
                        "cost_stress_passed": cost_stress_passed,
                        "stressed_net_r": stressed_net_r,
                        "param_stability_passed": param_stability_passed,
                        "status": status.value,
                        "falsification_reasons": falsification_reasons,
                    }
                    all_candidate_reports.append(report)

                    # Print formatted milestone summary
                    print(f"--- [MILESTONE] {candidate_id} ---")
                    print(f"  Asset: {symbol} | Set: {set_name} ({sc['style']})")
                    print(f"  N: {n_trades:3d} (Req >= 100: {'PASS' if is_n_qualified else 'FAIL'}) | Net R: {net_r:+6.2f}R | Exp: {exp_r:+5.2f}R | PF: {pf} | MaxDD: {max_dd:5.2f}R")
                    print(f"  Top 1 Winner: {m['top_1_r']:+5.2f}R ({top_1_pct:5.1f}% of Net R) | Net R w/o Top 1: {net_r_no_top1:+6.2f}R | Status: {conc_status}")
                    if is_n_qualified and is_exp_positive:
                        print(f"  Cost Stress (2x Friction): {'PASS' if cost_stress_passed else 'FAIL'} ({stressed_net_r:+5.2f}R) | Parameter Stability: {'PASS' if param_stability_passed else 'FAIL'}")
                    print(f"  VERDICT: {status.value} | Reasons: {', '.join(falsification_reasons) if falsification_reasons else 'ALL DEVELOPMENT GATES PASSED'}")

        # Save all reports to JSON
        out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "autonomous_discovery_reports.json")
        with open(out_file, "w") as f:
            json.dump(all_candidate_reports, f, indent=2)
        print(f"\nAll candidate reports saved to: {out_file}")

        return all_candidate_reports


if __name__ == "__main__":
    researcher = AutonomousResearcher()
    researcher.run_discovery_cycle()
