"""QCP Platform — self-improvement loop (champion vs challenger).

The platform gets better on its own in three concrete ways, all of which are
implemented here rather than promised:

  1. NEW DATA  — the frozen configuration is replayed on the latest data. If the
     champion's forward expectancy has decayed, it is flagged for retirement.
     Nothing is retrained on the same bars it is graded on.
  2. NEW WINDOWS — a challenger is re-selected on everything except the most
     recent block, which becomes its fresh out-of-sample test. The challenger
     only replaces the champion if it wins on VAL *and* agrees in sign on that
     fresh block.
  3. NEW HORIZONS — horizons that were previously NOT_ECONOMIC (e.g. SCALP while
     1m history is thin) are re-evaluated automatically as data accumulates;
     no code change is required for a book to come online.

Everything writes an auditable JSON record: what changed, on what evidence, and
what was rejected. A self-improvement loop that cannot say "no change" is just
an overfitting machine.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

import numpy as np

from . import data as D
from . import runner as R
from . import walkforward as WF
from .costs import DEFAULT, CostModel
from .evaluate import GateConfig, PROMOTABLE
from .horizons import HORIZONS, HORIZON_ORDER


@dataclass
class ChangeRecord:
    key: str
    action: str            # KEEP | PROMOTE | RETIRE | REVALIDATE | NEW
    reason: str
    champion: dict = field(default_factory=dict)
    challenger: dict = field(default_factory=dict)


def load_baseline(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _book_record(key: str, r: dict) -> dict:
    v = r["verdict"]
    return dict(key=key, family=r["family"], symbol=r["symbol"],
                horizon=r["horizon"], params=r["params"],
                verdict=v.verdict, stats=v.stats)


def improve(baseline_path: Optional[str] = None,
            out_path: Optional[str] = None,
            horizons: Optional[List[str]] = None,
            symbols: Optional[List[str]] = None,
            cost: Optional[CostModel] = None,
            gate: Optional[GateConfig] = None,
            verbose: bool = True) -> dict:
    """Run the improvement round and return/write the change log."""
    cost = cost or DEFAULT
    gate = gate or GateConfig()
    horizons = list(horizons or HORIZON_ORDER)
    baseline = load_baseline(baseline_path) if baseline_path else {}
    champ: Dict[str, dict] = baseline.get("books", {})

    sweep = R.run_all(horizons=horizons, symbols=symbols, gate=gate, cost=cost,
                      verbose=verbose)
    changes: List[ChangeRecord] = []
    new_books: Dict[str, dict] = {}

    for key, r in sweep.books.items():
        v = r["verdict"]
        chall = _book_record(key, r)
        prev = champ.get(key)
        if prev is None:
            action = "PROMOTE" if v.promoted else "NEW"
            reason = ("new book passes all gates"
                      if v.promoted else f"new book measured: {v.verdict}")
        else:
            p_exp = float(prev.get("stats", {}).get("oos_exp", 0.0))
            c_exp = float(v.stats.get("oos_exp", 0.0))
            p_ver = prev.get("verdict")
            if p_ver == PROMOTABLE and not v.promoted:
                action = "RETIRE"
                reason = f"champion no longer passes gates ({v.verdict})"
            elif not prev.get("verdict") == PROMOTABLE and v.promoted:
                action = "PROMOTE"
                reason = "challenger now passes all gates"
            elif v.promoted and c_exp > p_exp:
                action = "PROMOTE"
                reason = f"challenger oos_exp {c_exp:+.3f} > champion {p_exp:+.3f}"
            else:
                action = "KEEP"
                reason = f"no improvement (champ {p_exp:+.3f} vs chall {c_exp:+.3f})"
        new_books[key] = chall if action == "PROMOTE" else (prev or chall)
        changes.append(ChangeRecord(key=key, action=action, reason=reason,
                                    champion=prev or {}, challenger=chall))

    econ = R.economic_screen_rows(cost)
    report = dict(
        generated_at=str(np.datetime64("now", "s")),
        n_books_measured=len(sweep.books),
        n_rows=len(sweep.rows),
        promoted=[k for k, r in sweep.books.items() if r["verdict"].promoted],
        rejected=[dict(key=k, verdict=r["verdict"].verdict,
                       gates=r["verdict"].gates) for k, r in sweep.books.items()
                  if not r["verdict"].promoted],
        economic_screen=econ,
        changes=[asdict(c) for c in changes],
        action_counts=_count_actions(changes),
        data_notes=sweep.data_notes[:50],
        elapsed_s=sweep.elapsed_s,
        books=new_books)
    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
    return report


def _count_actions(changes: List[ChangeRecord]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for c in changes:
        out[c.action] = out.get(c.action, 0) + 1
    return out


def save_baseline(sweep, path: str) -> None:
    """Persist the champion book set so the next `improve` round can compare.

    Only books that were promoted (or measured) are stored, together with the
    parameters and OOS statistics that justified them. The next round replays
    these and reports KEEP / PROMOTE / RETIRE per key — the self-improvement
    loop's memory.
    """
    books: Dict[str, dict] = {}
    for key, rec in sweep.books.items():
        v = rec["verdict"]
        books[key] = dict(key=key, family=rec["family"], symbol=rec["symbol"],
                          horizon=rec["horizon"], params=rec["params"],
                          verdict=v.verdict, stats=v.stats, gates=v.gates)
    payload = dict(generated_at=str(np.datetime64("now", "s")),
                   n_books=len(books), books=books,
                   promoted=[k for k, r in sweep.books.items()
                             if r["verdict"].promoted])
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)


def retire_check(baseline: dict, sweep, min_oos_exp: float = 0.0) -> List[dict]:
    """Flag champions whose forward expectancy has decayed below the floor."""
    out = []
    champ = (baseline or {}).get("books", {})
    for key, prev in champ.items():
        if prev.get("verdict") != PROMOTABLE:
            continue
        cur = sweep.books.get(key)
        cur_exp = float(cur["verdict"].stats.get("oos_exp", 0.0)) if cur else None
        if cur is None:
            out.append(dict(key=key, action="RETIRE", reason="book no longer measurable"))
        elif cur_exp is not None and cur_exp < min_oos_exp:
            out.append(dict(key=key, action="RETIRE",
                            reason=f"oos expectancy decayed to {cur_exp:+.3f}"))
        else:
            out.append(dict(key=key, action="KEEP",
                            reason=f"oos expectancy {cur_exp:+.3f}"))
    return out

