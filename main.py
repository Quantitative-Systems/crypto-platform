"""STRATA Digital Trading Platform — Autonomous Production Application Main Entrypoint.

Starts the 24/7/365 autonomous trading platform:
- Multi-Tier Capital Safety Gate (Fail-Closed)
- Real-time Binance market data ingestion (WebSocket streaming)
- Continuous 7-timeframe candle engine (1M down to 3M)
- Frozen Q.2 Fractal State Engine & MTF strategy coordination
- Hard target geometry (>= 4.0R floor) & automated circuit breakers
- Multi-broker account management (Paper, Demo, Micro-Live)
- Real-time trailing stops (+2R breakeven) & simulated execution
- Append-only immutable decision ledger with SHA-256 lineage
- Continuous state reconciliation & statistical drift monitoring
- Institutional Web Terminal & REST API server
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.autonomous_supervisor import AutonomousTradingSupervisor
from execution.safety.safety_gate import EnvironmentGateMode, SAFETY_GATE
from research.contracts.frozen_contract_guard import FROZEN_GUARD
from web.server import PhaseRWebServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("STRATA_Platform")


async def async_main(args: argparse.Namespace) -> None:
    # 1. Enforce environment mode and safety gate
    req_mode = args.mode.upper()
    if req_mode in EnvironmentGateMode.__members__:
        SAFETY_GATE.transition_environment(
            EnvironmentGateMode[req_mode],
            auth_passkey=args.auth_passkey if hasattr(args, "auth_passkey") else None
        )

    logger.info("=" * 80)
    logger.info("STARTING STRATA DIGITAL TRADING PLATFORM")
    logger.info(f"ENVIRONMENT: {SAFETY_GATE.current_mode.value}")
    logger.info(f"REAL CAPITAL AUTHORIZED: ${SAFETY_GATE.real_capital_authorized_usd:.2f}")
    logger.info(f"LIVE ADAPTER STATUS: {'ENABLED' if SAFETY_GATE.is_live_execution else 'HARD-DISABLED (FAIL-CLOSED)'}")
    logger.info("=" * 80)

    # 2. Assert research contract invariants
    FROZEN_GUARD.assert_capital_safety(
        real_capital_authorized=SAFETY_GATE.real_capital_authorized_usd,
        live_trading_enabled=SAFETY_GATE.is_live_execution,
    )

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    supervisor = AutonomousTradingSupervisor(
        symbols=symbols,
        simulated_equity=args.equity,
        min_confidence=args.min_confidence,
    )

    # 3. Seed historical candle cache for immediate warm start
    seeded = supervisor.seed_historical_state()
    logger.info(f"Historical seeding completed: {seeded}")

    # 4. Start supervisor background tasks
    await supervisor.start()

    # 5. Start web application dashboard
    web_server = PhaseRWebServer(supervisor=supervisor, host=args.host, port=args.port)
    runner = await web_server.start()
    logger.info(f"STRATA Institutional Terminal live at: http://{args.host}:{args.port}/dashboard")

    # 6. Keep running until shutdown signal
    stop_event = asyncio.Event()

    def _sig_handler(*_):
        logger.info("Shutdown signal received. Stopping gracefully...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _sig_handler)
        except NotImplementedError:
            pass  # Windows signal handling fallback

    try:
        if args.dry_run_seconds > 0:
            logger.info(f"Running dry-run for {args.dry_run_seconds} seconds...")
            await asyncio.sleep(args.dry_run_seconds)
        else:
            logger.info("Operating 24/7 autonomously. Press Ctrl+C to terminate.")
            await stop_event.wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        logger.info("Shutting down web server and streaming clients...")
        await supervisor.stop()
        await runner.cleanup()
        logger.info("STRATA Platform terminated cleanly. State checkpointed.")


def main():
    parser = argparse.ArgumentParser(description="STRATA Digital Trading Platform")
    parser.add_argument("--mode", type=str, default="PAPER", choices=["PAPER", "SHADOW", "BROKER_DEMO", "MICRO_LIVE"], help="Execution mode")
    parser.add_argument("--symbols", type=str, default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT", help="Comma-separated assets")
    parser.add_argument("--equity", type=float, default=100_000.0, help="Initial simulated equity USD")
    parser.add_argument("--min-confidence", type=float, default=0.50, help="Minimum fractal confidence threshold")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Web dashboard host")
    parser.add_argument("--port", type=int, default=8080, help="Web dashboard port")
    parser.add_argument("--dry-run-seconds", type=int, default=0, help="Optional duration in seconds for automated test runs")
    parser.add_argument("--auth-passkey", type=str, default=None, help="Cryptographic passkey for live modes")

    args = parser.parse_args()
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
