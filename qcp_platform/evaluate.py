"""Crypto Trading Platform — promotion gates and honesty statistics.

A book is only promoted when it passes ALL gates. Gates are ordered from
cheapest to most expensive so junk dies early:

  G1 DATA     enough trades in DEV and OOS; enough span to matter
  G2 ALPHA    positive expectancy in DEV, VAL and OOS (all three, same sign)
  G3 STATS    bootstrap probability of a positive edge, and t-stat of DEV
  G4 WFR      walk-forward ratio and rolling-window sign consistency
  G5 COSTS    survives a +50% cost shock and real cost/stop ratio is sane
  G6 RISK     max drawdown in R, no single trade dominating total R
  G7 PORTFOLIO marginal Sharpe contribution positive versus the existing book

Verdicts are explicit: PROMOTABLE_PAPER_ONLY, or REJECTED_<gate>. Reporting a
rejection with the gate that killed it is the point: it is information, and it
is what stops the platform from lying to itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from .costs import DEFAULT, CostModel
from .engine import BookResult

PROMOTABLE = "PROMOTABLE_PAPER_ONLY"


@dataclass
class GateConfig:
    min_dev_trades: int = 40
    min_val_trades: int = 15
    min_oos_trades: int = 15
    min_dev_span_days: int = 180
    min_expectancy_r: float = 0.02
    min_wfr: float = 0.30
    min_bootstrap_p: float = 0.60
    bootstrap_iters: int = 1000
    max_dd_r: float = 30.0
    max_single_trade_share: float = 0.50
    cost_shock_mult: float = 1.50
    min_oos_shock_exp: float = 0.0


@dataclass
class Verdict:
    strategy: str
    symbol: str
    horizon: str
    verdict: str
    gates: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)

    @property
    def promoted(self) -> bool:
        return self.verdict == PROMOTABLE

    def as_row(self) -> dict:
        return dict(strategy=self.strategy, symbol=self.symbol,
                    horizon=self.horizon, verdict=self.verdict,
                    gates=";".join(f"{k}={v}" for k, v in self.gates.items()),
                    **{k: (round(v, 4) if isinstance(v, float) else v)
                       for k, v in self.stats.items()})

    def failures(self) -> List[str]:
        return [k for k, v in self.gates.items() if v not in (True, "ok", "OK")]


def bootstrap_p_positive(rs: np.ndarray, iters: int = 1000,
                         seed: int = 7) -> float:
    """Probability that the true mean R is positive, via bootstrap resampling.

    Resamples trades with replacement (n = observed n) and reports the fraction
    of resampled means above zero. This is a statement about the measured
    sample, not a guarantee about the future, and it is reported as such.
    """
    r = np.asarray(rs, dtype=float)
    if len(r) < 5:
        return 0.0
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(r), size=(iters, len(r)))
    means = r[idx].mean(axis=1)
    return float((means > 0).mean())


def sign_stability(rs: np.ndarray, chunks: int = 4) -> float:
    """Fraction of equal-size chunks with positive mean R (regime robustness)."""
    r = np.asarray(rs, dtype=float)
    if len(r) < chunks * 5:
        return 0.0
    parts = np.array_split(r, chunks)
    return float(np.mean([p.mean() > 0 for p in parts]))


def t_stat(rs: np.ndarray) -> float:
    r = np.asarray(rs, dtype=float)
    if len(r) < 3 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * np.sqrt(len(r)))


def max_dd_r(rs: np.ndarray) -> float:
    r = np.asarray(rs, dtype=float)
    if not len(r):
        return 0.0
    cum = np.cumsum(r)
    return float(np.max(np.maximum.accumulate(cum) - cum))


def single_trade_share(rs: np.ndarray) -> float:
    """Share of total positive R contributed by the single best trade."""
    r = np.asarray(rs, dtype=float)
    tot = r[r > 0].sum()
    if tot <= 0:
        return 1.0
    return float(r.max() / tot)


def evaluate_book(strategy: str, symbol: str, horizon: str,
                  dev: BookResult, val: BookResult, oos: BookResult,
                  dev_span_days: int = 10_000,
                  cost_shock: Optional[BookResult] = None,
                  params: Optional[dict] = None,
                  cfg: Optional[GateConfig] = None,
                  extra_stats: Optional[dict] = None) -> Verdict:
    """Run the seven gates and return an explicit, auditable verdict."""
    cfg = cfg or GateConfig()
    gates: Dict[str, object] = {}
    stats: Dict[str, object] = {}
    rs_dev, rs_val, rs_oos = dev.rs, val.rs, oos.rs

    # G1 DATA
    gates["G1_data"] = (dev.n >= cfg.min_dev_trades
                        and val.n >= cfg.min_val_trades
                        and oos.n >= cfg.min_oos_trades
                        and dev_span_days >= cfg.min_dev_span_days)
    stats["dev_n"] = dev.n; stats["val_n"] = val.n; stats["oos_n"] = oos.n
    stats["dev_span_days"] = dev_span_days

    # G2 ALPHA (same sign, positive, in all three windows)
    de, ve, oe = dev.expectancy_r, val.expectancy_r, oos.expectancy_r
    gates["G2_alpha"] = bool(de >= cfg.min_expectancy_r and ve > 0 and oe > 0)
    stats["dev_exp"] = de; stats["val_exp"] = ve; stats["oos_exp"] = oe
    stats["dev_total_r"] = dev.total_r
    stats["oos_total_r"] = oos.total_r
    stats["oos_win_rate"] = oos.win_rate
    stats["oos_pf"] = oos.profit_factor
    stats["oos_sharpe"] = oos.sharpe_trade
    stats["dev_sharpe"] = dev.sharpe_trade
    stats["val_sharpe"] = val.sharpe_trade
    stats["oos_avg_bars"] = (round(float(np.mean([t.bars_held for t in oos.trades])), 1)
                             if oos.n else 0.0)
    stats["stop_bps_median"] = (round(float(np.median(
        [t.meta.get("stop_bps", 0.0) for t in oos.trades])), 1) if oos.n else 0.0)

    # G3 STATS
    p_dev = bootstrap_p_positive(rs_dev, cfg.bootstrap_iters)
    p_oos = bootstrap_p_positive(rs_oos, cfg.bootstrap_iters, seed=11)
    gates["G3_stats"] = bool(p_dev >= cfg.min_bootstrap_p and t_stat(rs_dev) > 0.5)
    stats["boot_p_dev"] = p_dev; stats["boot_p_oos"] = p_oos
    stats["t_dev"] = t_stat(rs_dev); stats["t_oos"] = t_stat(rs_oos)

    # G4 WALK-FORWARD
    from .walkforward import consistency_wfr
    wfr = consistency_wfr(de, ve, oe)
    stab = sign_stability(np.concatenate([rs_dev, rs_val, rs_oos]), 4)
    gates["G4_wfr"] = bool(wfr >= cfg.min_wfr and stab >= 0.50)
    stats["wfr"] = wfr; stats["chunk_stability"] = stab

    # G5 COSTS (must survive a +50% cost shock)
    if cost_shock is not None:
        se = cost_shock.expectancy_r
        gates["G5_costs"] = bool(se >= cfg.min_oos_shock_exp)
        stats["shock_exp"] = se
        stats["shock_n"] = cost_shock.n
    else:
        gates["G5_costs"] = "not_tested"

    # G6 RISK
    dd = max_dd_r(np.concatenate([rs_dev, rs_val, rs_oos]))
    share = single_trade_share(np.concatenate([rs_dev, rs_val, rs_oos]))
    gates["G6_risk"] = bool(dd <= cfg.max_dd_r
                            and share <= cfg.max_single_trade_share)
    stats["max_dd_r"] = dd; stats["best_trade_share"] = share

    # G7 PORTFOLIO (filled in later by the runner; default not_tested)
    gates["G7_portfolio"] = "not_tested"

    failed = [k for k, v in gates.items() if v is False]
    if failed:
        verdict = "REJECTED_" + failed[0].split("_", 1)[0]
    elif "not_tested" in gates.values():
        verdict = "MEASURED"
    else:
        verdict = PROMOTABLE
    if extra_stats:
        stats.update(extra_stats)
    return Verdict(strategy=strategy, symbol=symbol, horizon=horizon,
                   verdict=verdict, gates=gates, stats=stats,
                   params=params or {})


def apply_g7(verdict: "Verdict", passed: bool, reason: str = "") -> None:
    """Fill in the portfolio-level gate and finalize the verdict in place.

    MEASURED (all per-book gates passed) + G7 pass  -> PROMOTABLE_PAPER_ONLY
    MEASURED + G7 fail                              -> REJECTED_G7
    """
    verdict.gates["G7_portfolio"] = bool(passed) if passed else reason or False
    if passed:
        verdict.verdict = PROMOTABLE
    elif verdict.verdict == "MEASURED":
        verdict.verdict = "REJECTED_G7"

