import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import asdict

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from market_data.data_manager import ALL_ASSETS, DataManager
from research.economic_evaluation_engine import EconomicEvaluationEngine, EvaluationResult, CausalTripleBarrierBacktester
from platform_core.alpha_genome import AlphaGenome, AlphaFamily
from backtesting.friction_model import FrictionModel
from strategy_engine.factory.time_series_momentum import TimeSeriesMomentumStrategy


def check_capital_viability(avg_stop_dist_pct: float, risk_pct: float = 0.01, min_notional: float = 5.0):
    if avg_stop_dist_pct <= 0: return {"$10": False, "$50": False, "$100": False}
    viability = {}
    for cap in [10, 50, 100]:
        target_risk_usd = cap * risk_pct
        target_pos_size = target_risk_usd / avg_stop_dist_pct
        actual_pos_size = min(cap, target_pos_size)
        if actual_pos_size >= min_notional:
            viability[f"${cap}"] = True
        else:
            viability[f"${cap}"] = False
    return viability

def main():
    print("=== EABG-003: Time-Series Momentum (TSMOM) Discovery ===")
    
    baseline_engine = EconomicEvaluationEngine()
    adv_friction = FrictionModel(taker_fee_pct=0.0015, slippage_pct=0.00060, spread_pct=0.00020)
    adv_backtester = CausalTripleBarrierBacktester(friction=adv_friction)
    adv_engine = EconomicEvaluationEngine(backtester=adv_backtester)
    
    dm = DataManager()
    timeframes = ["1d", "4h", "1h", "15m"]
    
    # We create a dummy instance just to pull the param grid
    dummy_strat = TimeSeriesMomentumStrategy(strategy_id="dummy", symbol="dummy")
    param_grid = dummy_strat.get_parameter_grid()
    
    stats = {
        "total_hypotheses": 0,
        "falsified_phase1_baseline": 0,
        "falsified_phase2_adversarial": 0,
        "falsified_phase3_oos": 0,
        "oos_validated": 0
    }
    
    results_list = []
    
    for asset in ALL_ASSETS:
        symbol = f"{asset}/USDT"
        print(f"\n--- Testing {symbol} ---")
        for tf in timeframes:
            # Check if data exists for tf
            try:
                df, _ = baseline_engine.loader.load(symbol, tf)
                if df is None or len(df) == 0:
                    continue
            except Exception:
                continue
                
            for params in param_grid:
                stats["total_hypotheses"] += 1
                
                lb = params["lookback"]
                vscale = params["vol_scaled"]
                
                alpha_id = f"ALPHA_TSMOM_L{lb}_V{int(vscale)}_{asset}_{tf}"
                
                genome = AlphaGenome(
                    alpha_id=alpha_id, family=AlphaFamily.DIRECTIONAL, version="1.0.0",
                    asset_universe=[symbol], venues=["Binance"], instruments=["SPOT"],
                    timeframe=tf, expected_holding_period_hours=24.0,
                    economic_rationale=f"TSMOM with Lookback {lb}, VolScaled={vscale}",
                    features=["close", "high", "low"],
                    entry_mechanism="Time-Series Momentum", exit_mechanism="Triple Barrier",
                )
                
                strat = TimeSeriesMomentumStrategy(strategy_id=alpha_id, symbol=symbol, timeframe=tf, parameters=params)
                
                # Phase 1: Baseline
                res_base = baseline_engine.evaluate(genome=genome, signal_fn=strat.generate_signals, symbol=symbol, timeframe=tf)
                
                if res_base.status != "MEASURED" or not res_base.partitions:
                    stats["falsified_phase1_baseline"] += 1
                    continue
                    
                dev_base = res_base.partitions.get("DEV")
                val_base = res_base.partitions.get("VAL")
                
                if not dev_base or not val_base or not dev_base.metrics_available or not val_base.metrics_available or dev_base.performance.net_edge_r <= 0 or val_base.performance.net_edge_r <= 0:
                    stats["falsified_phase1_baseline"] += 1
                    continue
                
                # Phase 2: Adversarial
                res_adv = adv_engine.evaluate(genome=genome, signal_fn=strat.generate_signals, symbol=symbol, timeframe=tf)
                dev_adv = res_adv.partitions.get("DEV")
                val_adv = res_adv.partitions.get("VAL")
                
                if not dev_adv or not val_adv or not dev_adv.metrics_available or not val_adv.metrics_available or dev_adv.performance.net_edge_r <= 0 or val_adv.performance.net_edge_r <= 0:
                    stats["falsified_phase2_adversarial"] += 1
                    continue
                    
                # Phase 3: Locked OOS Validation
                oos_adv = res_adv.partitions.get("OOS")
                if not oos_adv or not oos_adv.metrics_available or oos_adv.performance.net_edge_r <= 0:
                    stats["falsified_phase3_oos"] += 1
                    continue
                    
                stats["oos_validated"] += 1
                print(f"[{symbol} {tf} | TSMOM(lb={lb}, v={vscale})] => SURVIVED ALL PHASES! OOS Edge: {oos_adv.performance.net_edge_r:.4f}R")
                
                # Phase 4 & 5: Viability
                avg_stop_dist = 0.02 
                viability = check_capital_viability(avg_stop_dist)
                
                results_list.append({
                    "alpha_id": alpha_id,
                    "strategy": "TSMOM",
                    "parameters": params,
                    "symbol": symbol,
                    "timeframe": tf,
                    "dev_net_edge": dev_adv.performance.net_edge_r,
                    "val_net_edge": val_adv.performance.net_edge_r,
                    "oos_net_edge": oos_adv.performance.net_edge_r,
                    "oos_trades": oos_adv.trade_count,
                    "oos_win_rate": oos_adv.performance.win_rate,
                    "oos_sharpe": oos_adv.performance.annualized_sharpe,
                    "viability": viability
                })
    
    # Save reports
    results_list.sort(key=lambda x: x["oos_net_edge"], reverse=True)
    report_json_path = REPO_ROOT / "research" / "results" / "EABG003_TSMOM_REPORT.json"
    report_md_path = REPO_ROOT / "research" / "results" / "EABG003_TSMOM_REPORT.md"
    
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_json_path, "w") as f:
        json.dump({"stats": stats, "survivors": results_list}, f, indent=2)
        
    md_content = [
        "# EABG-003: TIME-SERIES MOMENTUM (TSMOM) DISCOVERY REPORT",
        "## Formal Falsification Results",
        "",
        f"- **Report Date**: {datetime.now(timezone.utc).isoformat()}",
        f"- **Total Hypotheses Tested**: {stats['total_hypotheses']}",
        f"- **Falsified (Phase 1 - Baseline)**: {stats['falsified_phase1_baseline']}",
        f"- **Falsified (Phase 2 - Adversarial Friction)**: {stats['falsified_phase2_adversarial']}",
        f"- **Falsified (Phase 3 - Locked OOS)**: {stats['falsified_phase3_oos']}",
        f"- **OOS Validated Survivors**: {stats['oos_validated']}",
        "",
        "## Survivor Candidates" if stats["oos_validated"] > 0 else "## ZERO SURVIVORS",
    ]
    
    if stats["oos_validated"] == 0:
        md_content.append("\nAll tested TSMOM hypotheses failed the rigorous multi-stage falsification pipeline. Absolute historical performance alone is insufficient to overcome institutional transaction costs and adversarial friction. **Research outcome is considered successful.**")
    else:
        for r in results_list:
            md_content.append(f"\n### {r['alpha_id']}")
            md_content.append(f"- **Strategy**: {r['strategy']} | **Asset**: {r['symbol']} | **TF**: {r['timeframe']}")
            md_content.append(f"- **Parameters**: Lookback={r['parameters']['lookback']}, VolScaled={r['parameters']['vol_scaled']}")
            md_content.append(f"- **DEV Net Edge**: {r['dev_net_edge']:.4f}R")
            md_content.append(f"- **VAL Net Edge**: {r['val_net_edge']:.4f}R")
            md_content.append(f"- **OOS Net Edge**: {r['oos_net_edge']:.4f}R (Trades: {r['oos_trades']}, WR: {r['oos_win_rate']:.2%}, Sharpe: {r['oos_sharpe']:.2f})")
            md_content.append(f"- **Capital Viability**: $10: {r['viability']['$10']} | $50: {r['viability']['$50']} | $100: {r['viability']['$100']}")
            
    with open(report_md_path, "w") as f:
        f.write("\n".join(md_content))
        
    print("\n=======================================================")
    print(f"TSMOM Discovery complete. Report saved to {report_md_path.relative_to(REPO_ROOT)}")

if __name__ == "__main__":
    main()
