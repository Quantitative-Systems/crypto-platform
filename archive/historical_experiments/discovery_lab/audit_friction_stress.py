"""
Quantitative Systems Platform (QSP) — Systematic Strategies Research Division.
Phase C: Expanded Friction Stress Battery & Breakpoint Analysis.

Tests all 5 qualified candidate strategies across:
1. Graduated friction multipliers: 1.0x, 1.5x, 2.0x, 3.0x, 4.0x
   - Base 1.0x: Taker 0.075%, Slippage 0.03%, Spread 0.01% (Round-trip 0.22%)
   - Heavy 2.0x: Taker 0.150%, Slippage 0.06%, Spread 0.02% (Round-trip 0.44%)
   - Adverse 3.0x: Taker 0.225%, Slippage 0.09%, Spread 0.03% (Round-trip 0.66%)
   - Extreme 4.0x: Taker 0.300%, Slippage 0.12%, Spread 0.04% (Round-trip 0.88%)
2. Stochastic Slippage Battery (Gaussian distribution N(0.03%, 0.02%), bounded [0.01%, 0.15%], seed=42)
3. Computes the friction breakpoint where strategy expectancy degrades to 0.0R.
"""

import os
import sys
import json
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_intelligence.primitives import Candle
from backtesting.friction_model import FrictionModel
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, load_candles
from research.discovery_lab.oos_manager import OOSManager
from research.discovery_lab.strategy_generator import StrategyExecutor

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
VAL_OOS_FILE = os.path.join(RESULTS_DIR, "validation_and_oos_results.json")
OUTPUT_FILE = os.path.join(RESULTS_DIR, "AUDIT_PHASE_C_FRICTION_BATTERY.json")


class StochasticFrictionModel(FrictionModel):
    """Simulates variable market microstructure slippage with Gaussian dispersion."""

    def __init__(self, seed: int = 42, base_mult: float = 1.0):
        super().__init__(
            taker_fee_pct=0.00075 * base_mult,
            slippage_pct=0.00030 * base_mult,
            spread_pct=0.00010 * base_mult,
        )
        self.rng = np.random.RandomState(seed)

    def calculate_buy_fill(self, raw_price: float) -> float:
        stoch_slip = float(np.clip(self.rng.normal(self.slippage_pct, self.slippage_pct * 0.66), 0.00010, 0.00150))
        return raw_price * (1.0 + stoch_slip + (self.spread_pct / 2.0))

    def calculate_sell_fill(self, raw_price: float) -> float:
        stoch_slip = float(np.clip(self.rng.normal(self.slippage_pct, self.slippage_pct * 0.66), 0.00010, 0.00150))
        return raw_price * (1.0 - stoch_slip - (self.spread_pct / 2.0))


def run_phase_c_audit():
    print("=" * 90)
    print("PHASE C: EXPANDED FRICTION STRESS BATTERY & BREAKPOINT ANALYSIS")
    print("=" * 90)

    if not os.path.exists(VAL_OOS_FILE):
        raise FileNotFoundError(f"Missing {VAL_OOS_FILE}")

    with open(VAL_OOS_FILE, "r") as f:
        val_oos_records = json.load(f)

    qualified = [r for r in val_oos_records if r["final_status"] == "QUALIFIED_ROBUST"]
    print(f"Stress-testing {len(qualified)} QUALIFIED_ROBUST candidates across full 2021-2026 horizon...")

    multipliers = [1.0, 1.5, 2.0, 3.0, 4.0]
    audit_results = []

    for cand in qualified:
        cid = cand["candidate_id"]
        symbol = cand["symbol"]
        set_id = cand["set"]
        fam_id = cand["family_id"]

        sc = TIMEFRAME_SETS[set_id]
        htf = load_candles(symbol, sc["HTF"])
        mtf = load_candles(symbol, sc["MTF"])
        ltf = load_candles(symbol, sc["LTF"])

        method_name = "run_family_7_mtf_continuation" if fam_id == "FAM-07-MTFCONT" else "run_family_4_momentum"

        mult_results = {}
        for m in multipliers:
            exec_m = StrategyExecutor(
                symbol, set_id, htf, mtf, ltf,
                start_ts=OOSManager.DEV_START_TS, end_ts=1788307200
            )
            exec_m.friction = FrictionModel(
                taker_fee_pct=0.00075 * m,
                slippage_pct=0.00030 * m,
                spread_pct=0.00010 * m,
            )
            res = getattr(exec_m, method_name)()
            met = res["metrics"]
            mult_results[f"{m:.1f}x"] = {
                "multiplier": m,
                "net_r": round(float(met["net_r"]), 2),
                "expectancy_r": round(float(met["expectancy_r"]), 4),
                "profit_factor": met["profit_factor_r"],
                "max_drawdown_r": round(float(met["max_drawdown_r"]), 2),
                "trades": int(met["total_trades"]),
                "survived": bool(met["net_r"] > 0 and met["expectancy_r"] > 0),
            }

        # Stochastic Slippage test
        exec_stoch = StrategyExecutor(
            symbol, set_id, htf, mtf, ltf,
            start_ts=OOSManager.DEV_START_TS, end_ts=1788307200
        )
        exec_stoch.friction = StochasticFrictionModel(seed=42, base_mult=1.0)
        res_stoch = getattr(exec_stoch, method_name)()
        met_stoch = res_stoch["metrics"]

        stoch_result = {
            "net_r": round(float(met_stoch["net_r"]), 2),
            "expectancy_r": round(float(met_stoch["expectancy_r"]), 4),
            "profit_factor": met_stoch["profit_factor_r"],
            "max_drawdown_r": round(float(met_stoch["max_drawdown_r"]), 2),
            "trades": int(met_stoch["total_trades"]),
            "survived": bool(met_stoch["net_r"] > 0 and met_stoch["expectancy_r"] > 0),
        }

        # Find friction breakpoint (where Net R hits 0)
        breakpoint_mult = 1.0
        for test_m in np.linspace(1.0, 10.0, 19):
            exec_test = StrategyExecutor(
                symbol, set_id, htf, mtf, ltf,
                start_ts=OOSManager.DEV_START_TS, end_ts=1788307200
            )
            exec_test.friction = FrictionModel(
                taker_fee_pct=0.00075 * test_m,
                slippage_pct=0.00030 * test_m,
                spread_pct=0.00010 * test_m,
            )
            res_test = getattr(exec_test, method_name)()
            if res_test["metrics"]["net_r"] <= 0:
                breakpoint_mult = round(float(test_m), 1)
                break
        else:
            breakpoint_mult = ">10.0x"

        print(f"\n{cid} ({symbol} {set_id}):")
        print(f"  1.0x Base: NetR={mult_results['1.0x']['net_r']:+6.2f}R | Exp={mult_results['1.0x']['expectancy_r']:+5.2f}R | PF={mult_results['1.0x']['profit_factor']}")
        print(f"  2.0x Friction: NetR={mult_results['2.0x']['net_r']:+6.2f}R | Exp={mult_results['2.0x']['expectancy_r']:+5.2f}R | PF={mult_results['2.0x']['profit_factor']}")
        print(f"  3.0x Friction: NetR={mult_results['3.0x']['net_r']:+6.2f}R | Exp={mult_results['3.0x']['expectancy_r']:+5.2f}R | PF={mult_results['3.0x']['profit_factor']}")
        print(f"  4.0x Friction: NetR={mult_results['4.0x']['net_r']:+6.2f}R | Exp={mult_results['4.0x']['expectancy_r']:+5.2f}R | PF={mult_results['4.0x']['profit_factor']}")
        print(f"  Stochastic Slip: NetR={stoch_result['net_r']:+6.2f}R | Exp={stoch_result['expectancy_r']:+5.2f}R | PF={stoch_result['profit_factor']}")
        print(f"  Friction Breakpoint: {breakpoint_mult}")

        audit_results.append({
            "candidate_id": cid,
            "symbol": symbol,
            "set": set_id,
            "graduated_multipliers": mult_results,
            "stochastic_slippage": stoch_result,
            "friction_breakpoint": breakpoint_mult,
        })

    manifest = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_phase": "PHASE_C_FRICTION_BATTERY",
        "governance": "Quantitative Systems Platform (QSP) Research Division",
        "multipliers_tested": multipliers,
        "results": audit_results,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 90)
    print("AUDIT PHASE C COMPLETE.")
    print(f"Report saved to: {OUTPUT_FILE}")
    print("=" * 90)


if __name__ == "__main__":
    run_phase_c_audit()
