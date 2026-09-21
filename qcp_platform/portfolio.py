"""QCP Platform — portfolio construction: many books, ONE account.

The research layer measures edges in R. This layer turns them into an account
P&L under real constraints, and it is where blow-up risk is actually removed:

  * every book receives a capital weight (from its horizon's budget), and its
    per-trade risk is `weight x base_risk` — so ten books cannot each risk 3%
  * the Governor gates every single entry on live account state (drawdown
    tiers, daily/weekly loss limits, consecutive-loss cooldown)
  * total simultaneous open risk is capped, with per-symbol and per-horizon
    caps, so correlated crypto positions cannot stack into a single bet
  * compounding is honest: P&L is applied to live equity, so the reported path
    (including drawdowns) is what actually happened, not a sum of R

Capital weights are derived from measured out-of-sample statistics
(Sharpe x expectancy), never from preference.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from .engine import BookResult
from .governor import Governor, GovernorConfig


@dataclass
class PortfolioConfig:
    base_risk_pct: float = 0.005        # per-trade risk before book weighting
    target_portfolio_vol: float = 0.15  # annualized, governor aim
    max_concurrent: int = 12
    horizon_weight: Dict[str, float] = field(default_factory=lambda: {
        "SCALP": 0.05, "INTRADAY": 0.15, "SWING": 0.25,
        "POSITION": 0.25, "INVEST": 0.20, "CARRY": 0.10})


@dataclass
class PortfolioResult:
    equity_curve: List[tuple] = field(default_factory=list)   # (ts, equity)
    trades_taken: int = 0
    trades_skipped: int = 0
    skip_reasons: Dict[str, int] = field(default_factory=dict)
    per_book: Dict[str, dict] = field(default_factory=dict)
    governor: dict = field(default_factory=dict)

    @property
    def final_equity(self) -> float:
        return self.equity_curve[-1][1] if self.equity_curve else 1.0

    @property
    def total_return(self) -> float:
        return self.final_equity - 1.0

    @property
    def max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        eq = np.array([e for _, e in self.equity_curve])
        peak = np.maximum.accumulate(eq)
        return float(np.max((peak - eq) / peak))

    def sharpe(self, periods_per_year: float = 365.0) -> float:
        if len(self.equity_curve) < 3:
            return 0.0
        eq = np.array([e for _, e in self.equity_curve])
        r = np.diff(eq) / eq[:-1]
        if r.std(ddof=0) == 0:
            return 0.0
        return float(r.mean() / r.std(ddof=0) * np.sqrt(periods_per_year))

    def summary(self) -> dict:
        return dict(final_equity=round(self.final_equity, 4),
                    total_return=round(self.total_return, 4),
                    max_drawdown=round(self.max_drawdown, 4),
                    sharpe=round(self.sharpe(), 3),
                    trades_taken=self.trades_taken,
                    trades_skipped=self.trades_skipped,
                    skip_reasons=self.skip_reasons,
                    governor=self.governor)


def weights_from_oos(books: Dict[str, dict],
                     cfg: Optional[PortfolioConfig] = None) -> Dict[str, float]:
    """Book weights: horizon budget x out-of-sample quality, normalized.

    quality = max(0, oos_sharpe) x max(0, 0.5 + oos_expectancy)
    A book with no measurable edge receives zero weight, and its horizon budget
    is redistributed to the books that do have one.
    """
    cfg = cfg or PortfolioConfig()
    raw: Dict[str, float] = {}
    for key, rec in books.items():
        v = rec["verdict"]
        budget = cfg.horizon_weight.get(v.horizon, 0.10)
        sh = float(v.stats.get("oos_sharpe", 0.0) or 0.0)
        ex = float(v.stats.get("oos_exp", 0.0) or 0.0)
        raw[key] = budget * max(0.0, sh) * max(0.0, 0.5 + ex)
    tot = sum(raw.values())
    if tot <= 0:
        return {k: 0.0 for k in raw}
    return {k: v / tot for k, v in raw.items()}


def simulate_portfolio(books: Dict[str, dict],
                       cfg: Optional[PortfolioConfig] = None,
                       gov_cfg: Optional[GovernorConfig] = None,
                       weights: Optional[Dict[str, float]] = None,
                       start_ts: int = 0,
                       use_window: str = "oos") -> PortfolioResult:
    """Event-driven account simulation across all selected books.

    Trades are processed in entry order; closed positions release risk before
    new entries are considered. Every entry passes the Governor, and realized
    P&L is applied to live equity, so the reported path is a real account path.

    `use_window` selects which slice of each book to trade: "oos" (default,
    the honest forward test) or "full" (the whole history).
    """
    cfg = cfg or PortfolioConfig()
    gov = Governor(gov_cfg or GovernorConfig(), initial_equity=1.0)
    res = PortfolioResult()
    res.equity_curve.append((start_ts, 1.0))
    if not books:
        res.governor = gov.snapshot()
        return res

    weights = weights if weights is not None else weights_from_oos(books, cfg)
    flat: List[tuple] = []
    for key, rec in books.items():
        w = weights.get(key, 0.0)
        if w <= 0:
            continue
        v = rec["verdict"]
        risk_frac = cfg.base_risk_pct * w
        src = rec.get(use_window)
        if src is None:
            continue
        for t in src.trades:
            flat.append((t.entry_ts, t.exit_ts, key, t.r_multiple,
                         risk_frac, v.horizon, t.symbol))
    if not flat:
        res.governor = gov.snapshot()
        return res
    flat.sort(key=lambda x: x[0])

    open_pos: List[tuple] = []      # (exit_ts, key, risk, horizon, symbol, r)
    eq = 1.0
    per_book: Dict[str, dict] = {}
    g = gov.cfg

    def take(key, r_mult, rf):
        nonlocal eq
        pnl = rf * r_mult
        eq *= (1.0 + pnl)
        b = per_book.setdefault(key, dict(n=0, wins=0, r_sum=0.0, pnl=0.0))
        b["n"] += 1
        b["wins"] += int(pnl > 0)
        b["r_sum"] += r_mult
        b["pnl"] += pnl
        return pnl

    for (e_ts, x_ts, key, r, rf, hz, sy) in flat:
        still = []
        for pos in open_pos:
            if pos[0] <= e_ts:
                pnl = take(pos[1], pos[5], pos[2])
                gov.on_pnl(pnl, int(pos[0] // 86400))
                res.equity_curve.append((pos[0], round(eq, 6)))
            else:
                still.append(pos)
        open_pos = still

        gov.new_day(int(e_ts // 86400))
        allowed, scale, reason = gov.allow_new_risk()
        if not allowed:
            res.trades_skipped += 1
            res.skip_reasons[reason] = res.skip_reasons.get(reason, 0) + 1
            continue
        if len(open_pos) >= cfg.max_concurrent:
            res.trades_skipped += 1
            res.skip_reasons["MAX_CONCURRENT"] = res.skip_reasons.get("MAX_CONCURRENT", 0) + 1
            continue
        if sum(p[2] for p in open_pos) + rf > g.max_total_risk:
            res.trades_skipped += 1
            res.skip_reasons["MAX_TOTAL_RISK"] = res.skip_reasons.get("MAX_TOTAL_RISK", 0) + 1
            continue
        if sum(p[2] for p in open_pos if p[4] == sy) + rf > g.max_risk_per_symbol:
            res.trades_skipped += 1
            res.skip_reasons["MAX_SYMBOL_RISK"] = res.skip_reasons.get("MAX_SYMBOL_RISK", 0) + 1
            continue
        if sum(p[2] for p in open_pos if p[3] == hz) + rf > g.max_risk_per_horizon:
            res.trades_skipped += 1
            res.skip_reasons["MAX_HORIZON_RISK"] = res.skip_reasons.get("MAX_HORIZON_RISK", 0) + 1
            continue
        open_pos.append((x_ts, key, rf * scale, hz, sy, r))
        res.trades_taken += 1

    for pos in open_pos:
        pnl = take(pos[1], pos[5], pos[2])
        gov.on_pnl(pnl, int(pos[0] // 86400))
        res.equity_curve.append((pos[0], round(eq, 6)))

    res.equity_curve.sort(key=lambda x: x[0])
    res.per_book = {k: dict(n=v["n"], win_rate=round(v["wins"] / v["n"], 3),
                            avg_r=round(v["r_sum"] / v["n"], 4),
                            pnl=round(v["pnl"], 4))
                    for k, v in per_book.items()}
    res.governor = gov.snapshot()
    return res


def select_books(books: Dict[str, dict],
                 cfg: Optional[PortfolioConfig] = None,
                 gov_cfg: Optional[GovernorConfig] = None,
                 use_window: str = "oos",
                 min_sharpe_gain: float = 0.0) -> tuple:
    """G7 gate: greedy forward selection by marginal portfolio contribution.

    Starting from an empty book set, repeatedly add the candidate whose
    inclusion most improves the paper-portfolio Sharpe (OOS window). A book
    whose addition does not improve Sharpe by at least `min_sharpe_gain` is
    dropped with reason — this is the final promotion filter above the
    per-book gates: an edge that adds nothing to the account as a whole is
    not an edge the account should carry.

    Returns (selected: Dict[key, dict], dropped: List[dict]).
    """
    cfg = cfg or PortfolioConfig()
    candidates = list(books.keys())
    selected: Dict[str, dict] = {}
    dropped: List[dict] = []
    base = simulate_portfolio(selected, cfg, gov_cfg, use_window=use_window)
    best_sharpe = base.sharpe()
    while candidates:
        trials = []
        for key in candidates:
            trial = dict(selected)
            trial[key] = books[key]
            r = simulate_portfolio(trial, cfg, gov_cfg, use_window=use_window)
            trials.append((r.sharpe(), key, r))
        trials.sort(key=lambda x: (-x[0], x[1]))
        sh, key, _ = trials[0]
        if sh <= best_sharpe + min_sharpe_gain and selected:
            for k in candidates:
                dropped.append(dict(key=k, reason="G7_no_marginal_sharpe"))
            break
        if sh <= best_sharpe + min_sharpe_gain:
            # nothing improves on empty; take the best single book if positive
            if sh > 0:
                selected[key] = books[key]
                candidates.remove(key)
                best_sharpe = sh
                continue
            for k in candidates:
                dropped.append(dict(key=k, reason="G7_no_positive_sharpe"))
            break
        selected[key] = books[key]
        candidates.remove(key)
        best_sharpe = sh
    return selected, dropped


def run_portfolio(books: Dict[str, dict],
                  cfg: Optional[PortfolioConfig] = None,
                  gov_cfg: Optional[GovernorConfig] = None,
                  use_window: str = "oos") -> dict:
    """Full portfolio pass: G7 selection, governor simulation, report dict."""
    cfg = cfg or PortfolioConfig()
    selected, dropped = select_books(books, cfg, gov_cfg, use_window)
    weights = weights_from_oos(selected, cfg)
    res = simulate_portfolio(selected, cfg, gov_cfg, weights=weights,
                             use_window=use_window)
    return dict(selection=dict(selected=sorted(selected.keys()),
                               dropped=dropped, weights={
                                   k: round(w, 4) for k, w in weights.items()}),
                result=res, summary=res.summary())


def correlation_matrix(books: Dict[str, dict], window: str = "oos") -> Dict[str, float]:
    """Mean pairwise correlation of per-book monthly R (overlap risk report)."""
    series: Dict[str, Dict[str, float]] = {}
    for key, rec in books.items():
        b = rec.get(window)
        if b is None or b.n < 10:
            continue
        by_month: Dict[str, float] = {}
        for t in b.trades:
            m = str(np.datetime64(int(t.exit_ts), "s"))[:7]
            by_month[m] = by_month.get(m, 0.0) + t.r_multiple
        series[key] = by_month
    keys = list(series)
    out: Dict[str, float] = {}
    for a in keys:
        corrs = []
        months = sorted(series[a])
        for b in keys:
            if b == a:
                continue
            common = [m for m in months if m in series[b]]
            if len(common) < 6:
                continue
            x = np.array([series[a][m] for m in common])
            y = np.array([series[b][m] for m in common])
            if x.std() == 0 or y.std() == 0:
                continue
            corrs.append(float(np.corrcoef(x, y)[0, 1]))
        out[a] = round(float(np.mean(corrs)), 3) if corrs else 0.0
    return out

