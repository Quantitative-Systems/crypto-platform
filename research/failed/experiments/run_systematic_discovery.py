import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_data.data_manager import ALL_ASSETS
from research.economic_evaluation_engine import EconomicEvaluationEngine, CausalTripleBarrierBacktester, BacktestConfig
from backtesting.friction_model import FrictionModel
from research.alpha_matrix.blueprints.scalp_blueprint import ScalpBlueprint
from research.alpha_matrix.blueprints.macro_scalp_blueprint import MacroScalpBlueprint
from research.alpha_matrix.blueprints.intraday_blueprint import IntradayBlueprint
from research.alpha_matrix.blueprints.swing_blueprint import SwingBlueprint
from research.alpha_matrix.blueprints.positional_blueprint import PositionalBlueprint
from research.alpha_matrix.blueprints.macro_investing_blueprint import MacroInvestingBlueprint

def main():
    print("================================================================")
    print("QCP SYSTEMATIC ALPHA DISCOVERY ENGINE")
    print("Evaluating 6 Trading Styles Across 10 Assets")
    print("================================================================\n")
    
    # Standard engine (Taker fees)
    standard_config = BacktestConfig(target_r_multiple=1.35, max_holding_bars=20)
    standard_backtester = CausalTripleBarrierBacktester(config=standard_config)
    engine = EconomicEvaluationEngine(backtester=standard_backtester, min_trades_per_partition=1)
    
    # 2) For Scalping: We mathematically *must* use Limit Orders (Maker Rebates).
    #    Otherwise, the spread+fee crushes the 1m/5m timeframe.
    maker_friction = FrictionModel(taker_fee_pct=-0.00010, slippage_pct=0.0, spread_pct=0.0) # -0.01% rebate for maker
    maker_config = BacktestConfig(target_r_multiple=1.35, max_holding_bars=10)
    maker_backtester = CausalTripleBarrierBacktester(friction=maker_friction, config=maker_config)
    maker_engine = EconomicEvaluationEngine(backtester=maker_backtester, min_trades_per_partition=1)
    
    # We will test all 10 assets
    universe = [f"{asset}/USDT" for asset in ALL_ASSETS]
    
    results_list = []
    
    for symbol in universe:
        print(f"\n--- Testing Asset: {symbol} ---")
        
        # 1. MICRO_SCALP (1m)
        print("  Evaluating MICRO_SCALP (1m)...")
        genome_micro = ScalpBlueprint.construct_statarb_genome(symbol)
        res_micro = maker_engine.evaluate(
            genome=genome_micro,
            signal_fn=lambda df: ScalpBlueprint.generate_zscore_signal(df, df), # Dummy 2-leg for single asset test
            symbol=symbol,
            timeframe="1m",
            partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
        )
        _process_result("MICRO_SCALP", symbol, "1m", res_micro, results_list)
        
        # 2. MACRO_SCALP (5m)
        print("  Evaluating MACRO_SCALP (5m)...")
        genome_macro_scalp = MacroScalpBlueprint.construct_orderflow_genome(symbol)
        res_macro_scalp = maker_engine.evaluate(
            genome=genome_macro_scalp,
            signal_fn=MacroScalpBlueprint.generate_volume_fade_signal,
            symbol=symbol,
            timeframe="5m",
            partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
        )
        _process_result("MACRO_SCALP", symbol, "5m", res_macro_scalp, results_list)
        
        # 3. INTRADAY (15m)
        print("  Evaluating INTRADAY (15m)...")
        genome_intra = IntradayBlueprint.construct_mean_reversion_genome(symbol)
        res_intra = engine.evaluate(
            genome=genome_intra,
            signal_fn=IntradayBlueprint.generate_rsi_fade_signal,
            symbol=symbol,
            timeframe="15m",
            partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
        )
        _process_result("INTRADAY", symbol, "15m", res_intra, results_list)
        
        # 4. SWING (4h)
        print("  Evaluating SWING (4h)...")
        genome_swing = SwingBlueprint.construct_momentum_genome(symbol)
        res_swing = engine.evaluate(
            genome=genome_swing,
            signal_fn=SwingBlueprint.generate_macd_signal,
            symbol=symbol,
            timeframe="4h",
            partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
        )
        _process_result("SWING", symbol, "4h", res_swing, results_list)
        
        # 5. POSITIONAL (1d) - Uses Funding Arb eval engine
        print("  Evaluating POSITIONAL (1d)...")
        genome_pos = PositionalBlueprint.construct_funding_arb_genome(symbol)
        res_pos = engine.evaluate_funding_arbitrage(
            genome=genome_pos,
            signal_fn=PositionalBlueprint.generate_funding_signal,
            symbol=symbol,
            timeframe="1d",
            partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
        )
        _process_result("POSITIONAL", symbol, "1d", res_pos, results_list)
        
        # 6. MACRO_INVESTING (1w)
        print("  Evaluating MACRO_INVESTING (1w)...")
        genome_macro_inv = MacroInvestingBlueprint.construct_macro_trend_genome(symbol)
        res_macro_inv = engine.evaluate(
            genome=genome_macro_inv,
            signal_fn=MacroInvestingBlueprint.generate_macro_signal,
            symbol=symbol,
            timeframe="1w",
            partitions=[("ALL_DATA", "2000-01-01", "2030-01-01")]
        )
        _process_result("MACRO_INVESTING", symbol, "1w", res_macro_inv, results_list)

    # Save the master report
    _save_report(results_list)

def _process_result(style, symbol, tf, res, results_list):
    if res.status == "MEASURED" and res.overall:
        perf = res.overall.performance
        net_r = perf.net_edge_r
        trades = perf.trade_count
        print(f"    -> [MEASURED] NET EDGE: {net_r:.4f}R (Trades: {trades})")
        
        if net_r > 0:
            print(f"       => PROMOTED: {style} on {symbol} survives Friction Battery!")
            
        results_list.append({
            "style": style,
            "alpha_id": res.alpha_id,
            "symbol": symbol,
            "timeframe": tf,
            "net_edge_r": net_r,
            "trade_count": trades,
            "win_rate": perf.win_rate,
            "max_drawdown_r": perf.max_drawdown_r,
            "sharpe": perf.annualized_sharpe
        })
    else:
        print(f"    -> [FAILED] Status: {res.status} | Notes: {res.notes}")

def _save_report(results_list):
    report_path = Path("research/results/SYSTEMATIC_ALPHA_PORTFOLIO.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Sort results by net edge (descending)
    results_list.sort(key=lambda x: x["net_edge_r"], reverse=True)
    
    report_data = {
        "total_evaluated": len(ALL_ASSETS) * 6,
        "total_profitable": len([r for r in results_list if r["net_edge_r"] > 0]),
        "top_performers": results_list[:15],
        "all_results": results_list
    }
    
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
        
    print("\n=======================================================")
    print(f"Systematic Discovery complete. Report saved to {report_path}")
    print("=== TOP 5 STRATEGIES ===")
    for i, r in enumerate(results_list[:5], 1):
        print(f"#{i}: {r['style']} {r['symbol']} -> NET: {r['net_edge_r']:.4f}R | TRADES: {r['trade_count']}")

if __name__ == "__main__":
    main()
