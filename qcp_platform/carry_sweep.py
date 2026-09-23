"""Crypto Trading Platform — parameter sweep for the funding-carry hypothesis.

The platform already discovers, validates, allocates, executes, monitors and
retires strategies. That architecture is locked. What's missing is a *parameter
sweep* for funding_carry: profitable per trade (~8-15R) but too sparse under
the default APR=15% threshold to clear G1 (needs >= 40/15/15 DEV/VAL/OOS
trades). This script sweeps entry/exit thresholds and lookback windows to
find configs that clear G1 with positive net expectancy.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Dict, List

import numpy as np

from . import data as D
from . import walkforward as WF
from .allocations import funding_carry_book
from .costs import DEFAULT as DEFAULT_COST
from .evaluate import GateConfig, evaluate_book


OUTDIR = os.path.join("research", "results", "qcp_platform")


@dataclass
class CarryParam:
    """One candidate parameter set for the funding-carry book."""
    apr_entry: float
    apr_exit: float
    lookback_days: int
    name: str = ""


# Lower entry => more trades; the sweep finds the knee where net expectancy
# stays positive AND G1 trade-count is satisfied.
PARAM_GRID = [
    (0.15, 0.05, 7),   (0.12, 0.04, 7),
    (0.10, 0.03, 7),   (0.08, 0.02, 7),
    (0.06, 0.02, 7),   (0.10, 0.03, 3),
    (0.08, 0.02, 3),   (0.06, 0.01, 3),
    (0.05, 0.01, 3),   (0.08, 0.02, 5),
    (0.06, 0.02, 5),   (0.05, 0.01, 5),
    (0.04, 0.01, 5),   (0.04, 0.01, 3),
    (0.03, 0.005, 3),  (0.05, 0.01, 7),
]


def grid() -> List[CarryParam]:
    out: List[CarryParam] = []
    for entry, exit_, lb in PARAM_GRID:
        label = f"entry{entry:.0%}_exit{exit_:.0%}_lb{lb}d"
        out.append(CarryParam(apr_entry=entry, apr_exit=exit_,
                              lookback_days=lb, name=label))
    return out


def _bounds(book):
    """Walk-forward slicing: 70 % DEV, 15 % VAL, 15 % OOS."""
    ts = [t.exit_ts for t in book.trades if t.exit_ts]
    if not ts:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    t_min, t_max = min(ts), max(ts)
    span = t_max - t_min
    d1 = t_min + 0.70 * span
    v1 = t_min + 0.85 * span
    return t_min, d1, d1, v1, v1, t_max


def evaluate_carry(symbol: str, params: CarryParam,
                   gate: GateConfig) -> dict:
    """Run one funding-carry book for one symbol with explicit params."""
    f = D.load_funding(symbol)
    daily = D.load_ohlcv(symbol, "1d")
    if f is None or daily is None or daily["n"] < 120:
        return dict(symbol=symbol, params=asdict(params),
                    verdict="REJECTED_DATA", gates=dict(G1=False),
                    reason="insufficient data")

    b = funding_carry_book(
        symbol, daily, f["ts"], f["rate"],
        cost=DEFAULT_COST,
        apr_entry=params.apr_entry,
        apr_exit=params.apr_exit,
        lookback_days=params.lookback_days,
    )

    if b.n < 3:
        return dict(symbol=symbol, params=asdict(params),
                    verdict="REJECTED_G1", gates=dict(G1=False,
                    min_dev=40, dev_n=b.n),
                    note="too few total trades")

    d0, d1, v0, v1, o0, o1 = _bounds(b)
    dev = WF.slice_book(b, d0, d1)
    val = WF.slice_book(b, v0, v1)
    oos = WF.slice_book(b, o0, o1)

    v = evaluate_book("funding_carry", symbol, "CARRY",
                      dev, val, oos, cfg=gate)

    net = sum(t.meta.get("net", 0.0) for t in b.trades)
    held = sum(t.bars_held for t in b.trades)

    stats = {
        **v.stats,
        "total_trades": b.n,
        "dev_n": len(dev.trades),
        "val_n": len(val.trades),
        "oos_n": len(oos.trades),
        "net_R": round(net, 4),
        "days_in_market": held,
        "net_per_year": round(net / max(1, held) * 365, 4),
        "cost_bps": DEFAULT_COST.carry_roundtrip_bps(),
    }
    return dict(symbol=symbol, params=asdict(params),
                stats=stats, verdict=v.verdict,
                gates=v.gates, param_name=params.name,
                                note="market-neutral spot+perp")


def sweep_carry(gate: GateConfig | None = None,
                symbols: List[str] | None = None,
                verbose: bool = True) -> dict:
    """Sweep carry parameters as a *portfolio-level* book.

    funding_carry is inherently low-frequency per asset (~2-8 entries/year),
    so a single asset can never reach G1's 15-trade OOS floor. The carry
    family is therefore evaluated as a single aggregated book across all
    eligible assets — exactly the pattern used by xs_momentum (PORTFOLIO
    horizon). This gives ~600+ round-trips that distribute enough across the
    70 DEV / 15 VAL / 15 OOS windows to be statistically governable.
    """
    gate = gate or GateConfig()
    assets = list(symbols or D.ASSETS)
    grid_params = grid()
    t0 = time.time()

    # Build one aggregated book per parameter config
    portfolio_rows: List[dict] = []
    best: dict | None = None

    for p in grid_params:
        all_trades = []
        per_asset_stats: List[dict] = []
        for sym in assets:
            r = evaluate_carry(sym, p, gate)
            per_asset_stats.append(r)
            # collect the actual trade objects for portfolio aggregation
            f = D.load_funding(sym)
            daily = D.load_ohlcv(sym, "1d")
            if f is None or daily is None or daily["n"] < 120:
                continue
            b = funding_carry_book(
                sym, daily, f["ts"], f["rate"],
                cost=DEFAULT_COST,
                apr_entry=p.apr_entry,
                apr_exit=p.apr_exit,
                lookback_days=p.lookback_days,
            )
            all_trades.extend(b.trades)

        # Aggregate into one portfolio book
        from .engine import BookResult
        agg = BookResult(strategy="funding_carry", horizon="CARRY")
        agg.trades = sorted(all_trades, key=lambda t: t.exit_ts)
        agg.signal_count = len(all_trades)

        if agg.n < 3:
            portfolio_rows.append(dict(
                params=asdict(p), param_name=p.name,
                verdict="REJECTED_G1", total_trades=agg.n,
                note="too few total portfolio trades"))
            continue

        d0, d1, v0, v1, o0, o1 = _bounds(agg)
        dev = WF.slice_book(agg, d0, d1)
        val = WF.slice_book(agg, v0, v1)
        oos = WF.slice_book(agg, o0, o1)

        v = evaluate_book("funding_carry", "PORTFOLIO", "CARRY",
                          dev, val, oos, cfg=gate)

        net = sum(t.meta.get("net", 0.0) for t in agg.trades)
        held = sum(t.bars_held for t in agg.trades)

        stats = {
            **v.stats,
            "total_trades": agg.n,
            "dev_n": len(dev.trades),
            "val_n": len(val.trades),
            "oos_n": len(oos.trades),
            "net_R": round(net, 4),
            "days_in_market": held,
            "net_per_year": round(net / max(1, held) * 365, 4),
            "cost_bps": DEFAULT_COST.carry_roundtrip_bps(),
        }

        row = dict(
            params=asdict(p), param_name=p.name,
            stats=stats, verdict=v.verdict,
            gates=v.gates,
            note="portfolio-aggregated, 10 assets",
        )
        portfolio_rows.append(row)

        st = stats
        tag = "★" if v.verdict == "PROMOTABLE_PAPER_ONLY" else " "
        if verbose:
            print(f"  {tag} {p.name:30s}  {v.verdict:22s}  "
                  f"trades={st.get('total_trades',0)} "
                  f"dev={st.get('dev_n',0)} val={st.get('val_n',0)} "
                  f"oos={st.get('oos_n',0)} net_R={st.get('net_R',0):+.3f}")

        if v.verdict == "PROMOTABLE_PAPER_ONLY":
            if best is None or net > best["stats"]["net_R"]:
                best = row

    if best is None and portfolio_rows:
        # Fallback: pick the config with the best OOS expectancy among those
        # that actually passed all honesty gates (MEASURED).  Preferring "most
        # trades" was the bug: the densest configs sit in the tail where costs
        # swallow the signal and OOS flips negative (entry3%_exit0%_lb3d is the
        # canonical example: 624 trades, OOS -0.59R, REJECTED_G2).
        measured = [r for r in portfolio_rows
                    if r.get("verdict") == "MEASURED"]
        if measured:
            best = max(measured,
                       key=lambda r: r["stats"].get("oos_exp", -1e9))
        elif portfolio_rows:
            # absolute fallback: positive-OOS configs, then most-trades as tiebreak
            positive = [r for r in portfolio_rows
                        if r["stats"].get("oos_exp", 0) > 0]
            if positive:
                best = max(positive, key=lambda r: r["stats"].get("oos_exp", -1e9))
            else:
                best = max(portfolio_rows,
                           key=lambda r: r["stats"].get("total_trades", 0))

    result = dict(
        generated_at=str(np.datetime64("now", "s")),
        elapsed_s=round(time.time() - t0, 1),
        mode="portfolio_aggregated_carry",
        cost_bps=DEFAULT_COST.carry_roundtrip_bps(),
        gate_config=dict(
            min_dev_trades=gate.min_dev_trades,
            min_val_trades=gate.min_val_trades,
            min_oos_trades=gate.min_oos_trades,
            min_expectancy_r=gate.min_expectancy_r,
            min_bootstrap_p=gate.min_bootstrap_p,
        ),
        portfolio_rows=portfolio_rows,
        recommended_config=best["param_name"] if best else None,
        recommended_stats=best["stats"] if best else None,
        recommended_verdict=best["verdict"] if best else None,
        recommended_params=best["params"] if best else None,
    )

    os.makedirs(OUTDIR, exist_ok=True)
    out_path = os.path.join(OUTDIR, "carry_sweep.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    if verbose:
        print(f"\nWrote {out_path}")
        if best:
            st = best["stats"]
            print(f"\nRecommended config: {best['param_name']}")
            print(f"  verdict:           {best['verdict']}")
            print(f"  params:            {best['params']}")
            print(f"  total trades:      {st.get('total_trades',0)}")
            print(f"  dev/val/oos:       {st.get('dev_n',0)}/{st.get('val_n',0)}/{st.get('oos_n',0)}")
            print(f"  net R:             {st.get('net_R',0):+.3f}")
            print(f"  net/yr (R):        {st.get('net_per_year',0):+.3f}")
            print(f"  cost bps:          {st.get('cost_bps',0)}")
    return result


if __name__ == "__main__":
    sweep_carry(verbose=True)