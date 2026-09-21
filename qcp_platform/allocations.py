"""QCP Platform — allocation families: rotation, accumulation, pairs, carry.

These cover the horizons that single-asset breakout logic does not serve well:

  * xs_momentum   — cross-sectional rotation across all 10 assets (POSITION/INVEST)
  * invest_dca    — valuation- and volatility-scaled accumulation (INVEST)
  * pairs_statarb — market-neutral relative value (SWING/POSITION)
  * funding_carry — market-neutral funding harvest, the highest-Sharpe book
                    available with this data (CARRY)

Rotation and accumulation reduce to boolean signal arrays and are executed by
`engine.resolve_trades` like every other family, so their fills/costs/stops are
subject to identical realism. Funding carry is its own settlement model because
its P&L is funding, not price — that model is documented inline.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from . import indicators as ind
from .costs import DEFAULT, CostModel
from .engine import BookResult, Trade, resolve_trades


def _xrank(mat: np.ndarray) -> np.ndarray:
    """Cross-sectional fractional rank per row, NaNs preserved."""
    out = np.full(mat.shape, np.nan)
    for i in range(mat.shape[0]):
        row = mat[i]
        ok = np.isfinite(row)
        if ok.sum() < 2:
            continue
        order = row[ok].argsort().argsort().astype(float)
        out[i, ok] = order / (ok.sum() - 1.0)
    return out


def momentum_score(C: np.ndarray, windows=(30, 90, 180)) -> np.ndarray:
    """Blended risk-adjusted momentum score per asset per bar (causal)."""
    parts = []
    for w in windows:
        r = np.full(C.shape, np.nan)
        with np.errstate(invalid="ignore"):
            r[w:] = C[w:] / C[:-w] - 1.0
        parts.append(r)
    raw = np.zeros_like(parts[0])
    for p in parts:
        raw = np.where(np.isfinite(p), np.nan_to_num(raw) + np.nan_to_num(p), raw)
    n_ok = np.sum([np.isfinite(p) for p in parts], axis=0)
    raw = np.divide(raw, np.maximum(n_ok, 1))
    vol = np.full(C.shape, np.nan)
    for j in range(C.shape[1]):
        v = ind.realized_vol(C[:, j], 30, ann=365)
        vol[:, j] = v
    # floor vol so near-constant series still rank (score ~ raw/0.02)
    vol = np.where(np.isfinite(vol), np.maximum(vol, 0.02), 0.02)
    return raw / vol


def xs_momentum_signals(panel: Dict[str, np.ndarray], top_k: int = 3,
                        rebalance_bars: int = 7, long_short: bool = True,
                        min_score: float = 0.0,
                        breadth_gate: float = 0.0) -> Dict[str, tuple]:
    """Rotation membership and entry events per asset.

    Returns {symbol: (hold_long, hold_short, exit_long, exit_short)}.

    Index 0/1 are membership arrays (True while the asset is in the held set) —
    the resolver enters on the first True and ignores repeats while a position
    is open, so membership arrays double as entry signals. Index 2/3 fire when
    the asset drops out of the set, which is what makes this a rotation rather
    than a stack of breakouts.
    """
    C = panel["c"]
    k, s = C.shape
    syms = panel["symbols"]
    score = momentum_score(C)
    hold_l = np.zeros((k, s), dtype=bool)
    hold_s = np.zeros((k, s), dtype=bool)
    snap = None
    for i in range(k):
        if i % rebalance_bars == 0:
            snap = score[i].copy()
        if snap is None:
            continue
        ok = np.isfinite(snap)
        if ok.sum() < top_k + 1:
            continue
        order = np.argsort(-np.where(ok, snap, -np.inf))
        for j in order[:top_k]:
            if snap[j] > min_score:
                hold_l[i, j] = True
        if long_short:
            for j in order[-top_k:]:
                if snap[j] < -min_score:
                    hold_s[i, j] = True
    if breadth_gate > 0:
        from .regimes import breadth as _breadth
        b = _breadth(C, 50)
        hold_l &= (b >= breadth_gate)[:, None]
        if long_short:
            hold_s &= (b < breadth_gate)[:, None]

    def _events(h):
        h = np.asarray(h, dtype=bool)
        # membership doubles as the entry signal; exit when it lapses
        return h, ~h

    out = {}
    for j, sym in enumerate(syms):
        el, xl = _events(hold_l[:, j])
        es, xs_ = _events(hold_s[:, j])
        out[sym] = (el, es, xl, xs_)
    return out


# ---------------------------------------------------------------------------
# DCA / accumulation (INVEST)
# ---------------------------------------------------------------------------
def invest_dca_signals(d: Dict, atr_arr: np.ndarray, dd_entry: float = 0.25,
                       vol_cap: float = 1.30, exit_span: int = 200):
    """Accumulate on discount while the long-term trend is intact.

    Long-only, no leverage, disaster stop only. Exits on a trend break
    (close < EMA200) via a SIGNAL exit — this is the investing book, so it is
    designed to be boring and to survive 50%+ drawdowns without liquidation.
    """
    c = d["c"]
    dd = ind.drawdown_from_ath(c)
    e = ind.ema(c, exit_span)
    rv = ind.realized_vol(c, 30, ann=365)
    long_sig = (dd >= dd_entry) & np.nan_to_num(rv <= vol_cap, nan=False)
    long_sig[: exit_span + 5] = False
    exit_l = np.nan_to_num(c < e, nan=False)
    return long_sig, np.zeros(len(c), dtype=bool), exit_l


# ---------------------------------------------------------------------------
# Pairs / relative value (SWING, POSITION — market neutral)
# ---------------------------------------------------------------------------
def pairs_signals(panel: Dict[str, np.ndarray], i: int, j: int,
                  lookback: int = 90, z_entry: float = 2.0,
                  z_exit: float = 0.5, corr_min: float = 0.70):
    """Leg-level signals for the log-price spread between assets i and j.

    Returns dict(leg_a=(long, short, exit), leg_b=(long, short, exit)).
    Correlation is re-checked causally; a pair whose correlation decays below
    `corr_min` is force-flattened, because that is precisely the regime in
    which relative-value trades stop working.
    """
    a = panel["c"][:, i].astype(float)
    b = panel["c"][:, j].astype(float)
    k = len(a)
    ra = np.diff(a, prepend=a[0])
    rb = np.diff(b, prepend=b[0])
    with np.errstate(invalid="ignore", divide="ignore"):
        lr = np.log(a) - np.log(b)
        m = ind.sma(lr, lookback)
        sd = ind.rolling_std(lr, lookback)
        z = (lr - m) / np.where(sd > 0, sd, np.nan)
    corr = ind.correlation(ra, rb, lookback)
    z = np.where(np.nan_to_num(corr, nan=0.0) >= corr_min, z, np.nan)
    la = np.zeros(k, dtype=bool); sa = np.zeros(k, dtype=bool); xa = np.zeros(k, dtype=bool)
    lb = np.zeros(k, dtype=bool); sb = np.zeros(k, dtype=bool); xb = np.zeros(k, dtype=bool)
    state = 0
    for t in range(k):
        zt = z[t]
        if not np.isfinite(zt):
            if state != 0:
                xa[t] = xb[t] = True
                state = 0
            continue
        if state == 0:
            if zt >= z_entry:
                state = 1          # spread rich -> short A / long B
                sa[t] = True; lb[t] = True
            elif zt <= -z_entry:
                state = -1         # spread cheap -> long A / short B
                la[t] = True; sb[t] = True
        else:
            if abs(zt) <= z_exit:
                xa[t] = xb[t] = True
                state = 0
            elif state == 1 and zt <= -z_entry:
                xa[t] = xb[t] = True
                state = -1
                la[t] = True; sb[t] = True
            elif state == -1 and zt >= z_entry:
                xa[t] = xb[t] = True
                state = 1
                sa[t] = True; lb[t] = True
    return dict(leg_a=(la, sa, xa), leg_b=(lb, sb, xb))


# ---------------------------------------------------------------------------
# Funding carry (CARRY — market neutral, highest-capacity book)
# ---------------------------------------------------------------------------
def daily_funding(ts: np.ndarray, rate: np.ndarray) -> Dict[str, np.ndarray]:
    """Sum the 3 daily 8h settlements into a per-day funding total."""
    day = (np.asarray(ts, dtype=np.int64) // 86400) * 86400
    uniq, inv = np.unique(day, return_inverse=True)
    tot = np.zeros(len(uniq))
    np.add.at(tot, inv, np.asarray(rate, dtype=float))
    return dict(ts=uniq, close_ts=uniq + 86400, sum=tot, n=len(uniq))


def funding_carry_book(symbol: str, daily: Dict, fund_ts: np.ndarray,
                       fund_rate: np.ndarray, cost: Optional[CostModel] = None,
                       apr_entry: float = 0.15, apr_exit: float = 0.05,
                       lookback_days: int = 7, max_hold_days: int = 90,
                       min_hold_days: int = 7, risk_unit: float = 0.005,
                       horizon: str = "CARRY") -> BookResult:
    """Harvest positive perpetual funding with a delta-neutral position.

    Position: long spot + short perp of the SAME asset. Price P&L cancels;
    the return is the funding stream, which is paid to the short-perp side when
    funding is positive (the usual state in crypto bull/chop markets).

    Modelled risk (the units of 1R): basis/funding risk, NOT price. 1R is
    defined as a 0.5% adverse move of (funding received - basis), which is a
    large, rare event for a hedged book. Entry/exit costs are charged as four
    market fills plus explicit basis friction (see CostModel.carry_roundtrip_bps).

    Honest limitations, stated up front:
      * We do not have spot klines; the spot leg is modelled as the perp price,
        so the spot-vs-perp basis is charged as an explicit cost instead of
        being exploited.
      * Margin/liquidation of the perp leg is not modelled because the hedge
        makes the combined position delta-neutral; a de-peg or exchange failure
        would be far worse than anything here. This is a PAPER book.
    """
    cost = cost or DEFAULT
    af = daily_funding(fund_ts, fund_rate)
    grid_ts = daily["ts"]
    k = len(grid_ts)
    # causal alignment: last COMPLETED funding day
    idx = np.searchsorted(af["close_ts"], grid_ts, side="right") - 1
    fday = np.where(idx >= 0, af["sum"][np.clip(idx, 0, af["n"] - 1)], np.nan)

    res = BookResult(strategy="funding_carry", horizon=horizon)
    rt_cost = cost.carry_roundtrip_bps() / 1e4
    in_pos = False
    start = 0
    acc = 0.0
    for t in range(k):
        if not in_pos:
            if t < lookback_days:
                continue
            window = fday[t - lookback_days + 1: t + 1]
            if not np.all(np.isfinite(window)):
                continue
            apr = float(np.mean(window) * 365.0)
            if apr >= apr_entry:
                in_pos = True
                start = t
                acc = 0.0
            continue
        # in position: accrue today's funding
        if np.isfinite(fday[t]):
            acc += float(fday[t])
        held = t - start
        apr_now = float(np.mean(fday[max(0, t - lookback_days + 1): t + 1]) * 365.0)
        reason = None
        if held >= max_hold_days:
            reason = "MAX_HOLD"
        elif held >= min_hold_days and apr_now < apr_exit:
            reason = "FUND_DECAY"
        elif apr_now < 0.0 and held >= min_hold_days:
            reason = "FUND_NEGATIVE"
        if reason:
            net = acc - rt_cost
            res.trades.append(Trade(
                strategy="funding_carry", symbol=symbol, horizon=horizon,
                direction=-1, entry_ts=int(grid_ts[start]),
                exit_ts=int(grid_ts[t] + 86400),
                entry_px=1.0, exit_px=1.0, stop_px=0.0, target_px=0.0,
                r_multiple=net / risk_unit, exit_reason=reason,
                bars_held=int(held),
                meta=dict(funding_collected=round(acc, 6),
                          cost=round(rt_cost, 6),
                          net=round(net, 6),
                          entry_apr=round(float(np.mean(
                              fday[max(0, start - lookback_days + 1):start + 1]) * 365.0), 4),
                          exit_apr=round(apr_now, 4),
                          hedged=True)))
            in_pos = False
            acc = 0.0
    return res


