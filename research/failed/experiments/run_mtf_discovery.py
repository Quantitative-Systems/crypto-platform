import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_data.data_manager import ALL_ASSETS
from research.economic_evaluation_engine import EconomicEvaluationEngine, CausalTripleBarrierBacktester, BacktestConfig
from backtesting.friction_model import FrictionModel
from research.alpha_matrix.blueprints.mtf_blueprint import MTFBlueprint

def main():
    print("================================================================")
    print("QCP MTF TRAILING DISCOVERY ENGINE")
    print("Evaluating MTF 1:4 RR System Across 10 Assets")
    print("================================================================\n")
    
    # Standard configuration with 1:4 RR and trailing stop
    # 1R = 1% Risk 
    mtf_config = BacktestConfig(
        target_r_multiple=10.0, 
        max_holding_bars=100, 
        use_trailing_stop=True,
        apply_borrow_financing=True
    )
    mtf_backtester = CausalTripleBarrierBacktester(config=mtf_config)
    engine = EconomicEvaluationEngine(backtester=mtf_backtester, min_trades_per_partition=1)
    
    universe = [f"{asset}/USDT" for asset in ALL_ASSETS]
    results_list = []
    
    for symbol in universe:
        print(f"\n--- Testing Asset: {symbol} ---")
        print("  Evaluating MTF Strategy (HTF: 4h, MTF: 15m, LTF: 5m)...")
        
        genome_mtf = MTFBlueprint.construct_mtf_genome(symbol, ltf="5m", mtf="15m", htf="4h")
        
        # We wrap the signal_fn in a lambda to pass the symbol down to the blueprint
        # so it can fetch the correct MTF and HTF data.
        res_mtf = engine.evaluate(
            genome=genome_mtf,
            signal_fn=lambda df: MTFBlueprint.generate_mtf_signal(df, symbol, mtf="15m", htf="4h"),
            symbol=symbol,
            timeframe="5m",
            partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
        )
        
        _process_result("MTF_TREND", symbol, "5m", res_mtf, results_list)

    # Save the master report
    _save_report(results_list)

def _process_result(style, symbol, tf, res, results_list):
    if res.status == "MEASURED" and res.overall:
        perf = res.overall.performance
        net_r = perf.net_edge_r
        trades = perf.trade_count
        print(f"    -> [MEASURED] NET EDGE: {net_r:.4f}R (Trades: {trades})")
        print(f"       Win Rate: {perf.win_rate:.2f}% | Profit Factor: {perf.profit_factor:.2f}")
        
        if net_r > 0:
            print(f"       => PROMOTED: {style} on {symbol} is Profitable!")
            
        results_list.append({
            "style": style,
            "alpha_id": res.alpha_id,
            "symbol": symbol,
            "timeframe": tf,
            "net_edge_r": net_r,
            "trade_count": trades,
            "win_rate": perf.win_rate,
            "profit_factor": perf.profit_factor,
            "max_drawdown_r": perf.max_drawdown_r,
            "sharpe": perf.annualized_sharpe
        })
    else:
        print(f"    -> [FAILED] Status: {res.status} | Notes: {res.notes}")

def _save_report(results_list):
    report_path = Path("research/results/MTF_ALPHA_PORTFOLIO.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Sort results by net edge (descending)
    results_list.sort(key=lambda x: x["net_edge_r"], reverse=True)
    
    report_data = {
        "total_evaluated": len(ALL_ASSETS),
        "total_profitable": len([r for r in results_list if r["net_edge_r"] > 0]),
        "top_performers": results_list[:15],
        "all_results": results_list
    }
    
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
        
    print("\n=======================================================")
    print(f"MTF Discovery complete. Report saved to {report_path}")
    print("=== TOP STRATEGIES ===")
    for i, r in enumerate(results_list[:5], 1):
        print(f"#{i}: {r['style']} {r['symbol']} -> NET: {r['net_edge_r']:.4f}R | TRADES: {r['trade_count']} | WR: {r['win_rate']}%")

if __name__ == "__main__":
    main()
