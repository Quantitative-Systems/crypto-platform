import sys
import json
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from market_data.data_manager import ALL_ASSETS
from research.economic_evaluation_engine import EconomicEvaluationEngine
from platform_core.alpha_genome import AlphaGenome, AlphaFamily

# Import our strategies
from strategy_engine.factory.canonical_families import (
    TrendStrategy,
    BreakoutStrategy,
    VolatilityStrategy,
    MeanReversionStrategy,
    RelativeValueStrategy,
    MomentumStrategy,
)

def main():
    print("=== 10-Asset Alpha Discovery & Profitability Hunt ===")
    
    engine = EconomicEvaluationEngine()
    timeframes = ["1d", "4h"]
    
    strategies = [
        ("Trend", TrendStrategy, AlphaFamily.DIRECTIONAL),
        ("Breakout", BreakoutStrategy, AlphaFamily.DIRECTIONAL),
        ("Volatility", VolatilityStrategy, AlphaFamily.DIRECTIONAL),
        ("MeanReversion", MeanReversionStrategy, AlphaFamily.RELATIVE_VALUE),
        ("RelativeValue", RelativeValueStrategy, AlphaFamily.RELATIVE_VALUE),
        ("Momentum", MomentumStrategy, AlphaFamily.DIRECTIONAL),
    ]
    
    results_list = []
    
    for asset in ALL_ASSETS:
        symbol = f"{asset}/USDT"
        print(f"\n--- Testing {symbol} ---")
        for tf in timeframes:
            for name, StratClass, family in strategies:
                alpha_id = f"ALPHA_{name.upper()}_{asset}_{tf}"
                
                # Create base genome
                genome = AlphaGenome(
                    alpha_id=alpha_id,
                    family=family,
                    version="1.0.0",
                    asset_universe=[symbol],
                    venues=["Binance"],
                    instruments=["SPOT"],
                    timeframe=tf,
                    expected_holding_period_hours=24.0,
                    economic_rationale=f"{name} applied to {symbol}",
                    features=["close", "high", "low"],
                    entry_mechanism=f"{name} Signal",
                    exit_mechanism="Triple Barrier",
                )
                
                strat = StratClass(strategy_id=alpha_id, family=family, symbol=symbol)
                
                res = engine.evaluate(
                    genome=genome,
                    signal_fn=strat.generate_signals,
                    symbol=symbol,
                    timeframe=tf
                )
                
                if res.status == "MEASURED" and res.overall:
                    perf = res.overall.performance
                    net_r = perf.net_edge_r
                    trades = perf.trade_count
                    print(f"[{symbol} {tf} | {name}] -> NET EDGE: {net_r:.4f}R (Trades: {trades})")
                    
                    if net_r > 0:
                        print(f"   => PROMOTED: {alpha_id} survives Friction Battery!")
                    
                    results_list.append({
                        "alpha_id": alpha_id,
                        "strategy": name,
                        "symbol": symbol,
                        "timeframe": tf,
                        "net_edge_r": net_r,
                        "trade_count": trades,
                        "win_rate": perf.win_rate,
                        "max_drawdown_r": perf.max_drawdown_r,
                        "sharpe": perf.annualized_sharpe
                    })
                else:
                    print(f"[{symbol} {tf} | {name}] -> FAILED: {res.status} | {res.notes}")
    
    # Save the report
    report_path = REPO_ROOT / "research" / "results" / "10_ASSET_ALPHA_DISCOVERY_REPORT.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Sort results by net edge (descending)
    results_list.sort(key=lambda x: x["net_edge_r"], reverse=True)
    
    report_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_evaluated": len(ALL_ASSETS) * len(timeframes) * len(strategies),
        "total_profitable": len([r for r in results_list if r["net_edge_r"] > 0]),
        "top_performers": results_list[:10],
        "all_results": results_list
    }
    
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
        
    print("\n=======================================================")
    print(f"Discovery complete. Report saved to {report_path.relative_to(REPO_ROOT)}")
    print("=== TOP 3 STRATEGIES ===")
    for i, r in enumerate(results_list[:3], 1):
        print(f"#{i}: {r['alpha_id']} -> NET: {r['net_edge_r']:.4f}R | TRADES: {r['trade_count']} | SR: {r['sharpe']:.2f}")

if __name__ == "__main__":
    main()
