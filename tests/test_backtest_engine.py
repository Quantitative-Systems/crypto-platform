"""
Product 01: Crypto Platform - Real Market Data Replay & Analytics Test Suite
Replays 1,000+ real Binance historical candles across BTC/USDT and computes true telemetry.
"""

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from market_data.warehouse_loader import WarehouseLoader
from backtesting.replay_engine import ReplayEngine
from backtesting.performance_analytics import PerformanceAnalytics


def run_real_backtest_suite():
    print("==========================================================================================================")
    print("     PRODUCT 01: REAL BINANCE MARKET DATA REPLAY & PERFORMANCE TELEMETRY")
    print("==========================================================================================================\n")

    symbol = "BTC/USDT"
    print(f"🌐 [REAL DATA INGESTION]: Querying Binance Public Market Data for {symbol}...")
    htf_candles = WarehouseLoader.load_history(symbol, "1D", limit=500)
    mtf_candles = WarehouseLoader.load_history(symbol, "4H", limit=800)
    ltf_candles = WarehouseLoader.load_history(symbol, "1H", limit=1000)

    print(f"  • Real Market Data Loaded: {len(htf_candles)} HTF (1D) bars | {len(mtf_candles)} MTF (4H) bars | {len(ltf_candles)} LTF (1H) bars")

    # Run Zero-Lookahead Market Replay on Real Binance Candles
    replay = ReplayEngine(swing_lookback=2)
    print("\n⏳ [ZERO-LOOKAHEAD REPLAY]: Replaying real market history bar-by-bar ($1,000 Starting Equity)...")
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

    print("\n🔍 [PIPELINE DIAGNOSTIC GATE FUNNEL REPORT]:")
    print(f"  • Total Real Bars Evaluated : {telemetry['total_bars_evaluated']}")
    print(f"  • Gate 1 Fails (HTF)        : {telemetry['gate_1_htf_fails']} bars")
    print(f"  • Gate 2 Fails (MTF)        : {telemetry['gate_2_mtf_fails']} bars")
    print(f"  • Gate 3 Fails (LTF)        : {telemetry['gate_3_ltf_fails']} bars")
    print(f"  • Gate 4 Fails (Risk)       : {telemetry['gate_4_risk_fails']} bars")
    print(f"  • Real Trades Approved      : {telemetry['trades_approved']} trades")

    # Calculate 18-Point Performance Report
    metrics = PerformanceAnalytics.compute_deep_metrics(history, starting_balance=1000.0)

    print("\n📊 [INSTITUTIONAL PERFORMANCE TELEMETRY REPORT]:")
    print(f"  • Starting Equity      : ${metrics.get('starting_balance', 1000.0):,.2f}")
    print(f"  • Final Net Equity     : ${metrics.get('final_balance', 1000.0):,.2f}")
    print(f"  • Net Dollar Return    : +${metrics.get('net_pnl_usd', 0.0):,.2f} ({metrics.get('net_return_pct', 0.0):+.1f}%)")
    print(f"  • Total Executed Trades: {metrics.get('total_trades', 0)}")
    print(f"  • Win Rate (%)         : {metrics.get('win_rate_pct', 0.0):.1f}%")
    print(f"  • Profit Factor        : {metrics.get('profit_factor', 0.0):.2f}")
    print(f"  • Max Drawdown (%)     : {metrics.get('max_drawdown_pct', 0.0):.2f}%")
    print(f"  • Sharpe Ratio (Ann.)  : {metrics.get('sharpe_ratio', 0.0):.2f}")
    print(f"  • Calmar Ratio         : {metrics.get('calmar_ratio', 0.0):.2f}")
    print(f"  • Longest Win Streak   : {metrics.get('max_win_streak', 0)} consecutive wins")
    print(f"  • Longest Loss Streak  : {metrics.get('max_loss_streak', 0)} consecutive losses")
    print(f"  • LONG Win Rate        : {metrics.get('long_win_rate', 0.0):.1f}% ({metrics.get('long_trades', 0)} trades)")
    print(f"  • SHORT Win Rate       : {metrics.get('short_win_rate', 0.0):.1f}% ({metrics.get('short_trades', 0)} trades)")

    print("\n==========================================================================================================")
    print("  ✅ STAGE 3 INITIALIZED: Real Binance Market Data Ingestion & Replay Complete!")
    print("==========================================================================================================")


if __name__ == "__main__":
    run_real_backtest_suite()