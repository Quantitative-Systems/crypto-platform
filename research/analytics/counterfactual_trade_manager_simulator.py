"""
Product 04 — Research Laboratory: Counterfactual Trade Management Simulator
Executes Objective 4 and Objective 5 of the Master Research Directive.

Simulates alternative prospective trade-management policies on the EXACT SAME 128 H1 entries:
1. POLICY_A: Original H1 (Hold for 4.0R HTF TP, MTF external trailing)
2. POLICY_B: BE +0.1R after +1.0R MFE
3. POLICY_C: BE +0.1R after +0.75R MFE
4. POLICY_D: BE +0.1R after +1.5R MFE
5. POLICY_E: Fixed +1.5R TP
6. POLICY_F: Fixed +2.0R TP
7. POLICY_G: Trailing Ratchet at +0.75R (+0.1R) and +1.5R (+0.75R)
"""

import os
import json
import glob
from typing import Dict, List, Any
import numpy as np

from research.analytics.statistical_validator import StatisticalValidator


def simulate_counterfactual_policies(results_dir: str) -> Dict[str, Any]:
    stream_files = glob.glob(os.path.join(results_dir, "*_SET_*.json"))
    
    all_trades: List[Dict[str, Any]] = []
    for fpath in stream_files:
        if "MASTER_SUMMARY" in fpath or "manifest" in fpath:
            continue
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
            trades = data.get("trades", [])
            stream_key = data.get("provenance", {}).get("stream_key", os.path.basename(fpath).replace(".json", ""))
            for t in trades:
                t["_stream_key"] = stream_key
                all_trades.append(t)
        except Exception as e:
            print(f"Error loading {fpath}: {e}")

    policies = {
        "POLICY_A_ORIGINAL_H1": "Original H1 rule (Hold for 4.0R HTF TP, MTF external protected swing trail)",
        "POLICY_B_BE_AT_1_0R": "Ratchet SL to +0.1R once MFE reaches +1.0R",
        "POLICY_C_BE_AT_0_75R": "Ratchet SL to +0.1R once MFE reaches +0.75R",
        "POLICY_D_BE_AT_1_5R": "Ratchet SL to +0.1R once MFE reaches +1.5R",
        "POLICY_E_FIXED_1_5R_TP": "Fixed Target Take-Profit at +1.5R MFE",
        "POLICY_F_FIXED_2_0R_TP": "Fixed Target Take-Profit at +2.0R MFE",
        "POLICY_G_RATCHET_TWO_TIER": "Two-Tier: +0.75R -> SL=+0.1R; +1.5R -> SL=+0.75R"
    }

    policy_results: Dict[str, Any] = {}

    for pol_key, pol_desc in policies.items():
        simulated_net_r: List[float] = []
        simulated_gross_r: List[float] = []
        simulated_wins = 0
        simulated_losses = 0
        simulated_bes = 0
        
        for t in all_trades:
            raw_r = t.get("realized_rr", t.get("net_r", 0.0))
            mfe_r = t.get("mfe_r", 0.0) or t.get("metadata", {}).get("mfe_r", 0.0)
            mae_r = t.get("mae_r", 0.0) or t.get("metadata", {}).get("mae_r", 0.0)
            fee_r = t.get("fees_r", 0.001)
            slip_r = t.get("slippage_r", 0.005)
            friction_r = fee_r + slip_r
            
            # Simulate prospective rule execution
            if pol_key == "POLICY_A_ORIGINAL_H1":
                net_r = raw_r
            elif pol_key == "POLICY_B_BE_AT_1_0R":
                if mfe_r >= 1.0:
                    # If trade reached 1.0R, it was protected at +0.1R minimum
                    net_r = max(0.10, raw_r)
                else:
                    net_r = raw_r
            elif pol_key == "POLICY_C_BE_AT_0_75R":
                if mfe_r >= 0.75:
                    net_r = max(0.10, raw_r)
                else:
                    net_r = raw_r
            elif pol_key == "POLICY_D_BE_AT_1_5R":
                if mfe_r >= 1.5:
                    net_r = max(0.10, raw_r)
                else:
                    net_r = raw_r
            elif pol_key == "POLICY_E_FIXED_1_5R_TP":
                if mfe_r >= 1.5:
                    net_r = 1.50 - friction_r
                else:
                    net_r = -1.00 - friction_r if mae_r >= 1.0 else max(raw_r, -1.00)
            elif pol_key == "POLICY_F_FIXED_2_0R_TP":
                if mfe_r >= 2.0:
                    net_r = 2.00 - friction_r
                else:
                    net_r = -1.00 - friction_r if mae_r >= 1.0 else max(raw_r, -1.00)
            elif pol_key == "POLICY_G_RATCHET_TWO_TIER":
                if mfe_r >= 1.5:
                    net_r = max(0.75, raw_r)
                elif mfe_r >= 0.75:
                    net_r = max(0.10, raw_r)
                else:
                    net_r = raw_r
            else:
                net_r = raw_r
                
            gross_r = net_r + friction_r
            simulated_net_r.append(round(net_r, 4))
            simulated_gross_r.append(round(gross_r, 4))
            
            if net_r > 0.05:
                simulated_wins += 1
            elif -0.05 <= net_r <= 0.05:
                simulated_bes += 1
            else:
                simulated_losses += 1

        n_total = len(simulated_net_r)
        total_net_r = sum(simulated_net_r)
        mean_exp_r = total_net_r / n_total if n_total > 0 else 0.0
        win_rate = (simulated_wins / n_total * 100.0) if n_total > 0 else 0.0
        
        gross_wins = sum(x for x in simulated_net_r if x > 0)
        gross_losses = abs(sum(x for x in simulated_net_r if x < 0))
        pf = (gross_wins / gross_losses) if gross_losses > 0 else 999.0
        
        # Block Bootstrap
        boot = StatisticalValidator.block_bootstrap_resample(simulated_net_r, block_size=4, n_resamples=1000)
        
        # Max Drawdown estimation in R
        running_equity = 0.0
        peak_equity = 0.0
        max_dd_r = 0.0
        for r_val in simulated_net_r:
            running_equity += r_val
            if running_equity > peak_equity:
                peak_equity = running_equity
            dd = peak_equity - running_equity
            if dd > max_dd_r:
                max_dd_r = dd

        # Friction Shock (2.0x)
        cost_shock_exp_r = mean_exp_r - (0.006 * 2.0)

        policy_results[pol_key] = {
            "description": pol_desc,
            "total_trades": n_total,
            "wins": simulated_wins,
            "losses": simulated_losses,
            "breakevens": simulated_bes,
            "win_rate_pct": round(win_rate, 2),
            "net_realized_r": round(total_net_r, 4),
            "mean_expectancy_r": round(mean_exp_r, 4),
            "profit_factor": round(pf, 2),
            "max_drawdown_r": round(max_dd_r, 2),
            "bootstrap_95_ci": [boot["pct_5th"], boot["pct_95th"]],
            "prob_positive_edge_pct": boot["prob_positive_edge_pct"],
            "cost_shock_2x_exp_r": round(cost_shock_exp_r, 4)
        }

    return {
        "counterfactual_simulation_matrix": policy_results
    }


def main():
    results_dir = "/home/mrcn2/crypto-platform/research/results/BASELINE_002_20260902_013354"
    report = simulate_counterfactual_policies(results_dir)
    print("=" * 100)
    print("COUNTERFACTUAL TRADE-MANAGEMENT SIMULATION REPORT (N=128)")
    print("=" * 100)
    print(json.dumps(report, indent=2))
    
    out_file = "/home/mrcn2/crypto-platform/scratch/counterfactual_trade_management_results.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[OK] Counterfactual results written to: {out_file}")


if __name__ == "__main__":
    main()
