"""Crypto Trading Platform — Unified Command Line Interface.

Usage:
    python3 -m crypto_platform.cli screen      # Multi-horizon economic cost screening
    python3 -m crypto_platform.cli sweep       # Full walk-forward research sweep + G1-G7 gates
    python3 -m crypto_platform.cli report      # Rebuild the research performance report
    python3 -m crypto_platform.cli improve     # Champion/challenger automated strategy discovery
    python3 -m crypto_platform.cli paper       # Run forward paper trading engine / portfolio
    python3 -m crypto_platform.cli status      # Display platform operational health and status
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from qcp_platform import cli as legacy_cli
from qcp_platform import report as R
from qcp_platform.costs import DEFAULT
from qcp_platform.evaluate import apply_g7
from qcp_platform.horizons import HORIZONS, economic_screen
from qcp_platform.portfolio import run_portfolio, simulate_portfolio
from qcp_platform.runner import measure_median_atr_bps, run_all

OUTDIR = os.path.join("research", "results", "qcp_platform")


def _ensure(path: str = OUTDIR) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def cmd_screen(args) -> int:
    return legacy_cli.cmd_screen(args)


def cmd_sweep(args) -> int:
    return legacy_cli.cmd_sweep(args)


def cmd_report(args) -> int:
    return legacy_cli.cmd_report(args)


def cmd_improve(args) -> int:
    return legacy_cli.cmd_improve(args)


def cmd_paper(args) -> int:
    """Execute paper trading with G7 portfolio gating properly resolved."""
    print("Running walk-forward research sweep to identify promoted books...")
    sweep = run_all(verbose=False)

    # Apply G7 portfolio evaluation to promote surviving books
    books_measured = {
        k: v for k, v in sweep.books.items() if v["verdict"].verdict == "MEASURED"
    }
    if books_measured:
        pf = run_portfolio(books_measured, use_window=args.window or "oos")
        selected_keys = set(pf["selection"]["selected"])
        for k, v in sweep.books.items():
            if v["verdict"].verdict == "MEASURED":
                apply_g7(
                    v["verdict"],
                    passed=k in selected_keys,
                    reason="no_marginal_sharpe_contribution",
                )

    promoted_books = {
        k: v for k, v in sweep.books.items()
        if v["verdict"].verdict.startswith("PROMOTABLE")
    }

    if not promoted_books:
        print("No strategies currently qualify for promotion under G1-G7 gates.")
        return 0

    print(f"Executing paper simulation across {len(promoted_books)} promoted books...")
    res = simulate_portfolio(promoted_books, use_window=args.window or "oos")
    summary = res.summary()

    out = _ensure()
    with open(os.path.join(out, "paper_portfolio.json"), "w") as f:
        json.dump(dict(summary=summary, books=list(promoted_books.keys())), f, indent=2)

    print("\n".join(R.portfolio_section(summary)))
    print(f"\nWrote paper portfolio results -> {os.path.join(out, 'paper_portfolio.json')}")
    return 0


def cmd_status(args) -> int:
    return legacy_cli.cmd_status(args)


def cmd_carry_stress(args) -> int:
    """Run realistic funding carry simulation and stress audit."""
    from crypto_platform.research_engine.carry_stress import CarryStressAuditor
    auditor = CarryStressAuditor()
    print("Running realistic funding carry simulation across normal and stressed regimes...")
    audit = auditor.execute_stress_matrix()
    print("\nStress Scenarios Evaluated:")
    for sc_id, data in audit["results"].items():
        print(f"  {sc_id:32} | Net Return: {data['aggregate_net_return_pct']:+6.2f}% | Win Rate: {data['aggregate_win_rate']*100:5.1f}%")
    print("\nSaved artifacts:")
    print("  research/results/crypto_platform/carry_stress_audit.json")
    print("  research/results/crypto_platform/carry_stress_report.md")
    return 0


def cmd_forward_paper(args) -> int:
    """Run forward paper trading session with live market data feeds."""
    import asyncio
    from crypto_platform.market_data.websocket_client import PublicWebSocketClient
    from crypto_platform.paper_trading.daemon import ForwardPaperTradingDaemon
    from crypto_platform.paper_trading.persistence import SQLitePaperLedger
    from crypto_platform.strategy_engine.trend import TrendBreakoutStrategy, TrendRiderStrategy
    from crypto_platform.strategy_engine.mean_reversion import BollingerMeanReversionStrategy
    from crypto_platform.strategy_engine.funding_carry import FundingCarryStrategy

    ledger = SQLitePaperLedger("research/paper_trading.db")
    daemon = ForwardPaperTradingDaemon(
        tenant_id="t_live",
        account_id="acc_paper_live",
        initial_equity=50_000.0,
        ledger=ledger,
    )
    # Register the 10 promoted strategy books across their target instruments & horizons
    # 1. INTRADAY (15m)
    daemon.register_strategy(TrendBreakoutStrategy("promoted_intraday_trend_eth", horizon="INTRADAY", supported_symbols=["ETHUSDT"]))
    daemon.register_strategy(TrendBreakoutStrategy("promoted_intraday_trend_sol", horizon="INTRADAY", supported_symbols=["SOLUSDT"]))
    daemon.register_strategy(BollingerMeanReversionStrategy("promoted_intraday_mr_ada", horizon="INTRADAY", supported_symbols=["ADAUSDT"]))
    # 2. SWING (1h)
    daemon.register_strategy(TrendBreakoutStrategy("promoted_swing_trend_eth", horizon="SWING", supported_symbols=["ETHUSDT"]))
    daemon.register_strategy(TrendBreakoutStrategy("promoted_swing_trend_sol", horizon="SWING", supported_symbols=["SOLUSDT"]))
    daemon.register_strategy(TrendBreakoutStrategy("promoted_swing_trend_ada", horizon="SWING", supported_symbols=["ADAUSDT"]))
    # 3. POSITION (4h)
    daemon.register_strategy(TrendBreakoutStrategy("promoted_pos_trend_bnb", horizon="POSITION", supported_symbols=["BNBUSDT"]))
    daemon.register_strategy(TrendBreakoutStrategy("promoted_pos_trend_ada", horizon="POSITION", supported_symbols=["ADAUSDT"]))
    daemon.register_strategy(TrendRiderStrategy("promoted_pos_rider_doge", horizon="POSITION", supported_symbols=["DOGEUSDT"]))
    # 4. CARRY (Portfolio Funding)
    daemon.register_strategy(FundingCarryStrategy("promoted_carry_portfolio", horizon="CARRY", supported_symbols=["ETHUSDT", "SOLUSDT", "ADAUSDT", "BNBUSDT", "DOGEUSDT"]))

    # Pre-warm strategy lookbacks from certified cache to eliminate cold-start starvation
    print("Pre-warming strategy lookbacks from certified market data cache...")
    daemon.warm_up(cache_dir="market_data/cache", bars=60)

    ws_client = PublicWebSocketClient(
        venue="binance",
        is_futures=False,
        timeframes=["15m", "1h", "4h"],
    )
    summary_path = "research/results/crypto_platform/forward_paper_summary.json"
    symbols = ["ETHUSDT", "SOLUSDT", "ADAUSDT", "BNBUSDT", "DOGEUSDT"]

    print(f"Starting forward paper trading daemon for {args.duration}s with public Binance feeds...")
    print(f"Active Promoted Symbols: {symbols}")
    print(f"Registered Books ({len(daemon.strategies)}): {list(daemon.strategies.keys())}")
    summary = asyncio.run(
        daemon.run_forward_session(
            duration_seconds=float(args.duration),
            symbols=symbols,
            ws_client=ws_client,
            summary_out_path=summary_path,
        )
    )
    funnel = summary.get("funnel", {})
    print("\n" + "=" * 65)
    print("FORWARD-PAPER EXECUTION FUNNEL")
    print("=" * 65)
    print(f"Market events:          {funnel.get('market_events', 0)}")
    print(f"Closed candles:         {funnel.get('closed_candles', 0)}")
    print(f"Strategy evaluations:   {funnel.get('strategy_evaluations', 0)}")
    print(f"Signals:                {funnel.get('signals', 0)}")
    print(f"Order intents:          {funnel.get('order_intents', 0)}")
    print(f"Risk accepted:          {funnel.get('risk_accepted', 0)}")
    print(f"OMS accepted:           {funnel.get('oms_acceptances', 0)}")
    print(f"Simulator submitted:    {funnel.get('simulator_submissions', 0)}")
    print(f"Resting:                {funnel.get('resting_orders', 0)}")
    print(f"Expired:                {funnel.get('expired_orders', 0)}")
    print(f"Cancelled:              {funnel.get('cancelled_orders', 0)}")
    print(f"Partial fills:          {funnel.get('partial_fills', 0)}")
    print(f"Full fills:             {funnel.get('full_fills', 0)}")
    print("=" * 65)
    if funnel.get("rejection_reasons"):
        print("REJECTION REASONS BREAKDOWN:")
        for r_code, count in funnel["rejection_reasons"].items():
            print(f"  {r_code:30}: {count}")
        print("=" * 65)
    print("Paper Trading Session Summary:")
    print(json.dumps(summary, indent=2))
    return 0


def cmd_compare(args) -> int:
    """Run Backtest vs OOS vs Forward Paper comparison report."""
    from crypto_platform.research_engine.comparison_engine import ComparisonEngine
    engine = ComparisonEngine()
    print("Building Backtest vs Validation vs OOS vs Forward Paper comparison report...")
    res = engine.build_comparison_report()
    pf = res.get("portfolio", {})
    metrics = pf.get("METRIC", [])
    dev = pf.get("HISTORICAL_DEV (2021-2022)", [])
    val = pf.get("VALIDATION (2023-2024)", [])
    oos = pf.get("OUT_OF_SAMPLE (2024-2026)", [])
    paper = pf.get("FORWARD_PAPER (LIVE FEED)", [])
    live = pf.get("LIVE_TRADING", [])

    print("\n" + "=" * 95)
    print(f"{'METRIC':<20} | {'DEV':<12} | {'VAL':<12} | {'OOS':<15} | {'FORWARD PAPER':<18} | {'LIVE'}")
    print("-" * 95)
    for i in range(len(metrics)):
        print(f"{metrics[i]:<20} | {dev[i]:<12} | {val[i]:<12} | {oos[i]:<15} | {paper[i]:<18} | {live[i]}")
    print("=" * 95)
    print("\nSaved artifacts:")
    print("  research/results/crypto_platform/backtest_vs_oos_vs_paper.json")
    print("  research/results/crypto_platform/profitability_validation_report.md")
    return 0


def cmd_soak(args) -> int:
    """Run real public WebSocket forward paper soak session."""
    import asyncio
    from crypto_platform.paper_trading.soak_runner import PaperSoakHarness
    harness = PaperSoakHarness()
    print(f"Starting forward paper trading soak session for {args.duration}s with public Binance feeds...")
    summary = asyncio.run(harness.run_soak_session(duration_seconds=float(args.duration), test_restart=True))
    print("\nSoak Session Completed Successfully:")
    print(json.dumps(summary, indent=2))
    return 0


def cmd_discover_arb(args) -> int:
    """Run relative-value / statistical arbitrage discovery across cointegrated pairs."""
    from crypto_platform.discovery.statistical_arbitrage_discovery import StatisticalArbitrageDiscovery
    disc = StatisticalArbitrageDiscovery()
    print("Executing 8-Stage Statistical Arbitrage candidate discovery...")
    summary = disc.run_discovery_campaign()
    print("\nDiscovery Campaign Summary:")
    print(json.dumps(summary, indent=2))
    return 0


def main():
    p = argparse.ArgumentParser(
        prog="crypto_platform",
        description="Crypto Trading Platform — Professional Systematic Trading Infrastructure",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # screen
    sub.add_parser("screen", help="Pre-trade cost economics per horizon")

    # sweep
    p_sw = sub.add_parser("sweep", help="Full walk-forward sweep with G1-G7 gates")
    p_sw.add_argument("--horizons", default="", help="Comma-separated horizons to run")
    p_sw.add_argument("--symbols", default="", help="Comma-separated symbols to run")

    # report
    p_rep = sub.add_parser("report", help="Rebuild the research report")
    p_rep.add_argument("--json", default="", help="Path to verdicts.json")

    # improve
    sub.add_parser("improve", help="Champion/challenger strategy improvement loop")

    # paper
    p_pap = sub.add_parser("paper", help="Paper-trade the promoted book set")
    p_pap.add_argument("--window", default="oos", choices=["dev", "oos", "full"])

    # carry-stress
    sub.add_parser("carry-stress", help="Realistic funding carry model and compression stress audit")

    # forward-paper
    p_fp = sub.add_parser("forward-paper", help="Controlled forward paper trading session with SQLite ledger")
    p_fp.add_argument("--duration", default=5.0, type=float, help="Session duration in seconds")

    # compare
    sub.add_parser("compare", help="Compare Backtest vs Validation vs OOS vs Forward Paper performance")

    # soak
    p_soak = sub.add_parser("soak", help="Public WebSocket forward paper soak session with restart verification")
    p_soak.add_argument("--duration", default=10.0, type=float, help="Soak duration in seconds")

    # discover-arb
    sub.add_parser("discover-arb", help="Discover relative-value / statistical arbitrage pair strategies")

    # status
    sub.add_parser("status", help="Current platform status and promoted books")

    # demo
    p_demo = sub.add_parser("demo", help="Run Demo / Testnet broker harness session")
    p_demo.add_argument("--venue", default="binance", choices=["binance", "bybit", "ccxt"], help="Target exchange adapter")
    p_demo.add_argument("--mock", action="store_true", default=True, help="Use deterministic contract-verified mock adapter")

    # health
    sub.add_parser("health", help="Run comprehensive system health, security, and connectivity checks")

    # web
    p_web = sub.add_parser("web", help="Launch institutional web dashboard and API gateway")
    p_web.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default 0.0.0.0)")
    p_web.add_argument("--port", default=8080, type=int, help="Port to listen on (default 8080)")

    # service (24/7 Production Supervisor)
    p_svc = sub.add_parser("service", help="Launch 24/7 continuous production trading and API supervisor")
    p_svc.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default 0.0.0.0)")
    p_svc.add_argument("--port", default=8080, type=int, help="Port to listen on (default 8080)")

    args = p.parse_args()
    dispatch = {
        "screen": cmd_screen,
        "sweep": cmd_sweep,
        "report": cmd_report,
        "improve": cmd_improve,
        "paper": cmd_paper,
        "carry-stress": cmd_carry_stress,
        "forward-paper": cmd_forward_paper,
        "compare": cmd_compare,
        "soak": cmd_soak,
        "discover-arb": cmd_discover_arb,
        "status": cmd_status,
        "demo": cmd_demo,
        "health": cmd_health,
        "web": cmd_web,
        "service": cmd_service,
    }
    sys.exit(dispatch[args.cmd](args))


def cmd_demo(args) -> int:
    """Run Demo / Testnet broker trading harness session."""
    import asyncio
    from crypto_platform.demo_trading.harness import DemoTradingHarness
    from crypto_platform.exchange_adapters.binance_adapter import BinanceAdapter
    from crypto_platform.exchange_adapters.bybit_adapter import BybitAdapter
    from crypto_platform.exchange_adapters.ccxt_adapter import CCXTAdapter
    from crypto_platform.strategy_engine.trend import TrendBreakoutStrategy

    venue = getattr(args, "venue", "binance").lower()
    print(f"Initializing Demo / Testnet broker harness on venue: {venue}...")
    if venue == "bybit":
        adapter = BybitAdapter(testnet=True, mock_mode=getattr(args, "mock", True))
    elif venue == "ccxt":
        adapter = CCXTAdapter(venue_id="kraken", mock_mode=True)
    else:
        adapter = BinanceAdapter(is_futures=True, testnet=True, mock_mode=getattr(args, "mock", True))

    harness = DemoTradingHarness(
        adapter=adapter,
        account_id=f"acc_demo_{venue}",
        initial_equity=100_000.0,
    )
    harness.register_strategy(TrendBreakoutStrategy("promoted_intraday_trend_eth", horizon="INTRADAY", supported_symbols=["ETHUSDT"]))

    async def _run():
        await harness.initialize()
        rec = await harness.reconcile()
        return harness.get_summary(), rec

    summary, reconciliation = asyncio.run(_run())
    print("\nDemo Trading Pre-Flight & State Reconciliation:")
    print(json.dumps(reconciliation, indent=2))
    print("\nDemo Trading Session Summary:")
    print(json.dumps(summary, indent=2))
    return 0


def cmd_health(args) -> int:
    """Run comprehensive platform health, configuration, and security pre-flight checks."""
    from crypto_platform.config.settings import PlatformSettings
    import os

    health_status = {
        "status": "HEALTHY",
        "live_trading_locked": True,
        "live_capital_usd": 0.0,
        "environment": "PAPER",
        "checks": {},
    }

    try:
        settings = PlatformSettings.load_from_env()
        health_status["checks"]["settings_validation"] = "PASSED"
        health_status["environment"] = settings.environment
        health_status["live_capital_usd"] = settings.live_capital_usd
    except Exception as e:
        health_status["checks"]["settings_validation"] = f"FAILED: {e}"
        health_status["status"] = "UNHEALTHY"

    # Database check
    db_file = "research/paper_trading.db"
    try:
        from crypto_platform.paper_trading.persistence import SQLitePaperLedger
        ledger = SQLitePaperLedger(db_path=db_file)
        conn = ledger._get_connection()
        conn.close()
        health_status["checks"]["database_connectivity"] = "PASSED"
    except Exception as e:
        health_status["checks"]["database_connectivity"] = f"FAILED: {e}"
        health_status["status"] = "UNHEALTHY"

    # Market data cache check
    cache_dir = "market_data/cache"
    if os.path.exists(cache_dir) and len(os.listdir(cache_dir)) > 5:
        health_status["checks"]["market_data_cache"] = f"PASSED ({len(os.listdir(cache_dir))} files)"
    else:
        health_status["checks"]["market_data_cache"] = "WARNING: Sparse cache directory"

    # Adapter endpoints check
    from crypto_platform.exchange_adapters.binance_adapter import BinanceAdapter
    b_adapter = BinanceAdapter(is_futures=True, testnet=True)
    health_status["checks"]["broker_testnet_endpoints"] = b_adapter.get_endpoints()

    print(json.dumps(health_status, indent=2))
    return 0 if health_status["status"] == "HEALTHY" else 1


def cmd_web(args) -> int:
    """Launch institutional REST and WebSocket web dashboard."""
    from aiohttp import web
    from crypto_platform.api.server import create_app
    app = create_app()
    print(f"Launching Quantitative Platform Web Dashboard at http://{args.host}:{args.port}")
    web.run_app(app, host=args.host, port=args.port)
    return 0


def cmd_service(args) -> int:
    """Launch 24/7 continuous production trading and API supervisor."""
    import asyncio
    from crypto_platform.production.supervisor import ProductionSupervisor
    supervisor = ProductionSupervisor(host=args.host, port=args.port)
    print(f"Launching 24/7 Production Supervisor at http://{args.host}:{args.port}")

    async def _run():
        await supervisor.start()
        # Keep running until cancelled
        while supervisor.is_running:
            await asyncio.sleep(1.0)

    try:
        asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit):
        asyncio.run(supervisor.stop())
    return 0


if __name__ == "__main__":
    main()

