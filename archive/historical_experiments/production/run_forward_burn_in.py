"""
Quantitative Crypto Platform (QCP) — Continuous Forward Paper Daemon Operational Entrypoint.

Starts continuous forward paper execution for SOL Set 2 (Primary Robust Candidate)
in background burn-in observation mode:
- Polls live Binance public closed candles (zero API keys).
- Feeds closed bars through CanonicalSignalEngine and 7D PortfolioRiskFirewall.
- Simulates execution with Adverse-First collision policy.
- Logs Model-vs-Reality deltas and continuous JSON heartbeats.
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_core.canonical_strategy_spec import create_fam07_spec, StrategyLifecycleState
from production.forward_paper_daemon import ForwardPaperDaemon, DaemonConfig

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="QCP Forward Paper Daemon Burn-in")
    parser.add_argument("--symbol", default="SOL/USDT", help="Trading pair symbol")
    parser.add_argument("--interval", type=float, default=15.0, help="Polling interval in seconds")
    parser.add_argument("--capital", type=float, default=1000.0, help="Starting capital USD")
    parser.add_argument("--dry-run", action="store_true", help="Execute single cycle then exit")
    args = parser.parse_args()

    config = DaemonConfig(
        symbol=args.symbol,
        poll_interval_sec=args.interval,
        starting_capital=args.capital,
        state_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_daemon_state.json"),
        audit_file=os.path.join(RESULTS_DIR, "FORWARD_PAPER_DAEMON_AUDIT.json"),
        heartbeat_interval_sec=60.0,
    )

    spec = create_fam07_spec(
        symbol=args.symbol,
        timeframe_set=2,
        lifecycle_state=StrategyLifecycleState.QUALIFIED_ROBUST,
        notes="Primary robust candidate under continuous forward paper burn-in",
    )

    print("=" * 80)
    print("QUANTITATIVE CRYPTO PLATFORM (QCP) — FORWARD PAPER DAEMON BURN-IN")
    print(f"Target Symbol: {args.symbol} | Strategy: {spec.strategy_id}")
    print(f"Starting Capital: ${args.capital:,.2f} | Polling Interval: {args.interval}s")
    print(f"Audit File: {config.audit_file}")
    print("=" * 80)

    daemon = ForwardPaperDaemon(config=config, strategy_spec=spec)

    if args.dry_run:
        print("[Burn-in] Executing dry-run single cycle verification...")
        res = daemon.run_cycle()
        print(f"[Burn-in] Cycle Status: {res['status']} | Active Positions: {res['active_positions']}")
        print("✅ Dry-run cycle complete.")
        return

    daemon.start()


if __name__ == "__main__":
    main()
