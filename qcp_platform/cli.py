"""QCP Platform — command line interface.

    python3 -m qcp_platform.cli screen      # pre-trade cost economics per horizon
    python3 -m qcp_platform.cli sweep       # full walk-forward sweep + gates
    python3 -m qcp_platform.cli report      # rebuild the markdown report
    python3 -m qcp_platform.cli improve     # champion/challenger self-improvement
    python3 -m qcp_platform.cli paper       # paper-trade the promoted book set
    python3 -m qcp_platform.cli status      # what the platform currently believes

Everything writes into research/results/qcp_platform/ so results are auditable
and reproducible. No subcommand ever places a live order: this platform
promotes to PAPER only, deliberately.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import data as D
from . import report as R
from .costs import DEFAULT
from .horizons import HORIZON_ORDER

OUTDIR = os.path.join("research", "results", "qcp_platform")


def _ensure(path: str = OUTDIR) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def cmd_screen(args) -> int:
    from .runner import measure_median_atr_bps
    from .horizons import economic_screen, HORIZONS
    measured = measure_median_atr_bps()          # keyed by HORIZON
    # economic_screen() indexes by the horizon's LTF timeframe, so translate
    # the measured per-horizon medians into that namespace.
    by_tf = {HORIZONS[k].ltf: v for k, v in measured.items()}
    rows = economic_screen(DEFAULT, by_tf)
    print(R.horizon_table(measured, DEFAULT))
    out = _ensure()
    with open(os.path.join(out, "economic_screen.json"), "w") as f:
        json.dump(dict(measured_atr_bps=measured,
                       atr_bps_by_timeframe=by_tf, rows=rows), f, indent=2)
    print(f"\nwrote {os.path.join(out, 'economic_screen.json')}")
    return 0


def cmd_sweep(args) -> int:
    from .runner import run_all
    from .improve import save_baseline
    from .portfolio import run_portfolio
    from .evaluate import apply_g7
    horizons = args.horizons.split(",") if args.horizons else None
    symbols = args.symbols.split(",") if args.symbols else None
    sweep = run_all(horizons=horizons, symbols=symbols, verbose=True)
    out = _ensure()
    print(R.verdict_table(sweep.rows))
    print(R.rejection_summary(sweep.rows))
    # portfolio pass: G7 converts MEASURED (per-book gates passed) into the
    # final verdict, using marginal portfolio contribution on the OOS window.
    books = {k: v for k, v in sweep.books.items()
             if v["verdict"].verdict == "MEASURED"}
    portfolio = None
    if books:
        pf = run_portfolio(books, use_window="oos")
        sel = set(pf["selection"]["selected"])
        for k, v in sweep.books.items():
            if v["verdict"].verdict == "MEASURED":
                apply_g7(v["verdict"], passed=k in sel,
                         reason="no_marginal_sharpe_contribution")
        # Re-sync the serialized rows with the post-G7 verdicts and attach the
        # canonical book key, so verdicts.json / REPORT.md / promoted() all
        # reflect the final (G7-inclusive) verdicts. Rows that never produced
        # a book (e.g. no DEV-surviving candidate) are PRESERVED verbatim —
        # deleting negative results is reporting fraud, not reporting.
        original_rows = list(sweep.rows)
        old_notes = {(r.get("strategy"), r.get("symbol"), r.get("horizon")):
                     r.get("note", "") for r in original_rows}
        rebuilt = []
        for k, v in sweep.books.items():
            row = v["verdict"].as_row()
            row["key"] = k
            row["note"] = old_notes.get((row["strategy"], row["symbol"],
                                         row["horizon"]), "")
            rebuilt.append(row)
        covered = {(r.get("strategy"), r.get("symbol"), r.get("horizon"))
                   for r in rebuilt}
        for r0 in original_rows:
            key0 = (r0.get("strategy"), r0.get("symbol"), r0.get("horizon"))
            if key0 not in covered:
                rebuilt.append(r0)
        sweep.rows = rebuilt
        portfolio = pf["summary"]
        portfolio["selected"] = sorted(sel)
        portfolio["dropped_g7"] = [d["key"] for d in pf["selection"]["dropped"]]
        portfolio["weights"] = pf["selection"]["weights"]
        print("\nPORTFOLIO (OOS, governed):",
              json.dumps({k: portfolio[k] for k in
                          ("final_equity", "total_return", "max_drawdown",
                           "sharpe", "trades_taken", "trades_skipped")},
                         indent=2))
    R.build_report(sweep, out, portfolio=portfolio)
    save_baseline(sweep, os.path.join(out, "baseline.json"))
    print(f"\n{len(sweep.promoted())} promoted / {len(sweep.rows)} measured "
          f"in {sweep.elapsed_s}s -> {out}")
    return 0


def cmd_report(args) -> int:
    path = args.json or os.path.join(OUTDIR, "verdicts.json")
    if not os.path.exists(path):
        print(f"no sweep at {path}; run `sweep` first")
        return 1
    print(f"sweep artefacts live in {OUTDIR} (REPORT.md / verdicts.json); "
          "re-run `sweep` to regenerate them from current data")
    return 0


def cmd_improve(args) -> int:
    from .improve import improve
    out = _ensure()
    summary = improve(baseline_path=os.path.join(out, "baseline.json"),
                      out_path=os.path.join(out, "improve.json"),
                      verbose=True)
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("books", "rejected")},
                     indent=2, default=str)[:4000])
    return 0


def cmd_paper(args) -> int:
    from .runner import run_all
    from .portfolio import simulate_portfolio
    from .report import portfolio_section
    sweep = run_all(verbose=False)
    books = {k: v for k, v in sweep.books.items()
             if v["verdict"].verdict.startswith("PROMOTABLE")}
    res = simulate_portfolio(books, use_window=args.window)
    summary = res.summary()
    out = _ensure()
    with open(os.path.join(out, "paper_portfolio.json"), "w") as f:
        json.dump(dict(summary=summary, books=list(books.keys())), f, indent=2)
    print("\n".join(portfolio_section(summary)))
    return 0


def cmd_status(args) -> int:
    """Everything the platform currently believes, in one screen."""
    from .runner import measure_median_atr_bps
    from .horizons import economic_screen, HORIZONS
    print("HORIZONS")
    for k in HORIZON_ORDER:
        h = HORIZONS[k]
        print(f"  {k:9s} {h.label:34s} {h.htf:>3s}/{h.mtf:>3s}/{h.ltf:>3s}  "
              f"risk={h.fixed_risk_pct*100:.2f}%  weight={h.capital_weight:.2f}")
    print("\nCOST ECONOMICS (measured ATR)")
    print(R.horizon_table(measure_median_atr_bps(), DEFAULT))
    path = os.path.join(OUTDIR, "verdicts.json")
    if os.path.exists(path):
        with open(path) as f:
            payload = json.load(f)
        rows = payload.get("rows", [])
        prom = [r for r in rows if str(r.get("verdict", "")).startswith("PROMOTABLE")]
        print(f"\nPROMOTED BOOKS: {len(prom)} / {len(rows)} measured")
        print(R.verdict_table(prom or rows))
    else:
        print("\nno sweep yet; run `sweep`")
    print("\nLIVE CAPITAL: $0.00  (paper-only by construction)")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="qcp_platform", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("screen", help="pre-trade cost economics per horizon")
    s.set_defaults(fn=cmd_screen)

    s = sub.add_parser("sweep", help="full walk-forward sweep with gates")
    s.add_argument("--horizons", default="", help="comma list, e.g. SWING,POSITION")
    s.add_argument("--symbols", default="", help="comma list of symbols")
    s.set_defaults(fn=cmd_sweep)

    s = sub.add_parser("report", help="rebuild report from sweep.json")
    s.add_argument("--json", default="")
    s.set_defaults(fn=cmd_report)

    s = sub.add_parser("improve", help="champion/challenger self-improvement pass")
    s.set_defaults(fn=cmd_improve)

    s = sub.add_parser("paper", help="paper-trade the promoted set")
    s.add_argument("--window", default="oos", choices=["oos", "full"])
    s.set_defaults(fn=cmd_paper)

    s = sub.add_parser("status", help="current beliefs of the platform")
    s.set_defaults(fn=cmd_status)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
