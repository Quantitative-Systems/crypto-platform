"""QCP Platform — report generation (markdown + JSON artefacts).

Every number in the report is produced by the measurement pipeline in this
package and is reproducible from the local cache. The report deliberately leads
with what did NOT work: the rejected horizons are the load-bearing part of the
argument that the accepted ones are real.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

import numpy as np

from . import runner as R
from .costs import DEFAULT, MEDIAN_ATR_BPS, CostModel
from .evaluate import PROMOTABLE
from .horizons import HORIZONS, HORIZON_ORDER


def _fmt(v, nd=3):
    return f"{v:+.{nd}f}" if isinstance(v, float) else str(v)


def horizon_table(median_atr: Dict[str, float], cost: CostModel) -> str:
    rows = ["| Horizon | Clocks (HTF/MTF/LTF) | Style | Median ATR (bps) |"
            " Stop (bps) | Cost (bps) | Cost/Stop | Verdict |",
            "|---|---|---|---|---|---|---|---|"]
    for key in HORIZON_ORDER:
        h = HORIZONS[key]
        clocks = f"{h.htf}/{h.mtf}/{h.ltf}"
        if h.atr_mult <= 0:
            rows.append(f"| **{key}** | {clocks} | {h.style} | — | — | "
                        f"{cost.carry_roundtrip_bps():.0f} | — | "
                        f"market-neutral (vs funding yield) |")
            continue
        a = median_atr.get(key, MEDIAN_ATR_BPS.get(h.ltf, 0.0))
        stop = a * h.atr_mult
        rt = cost.roundtrip_bps(h.maker_entry, h.maker_entry)
        ratio = rt / stop if stop > 0 else float("inf")
        verdict = "TRADABLE" if ratio <= 1 / 3 else "COST-BLOCKED"
        rows.append(f"| **{key}** | {clocks} | {h.style} | {a:.1f} | {stop:.0f} | "
                    f"{rt:.0f} | {ratio:.3f} | {verdict} |")
    return "\n".join(rows)


def verdict_table(rows_in, only_promoted: bool = False) -> str:
    rows = ["| Horizon | Family | Symbol | DEV exp | DEV n | VAL exp | VAL n |"
            " OOS exp | OOS n | Shock exp | WFR | Verdict |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    sel = rows_in if not only_promoted else [
        r for r in rows_in if r["verdict"] == PROMOTABLE]
    for r in sorted(sel, key=lambda x: (x["horizon"], x["strategy"], x["symbol"])):
        rows.append(
            f"| {r['horizon']} | {r['strategy']} | {r['symbol']} | "
            f"{_fmt(float(r.get('dev_exp', 0)))} | {r.get('dev_n', 0)} | "
            f"{_fmt(float(r.get('val_exp', 0)))} | {r.get('val_n', 0)} | "
            f"{_fmt(float(r.get('oos_exp', 0)))} | {r.get('oos_n', 0)} | "
            f"{_fmt(float(r.get('shock_exp', 0)))} | "
            f"{r.get('wfr', '-')} | {r['verdict']} |")
    return "\n".join(rows)


def rejection_summary(rows_in) -> str:
    counts: Dict[str, int] = {}
    for r in rows_in:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    rows = ["| Verdict | Count |", "|---|---|"]
    for k in sorted(counts, key=lambda x: -counts[x]):
        rows.append(f"| {k} | {counts[k]} |")
    return "\n".join(rows)


def cost_autopsy(rows_in, cost: CostModel) -> str:
    """Explain, per horizon, WHY books died — cost arithmetic or alpha."""
    lines = []
    by_hz: Dict[str, list] = {}
    for r in rows_in:
        by_hz.setdefault(r["horizon"], []).append(r)
    for hz in HORIZON_ORDER:
        rs = by_hz.get(hz, [])
        if not rs:
            continue
        h = HORIZONS[hz]
        stops = [float(r.get("stop_bps_median", 0.0)) for r in rs
                 if float(r.get("stop_bps_median", 0.0)) > 0]
        med_stop = float(np.median(stops)) if stops else 0.0
        rt = cost.roundtrip_bps(h.maker_entry, h.maker_entry)
        n_promo = sum(1 for r in rs if r["verdict"] == PROMOTABLE)
        n_alpha = sum(1 for r in rs if "G2" in r["verdict"])
        n_cost = sum(1 for r in rs if "G5" in r["verdict"])
        n_stats = sum(1 for r in rs if "G3" in r["verdict"])
        n_wfr = sum(1 for r in rs if "G4" in r["verdict"])
        n_g1 = sum(1 for r in rs if "G1" in r["verdict"])
        head = (f"- **{hz}** ({h.ltf} clock, {len(rs)} books): median 1R = "
                f"{med_stop:.0f}bps vs {rt:.0f}bps roundtrip "
                f"(cost/stop = {rt / med_stop:.3f}). " if med_stop > 0
                else f"- **{hz}** ({len(rs)} books): ")
        lines.append(head + f"Promoted {n_promo}; died of data {n_g1}, "
                            f"alpha {n_alpha}, stats {n_stats}, "
                            f"walk-forward {n_wfr}, cost-shock {n_cost}.")
    return "\n".join(lines)


def portfolio_section(portfolio: Optional[dict]) -> list:
    if not portfolio:
        return []
    md = ["## 6. Portfolio simulation (all books, one account, paper)", "",
          "| Metric | Value |", "|---|---|"]
    for k, v in portfolio.items():
        md.append(f"| {k} | {v} |")
    md.append("")
    return md


def build_report(sweep: R.SweepResult, outdir: str,
                 cost: Optional[CostModel] = None,
                 portfolio: Optional[dict] = None,
                 title: str = "QCP Platform — All-Horizon Edge Report") -> str:
    """Write JSON + markdown artefacts and return the markdown text."""
    cost = cost or DEFAULT
    os.makedirs(outdir, exist_ok=True)
    median_atr = R.measure_median_atr_bps()
    promoted = [(k, v) for k, v in sweep.books.items() if v["verdict"].promoted]
    promoted_rows = [dict(v["verdict"].as_row()) for _, v in promoted]

    md = [f"# {title}", "",
          f"_Generated {np.datetime64('now', 's')} · {len(sweep.rows)} books "
          f"measured · {len(promoted)} promoted · sweep {sweep.elapsed_s}s_", "",
          "> Every figure below is computed from the local price/funding cache "
          "with full transaction costs, next-bar-open fills and adverse-first "
          "stop resolution. Out-of-sample data is never used for selection.",
          "", "## 1. Horizon economics (the gate that decides everything)", "",
          horizon_table(median_atr, cost), "",
          "`Median ATR` is measured live from the cache; the cost column is the "
          "all-in roundtrip cost from `costs.CostModel`. Where **Cost/Stop** "
          "exceeds 1/3, the horizon cannot be traded with those fills no matter "
          "how good the signal looks.", "",
          "## 2. Verdicts across all books", "", rejection_summary(sweep.rows), "",
          "## 3. Promoted books", ""]
    if promoted_rows:
        md += [verdict_table(promoted_rows), ""]
    else:
        md += ["_No book passed all gates in this run. That is a finding, not a "
               "failure: nothing here is yet strong enough to risk capital on, "
               "and the platform says so._", ""]
    md += ["## 4. Where the edge died", "", cost_autopsy(sweep.rows, cost), "",
           "## 5. Full verdict matrix", "", verdict_table(sweep.rows), ""]
    md += portfolio_section(portfolio)
    if sweep.data_notes:
        md += ["## 7. Data notes / exclusions", ""]
        for n in sweep.data_notes[:40]:
            md.append(f"- {n}")
        md.append("")

    text = "\n".join(md)
    with open(os.path.join(outdir, "REPORT.md"), "w") as f:
        f.write(text)
    with open(os.path.join(outdir, "verdicts.json"), "w") as f:
        json.dump(dict(
            generated_at=str(np.datetime64("now", "s")),
            elapsed_s=sweep.elapsed_s,
            median_atr_bps=median_atr,
            n_books=len(sweep.books),
            promoted=[k for k, _ in promoted],
            rows=sweep.rows,
            data_notes=sweep.data_notes,
            portfolio=portfolio or {}), f, indent=2, default=str)
    return text

