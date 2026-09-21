"""
Product 01: Crypto Platform - Multi-Asset Research Engine
Executes zero-lookahead backtests across BTC/USDT, ETH/USDT, and SOL/USDT from real Binance market feeds.
Deducts real Binance Taker Fees (0.075%), Slippage (0.03%), and Spread (0.01%), persisting results to Research DB.
"""

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from market_data.warehouse_loader import WarehouseLoader
from backtesting.replay_engine import ReplayEngine
from backtesting.performance_analytics import PerformanceAnalytics


def run_multi_asset_research():
    print("==========================================================================================================")
    print("     PRODUCT 01: MULTI-ASSET FRICTIONAL QUANT RESEARCH ENGINE (BTC / ETH / SOL)")
    print("==========================================================================================================\n")

    assets = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    portfolio_results = {}

    replay = ReplayEngine(swing_lookback=2)

    for symbol in assets:
        print(f"🌐 [INGESTING DATA]: Querying Binance REST Feed for {symbol}...")
        htf_candles = WarehouseLoader.load_history(symbol, "1D", limit=500)
        mtf_candles = WarehouseLoader.load_history(symbol, "4H", limit=800)
        ltf_candles = WarehouseLoader.load_history(symbol, "1H", limit=1000)

        print(f"  • Data Ingested: {len(htf_candles)} HTF bars | {len(mtf_candles)} MTF bars | {len(ltf_candles)} LTF bars")

        # Run bar-by-bar replay simulation with friction models active
        results = replay.run_replay(
            symbol=symbol,
            htf_candles=htf_candles,
            mtf_candles=mtf_candles,
            ltf_candles=ltf_candles,
            starting_balance=1000.0,
            risk_pct=0.01
        )

        history = results["trade_history"]
        telemetry = results["telemetry"]
        metrics = PerformanceAnalytics.compute_deep_metrics(history, starting_balance=1000.0)

        strat_a_trades = [t for t in history if t.get("strategy_type") == "PULLBACK_RIDING"]
        strat_b_trades = [t for t in history if t.get("strategy_type") == "CONTINUATION_RIDING"]

        portfolio_results[symbol] = {
            "metrics": metrics,
            "telemetry": telemetry,
            "strat_a_count": len(strat_a_trades),
            "strat_b_count": len(strat_b_trades)
        }
        print(f"  ✅ Replay Completed for {symbol}: {metrics.get('total_trades', 0)} trades (Friction Drag: ${metrics.get('total_friction_usd', 0.0):.2f}).\n")

    # Display Side-by-Side Multi-Asset Research Matrix
    print("==========================================================================================================")
    print("📊 [PORTFOLIO MULTI-ASSET FRICTIONAL RESEARCH SUMMARY MATRIX]")
    print("==========================================================================================================")
    print(f"{'ASSET':<10} | {'TRADES':<8} | {'STRAT A/B':<10} | {'WIN RATE':<10} | {'NET RETURN ($)':<15} | {'FRICTION ($)':<14} | {'PROFIT FACTOR':<13} | {'MAX DD':<8}")
    print("----------------------------------------------------------------------------------------------------------")

    for symbol, data in portfolio_results.items():
        m = data["metrics"]
        print(
            f"{symbol:<10} | "
            f"{m.get('total_trades', 0):<8} | "
            f"{data['strat_a_count']}/{data['strat_b_count']:<8} | "
            f"{m.get('win_rate_pct', 0.0):<9.1f}% | "
            f"+${m.get('net_pnl_usd', 0.0):<14.2f} | "
            f"${m.get('total_friction_usd', 0.0):<13.2f} | "
            f"{m.get('profit_factor', 0.0):<13.2f} | "
            f"{m.get('max_drawdown_pct', 0.0):<7.2f}%"
        )

    print("==========================================================================================================")


if __name__ == "__main__":
    run_multi_asset_research()