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
    from crypto_platform.paper_trading.daemon import ForwardPaperTradingDaemon
    from crypto_platform.paper_trading.persistence import SQLitePaperLedger
    from crypto_platform.strategy_engine.trend import TrendBreakoutStrategy

    ledger = SQLitePaperLedger("research/paper_trading.db")
    daemon = ForwardPaperTradingDaemon(
        tenant_id="t_live",
        account_id="acc_paper_live",
        initial_equity=50_000.0,
        ledger=ledger,
    )
    strat = TrendBreakoutStrategy("trend_breakout_v1", lookback=10, supported_symbols=["BTCUSDT"])
    daemon.register_strategy(strat)
    print(f"Starting forward paper trading daemon for {args.duration}s...")
    summary = asyncio.run(daemon.run_forward_session(duration_seconds=float(args.duration)))
    print("Paper Trading Session Summary:")
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

    # status
    sub.add_parser("status", help="Current platform status and promoted books")

    args = p.parse_args()
    dispatch = {
        "screen": cmd_screen,
        "sweep": cmd_sweep,
        "report": cmd_report,
        "improve": cmd_improve,
        "paper": cmd_paper,
        "carry-stress": cmd_carry_stress,
        "forward-paper": cmd_forward_paper,
        "status": cmd_status,
    }
    sys.exit(dispatch[args.cmd](args))


if __name__ == "__main__":
    main()
