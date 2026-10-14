"""Crypto Engine — 24/7/365 Production Execution Entrypoint.

Starts the unified institutional fund daemon executing exclusively filter-passed
production champions across all 5 multi-horizon timeframe sets.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.autonomous_self_evolving_daemon import SelfEvolvingFundDaemon
from crypto_engine.pipeline.promotion_gate import ProductionPromotionGate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("CryptoEngineProduction")


def main():
    print("=" * 90)
    print("           CRYPTO ENGINE — 24/7/365 AUTONOMOUS PRODUCTION FUND           ")
    print("=" * 90)

    # 1. Load Filter-Passed Certified Production Champions
    champions = ProductionPromotionGate.list_live_champions()
    champion_symbols = list({meta.get("symbol") for meta in champions.values() if meta.get("symbol")})
    active_symbols = champion_symbols if champion_symbols else ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

    broker_mode = os.environ.get("BROKER_MODE", "PAPER").upper()
    equity = float(os.environ.get("ACCOUNT_EQUITY_USD", "100000.0"))

    print(f"Operational Mode: {broker_mode} | Active Capital: ${equity:,.2f}")
    print(f"Certified Production Models: {len(champions)}")
    print(f"Active Production Tickers: {active_symbols}")
    print("Mathematical Framework: 3 Universal Primitives (Structure, KeyZones, Phases)")
    print("Execution Governance: 1% Risk Sizing | >= 4.0R Target | 1.5x ATR Floor")
    print("-" * 90)

    daemon = SelfEvolvingFundDaemon(
        active_symbols=active_symbols,
        account_equity_usd=equity,
        broker_mode=broker_mode,
        research_interval_seconds=3600,
    )

    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        logger.info("Production shutdown requested by operator.")


if __name__ == "__main__":
    main()
