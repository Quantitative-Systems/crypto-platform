"""Crypto Trading Platform — the multiplatform runner.

For every (horizon, family, asset) it:
  1. loads the BASE timeframe once,
  2. builds HTF/MTF context (causal),
  3. selects parameters on DEV only,
  4. confirms on VAL, reports OOS, and re-runs the whole window rolled forward,
  5. applies a +50% cost shock and the seven gates,
  6. emits an auditable verdict row.

`run_all` is the single entry point used by the CLI, the portfolio layer and
the self-improvement loop, so every consumer sees the same measurement.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from . import allocations as alloc
from . import data as D
from . import indicators as ind
from . import strategies as S
from . import walkforward as WF
from .costs import DEFAULT, CostModel
from .engine import BookResult, resolve_trades
from .evaluate import GateConfig, PROMOTABLE, Verdict, evaluate_book
from .horizons import HORIZONS, HORIZON_ORDER, Horizon

# --------------------------------------------------------------------------
# Parameter grids (modest on purpose: hundreds of combos across the platform
# is already enough rope to hang yourself with; the walk-forward gates are the
# real defence and a huge grid just manufactures false winners)
# --------------------------------------------------------------------------
GRIDS: Dict[str, List[dict]] = {
    "trend_breakout": [
        dict(lookback=20, vol_pct_min=0.4, require_quality=False),
        dict(lookback=20, vol_pct_min=0.6, require_quality=True, q_min=0.5),
        dict(lookback=50, vol_pct_min=0.5, require_quality=False),
        dict(lookback=50, vol_pct_min=0.6, require_quality=True, q_min=0.55),
        dict(lookback=100, vol_pct_min=0.6, require_quality=True, q_min=0.55),
    ],
    "trend_rider": [
        dict(fast=20, slow=50, ts_min=0.4, adx_min=15.0),
        dict(fast=20, slow=50, ts_min=0.8, adx_min=20.0),
        dict(fast=50, slow=100, ts_min=0.6, adx_min=18.0),
    ],
    "mean_revert": [
        dict(band_n=20, z_entry=2.0, rsi_low=30.0, rsi_high=70.0),
        dict(band_n=20, z_entry=2.5, rsi_low=25.0, rsi_high=75.0),
        dict(band_n=50, z_entry=2.0, rsi_low=30.0, rsi_high=70.0),
    ],
    "grid_range": [
        dict(band_n=96, n_levels=6, max_adx=20.0),
        dict(band_n=192, n_levels=8, max_adx=22.0),
    ],
    "scalp_micro": [
        dict(lookback=12, vol_mult=1.5),
        dict(lookback=24, vol_mult=2.0),
    ],
}

RISK_VARIANTS = [
    dict(atr_mult=2.0, target_r=2.0, trail_atr_mult=0.0),
    dict(atr_mult=2.5, target_r=3.0, trail_atr_mult=0.0),
    dict(atr_mult=3.0, target_r=2.0, trail_atr_mult=0.0),
    dict(atr_mult=2.5, target_r=2.5, trail_atr_mult=2.0),
]

FAMILY_FN = {
    "trend_breakout": S.sig_trend_breakout,
    "trend_rider": S.sig_trend_rider,
    "mean_revert": S.sig_mean_revert,
    "grid_range": S.sig_grid_range,
    "scalp_micro": S.sig_scalp_micro,
}


@dataclass
class HorizonData:
    """Prepared, causally-aligned data stack for one (asset, horizon)."""
    symbol: str
    horizon: str
    base: Dict[str, np.ndarray]
    atr: np.ndarray
    htf: Dict[str, np.ndarray]
    mtf: Dict[str, np.ndarray]
    windows: WF.Windows

    @property
    def n(self) -> int:
        return self.base["n"]


def prepare(symbol: str, horizon: str, base_tf: Optional[str] = None,
            base: Optional[Dict[str, np.ndarray]] = None) -> Optional[HorizonData]:
    """Load and align everything a horizon needs. Returns None if data is short."""
    h = HORIZONS[horizon]
    b = base if base is not None else D.load_ohlcv(symbol, base_tf or h.ltf)
    if b is None or b["n"] < 600:
        return None
    htf = D.load_tf(symbol, h.htf)
    mtf = D.load_tf(symbol, h.mtf)
    if htf is None or mtf is None:
        return None
    a = ind.atr(b["h"], b["l"], b["c"], 14)
    w = WF.make_windows(b["n"])
    if w.val.stop - w.val.start < 50 or w.oos.stop - w.oos.start < 50:
        return None
    return HorizonData(symbol=symbol, horizon=horizon, base=b, atr=a,
                       htf=htf, mtf=mtf, windows=w)


def simulate_config(hd: HorizonData, family: str, params: dict,
                    risk: dict, cost: CostModel, maker: bool,
                    min_stop_bps: float, max_hold_bars: int,
                    allow_short: bool = True, shock: float = 1.0) -> BookResult:
    """Full-sample simulation for one config (windowing happens after)."""
    h = HORIZONS[hd.horizon]
    fn = FAMILY_FN[family]
    long_sig, short_sig = fn(hd.base, hd.atr, hd.htf, hd.mtf, **params)
    c = cost.apply_shock(shock) if shock != 1.0 else cost
    return resolve_trades(
        strategy=f"{family}", symbol=hd.symbol, horizon=hd.horizon,
        o=hd.base["o"], h=hd.base["h"], l=hd.base["l"], c=hd.base["c"],
        close_ts=hd.base["close_ts"], atr_arr=hd.atr,
        long_sig=long_sig, short_sig=short_sig,
        atr_mult=risk["atr_mult"], target_r=risk["target_r"],
        max_hold_bars=max_hold_bars, cost=c, maker_entry=maker,
        min_stop_bps=min_stop_bps,
        allow_short=allow_short, trail_atr_mult=risk.get("trail_atr_mult", 0.0))


def select_and_confirm(hd: HorizonData, family: str, cost: CostModel,
                       gate: GateConfig | None = None,
                       maker: bool = False,
                       min_stop_bps: float = 0.0,
                       allow_short: bool = True,
                       grids: Optional[List[dict]] = None,
                       select_cost_mult: float = 1.25) -> Optional[dict]:
    """DEV selection -> VAL confirm -> OOS report -> cost shock.

    Selection is deliberately COST-AWARE: candidates are ranked on DEV while
    paying `select_cost_mult` x real costs. A configuration whose edge is an
    artefact of cheap assumptions therefore loses to one with a genuine,
    cost-robust edge, and it is chosen without ever touching VAL/OOS. This is
    the single most valuable change to this platform's selection step: cost
    sensitivity is the dominant failure mode of crypto intraday systems.
    """
    h = HORIZONS[hd.horizon]
    gate = gate or GateConfig()
    dev_lo, dev_hi = WF.window_bounds(hd.base["close_ts"], hd.windows)[0]
    val_lo, val_hi = WF.window_bounds(hd.base["close_ts"], hd.windows)[1]
    oos_lo, oos_hi = WF.window_bounds(hd.base["close_ts"], hd.windows)[2]
    span_days = int((dev_hi - dev_lo) / 86400)

    grid = []
    for p in (grids if grids is not None else GRIDS[family]):
        for r in RISK_VARIANTS:
            grid.append(dict(params=p, risk=r))

    best = None
    best_score = -np.inf
    for cfg in grid:
        res = simulate_config(hd, family, cfg["params"], cfg["risk"], cost,
                              maker, min_stop_bps, h.max_hold_bars,
                              allow_short=allow_short,
                              shock=select_cost_mult)
        dev = WF.slice_book(res, dev_lo, dev_hi)
        if dev.n < gate.min_dev_trades:
            continue
        # rank on DEV expectancy under stressed costs, tempered by consistency:
        # a config that wins big but loses half its DEV chunks is not real.
        from .evaluate import sign_stability
        stab = sign_stability(dev.rs, 4)
        score = dev.expectancy_r * (0.5 + 0.5 * stab)
        if score > best_score:
            best_score = score
            best = dict(config=cfg, dev=dev, dev_score=score)
    if best is None:
        return None

    cfg = best["config"]
    full = simulate_config(hd, family, cfg["params"], cfg["risk"], cost, maker,
                           min_stop_bps, h.max_hold_bars, allow_short=allow_short)
    dev = WF.slice_book(full, dev_lo, dev_hi)
    val = WF.slice_book(full, val_lo, val_hi)
    oos = WF.slice_book(full, oos_lo, oos_hi)
    shock_book = simulate_config(hd, family, cfg["params"], cfg["risk"], cost,
                                 maker, min_stop_bps, h.max_hold_bars,
                                 allow_short=allow_short,
                                 shock=gate.cost_shock_mult)
    shock = WF.slice_book(shock_book, oos_lo, oos_hi)

    params = dict(cfg["params"]); params.update(cfg["risk"])
    params["maker_entry"] = maker
    v = evaluate_book(family, hd.symbol, hd.horizon, dev, val, oos,
                      dev_span_days=span_days, cost_shock=shock, params=params,
                      cfg=gate)
    return dict(verdict=v, dev=dev, val=val, oos=oos, shock=shock,
                full=full, params=params, family=family,
                symbol=hd.symbol, horizon=hd.horizon)


# ---------------------------------------------------------------------------
# Horizon -> family matrix (every horizon is covered by at least one family)
# ---------------------------------------------------------------------------
MATRIX: Dict[str, List[str]] = {
    "SCALP": ["scalp_micro"],
    "INTRADAY": ["trend_breakout", "mean_revert", "grid_range", "trend_rider"],
    "SWING": ["trend_breakout", "trend_rider", "mean_revert"],
    "POSITION": ["trend_breakout", "trend_rider", "xs_momentum"],
    "INVEST": ["invest_dca", "xs_momentum"],
    "CARRY": ["funding_carry"],
}

ALLOC_FAMILIES = ("xs_momentum", "invest_dca", "funding_carry")


def xs_momentum_books(tf: str, cost: CostModel, symbols: Optional[List[str]] = None,
                      top_k: int = 3, rebalance_bars: int = 7,
                      horizons_to_use=("POSITION", "INVEST")) -> Dict[str, BookResult]:
    """Cross-sectional rotation books; returns {horizon: BookResult}."""
    syms = symbols or D.ASSETS
    panel = D.merged_panel(syms, tf)
    if panel is None:
        return {}
    sig = alloc.xs_momentum_signals(panel, top_k=top_k,
                                    rebalance_bars=rebalance_bars)
    out: Dict[str, BookResult] = {}
    for horizon in horizons_to_use:
        h = HORIZONS[horizon]
        books = []
        for j, sym in enumerate(panel["symbols"]):
            atr_j = ind.atr(panel["h"][:, j], panel["l"][:, j], panel["c"][:, j], 14)
            el, es, xl, xsh = sig[sym]
            book = resolve_trades(
                strategy="xs_momentum", symbol=sym, horizon=horizon,
                o=panel["o"][:, j], h=panel["h"][:, j], l=panel["l"][:, j],
                c=panel["c"][:, j], close_ts=panel["close_ts"], atr_arr=atr_j,
                long_sig=el, short_sig=es, atr_mult=h.atr_mult,
                target_r=h.target_r, max_hold_bars=h.max_hold_bars,
                cost=cost, maker_entry=h.maker_entry,
                min_stop_bps=h.min_stop_bps, allow_short=True,
                exit_long=xl, exit_short=xsh)
            books.append(book)
        out[horizon] = combine_books(books, "xs_momentum", horizon)
    return out


def invest_dca_books(tf: str = "1d", cost: Optional[CostModel] = None,
                     symbols: Optional[List[str]] = None,
                     dd_entry: float = 0.25) -> BookResult:
    """Long-only accumulation book across all assets (INVEST horizon)."""
    cost = cost or DEFAULT
    h = HORIZONS["INVEST"]
    books = []
    for s in (symbols or D.ASSETS):
        d = D.load_ohlcv(s, tf)
        if d is None or d["n"] < 400:
            continue
        a = ind.atr(d["h"], d["l"], d["c"], 14)
        lg, sh, xl = alloc.invest_dca_signals(d, a, dd_entry=dd_entry)
        books.append(resolve_trades(
            strategy="invest_dca", symbol=s, horizon="INVEST",
            o=d["o"], h=d["h"], l=d["l"], c=d["c"], close_ts=d["close_ts"],
            atr_arr=a, long_sig=lg, short_sig=sh, atr_mult=h.atr_mult,
            target_r=h.target_r, max_hold_bars=h.max_hold_bars, cost=cost,
            maker_entry=h.maker_entry, min_stop_bps=h.min_stop_bps,
            allow_short=False, exit_long=xl))
    return combine_books(books, "invest_dca", "INVEST")


def _bounds(book: BookResult):
    """Split a book 60/20/20 by trade count into (dev_lo, dev_hi, ...)."""
    if book.n == 0:
        return (0, 0, 0, 0, 0, 0)
    ts = [t.exit_ts for t in book.trades]
    c1, c2 = int(book.n * 0.6), int(book.n * 0.8)
    return (ts[0], ts[min(c1, book.n - 1)] + 1,
            ts[min(c1, book.n - 1)], ts[min(c2, book.n - 1)] + 1,
            ts[min(c2, book.n - 1)], ts[-1] + 1)


def funding_carry_books(cost: Optional[CostModel] = None,
                        symbols: Optional[List[str]] = None,
                        apr_entry: float = 0.15, apr_exit: float = 0.05,
                        lookback_days: int = 7) -> List[BookResult]:
    """One market-neutral funding book per asset (CARRY horizon)."""
    cost = cost or DEFAULT
    out: List[BookResult] = []
    for s in (symbols or D.ASSETS):
        f = D.load_funding(s)
        daily = D.load_ohlcv(s, "1d")
        if f is None or daily is None or daily["n"] < 120:
            continue
        out.append(alloc.funding_carry_book(
            s, daily, f["ts"], f["rate"], cost=cost,
            apr_entry=apr_entry, apr_exit=apr_exit,
            lookback_days=lookback_days))
    return out


@dataclass
class SweepResult:
    rows: list = field(default_factory=list)
    books: Dict[str, dict] = field(default_factory=dict)
    data_notes: list = field(default_factory=list)
    elapsed_s: float = 0.0

    def promoted(self) -> list:
        return [r for r in self.rows if r["verdict"] == PROMOTABLE]

    def by_verdict(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in self.rows:
            k = r["verdict"] if r["verdict"] == PROMOTABLE else "REJECTED"
            counts[k] = counts.get(k, 0) + 1
        return counts


def _directional_sweep(out, horizons, symbols, cost, gate, verbose):
    """Directional families (one book per asset per family per horizon)."""
    for horizon in horizons:
        h = HORIZONS[horizon]
        for family in MATRIX.get(horizon, []):
            if family in ALLOC_FAMILIES:
                continue
            for sym in symbols:
                hd = prepare(sym, horizon)
                if hd is None:
                    out.data_notes.append(dict(symbol=sym, horizon=horizon,
                                               reason="insufficient_data"))
                    continue
                try:
                    r = select_and_confirm(hd, family, cost, gate=gate,
                                           maker=h.maker_entry,
                                           min_stop_bps=h.min_stop_bps,
                                           allow_short=True)
                except Exception as e:  # one bad asset must not kill the sweep
                    out.data_notes.append(dict(
                        symbol=sym, horizon=horizon,
                        reason=f"error:{type(e).__name__}:{e}"))
                    continue
                if r is None:
                    out.rows.append(dict(strategy=family, symbol=sym,
                                         horizon=horizon,
                                         verdict="REJECTED_DATA",
                                         gates="G1_data=False",
                                         note="no_dev_candidate"))
                    continue
                v = r["verdict"]
                row = v.as_row(); row["note"] = ""
                out.rows.append(row)
                out.books[f"{horizon}|{family}|{sym}"] = r
                if verbose:
                    print(f"  {horizon:8s} {family:15s} {sym:9s} "
                          f"{v.verdict:24s} dev={v.stats.get('dev_exp', 0):+.3f} "
                          f"oos={v.stats.get('oos_exp', 0):+.3f} "
                          f"n={v.stats.get('dev_n', 0)}/{v.stats.get('oos_n', 0)}",
                          flush=True)


def _alloc_sweep(out, symbols, cost, gate):
    """Rotation, accumulation and funding carry books."""
    try:
        xb = xs_momentum_books("1d", cost, symbols)
        for horizon, book in xb.items():
            if book.n == 0:
                continue
            d0, d1, v0, v1, o0, o1 = _bounds(book)
            dev = WF.slice_book(book, d0, d1)
            val = WF.slice_book(book, v0, v1)
            oos = WF.slice_book(book, o0, o1)
            v = evaluate_book("xs_momentum", "PORTFOLIO", horizon, dev, val,
                              oos, cfg=gate)
            out.rows.append(dict(v.as_row(), note="cross-sectional rotation"))
            out.books[f"{horizon}|xs_momentum|PORTFOLIO"] = dict(
                verdict=v, dev=dev, val=val, oos=oos, full=book,
                params=dict(top_k=3, rebalance_bars=7), symbol="PORTFOLIO",
                family="xs_momentum", horizon=horizon)
    except Exception as e:
        out.data_notes.append(dict(symbol="PORTFOLIO", horizon="XS",
                                   reason=f"error:{type(e).__name__}:{e}"))

    try:
        dca = invest_dca_books("1d", cost, symbols)
        if dca.n:
            d0, d1, v0, v1, o0, o1 = _bounds(dca)
            dev = WF.slice_book(dca, d0, d1)
            val = WF.slice_book(dca, v0, v1)
            oos = WF.slice_book(dca, o0, o1)
            v = evaluate_book("invest_dca", "PORTFOLIO", "INVEST", dev, val,
                              oos, cfg=gate)
            out.rows.append(dict(v.as_row(), note="long-only accumulation"))
            out.books["INVEST|invest_dca|PORTFOLIO"] = dict(
                verdict=v, dev=dev, val=val, oos=oos, full=dca, params={},
                symbol="PORTFOLIO", family="invest_dca", horizon="INVEST")
    except Exception as e:
        out.data_notes.append(dict(symbol="PORTFOLIO", horizon="DCA",
                                   reason=f"error:{type(e).__name__}:{e}"))

    try:
        # Carry is inherently low-frequency per asset (~2-8 entries/year), so
        # a single-asset book can never reach G1's 15-trade OOS floor. We
        # aggregate across all eligible assets into one PORTFOLIO-level book —
        # exactly the pattern used by xs_momentum and invest_dca — so the
        # family has enough trades to be statistically governable.
        #
        # Params are fixed to the platform's carry cost-coverage floor
        # (apr_entry=15%, apr_exit=5%, lb=7d). A separate parameter sweep
        # (carry_sweep.py) explores the grid and writes its recommendation to
        # carry_sweep.json; if and when that recommendation is promoted into
        # the main platform, the params below are updated here.
        cb = funding_carry_books(cost, symbols,
                                 apr_entry=0.15, apr_exit=0.05, lookback_days=7)
        if cb:
            agg = BookResult(strategy="funding_carry", horizon="CARRY")
            for b in cb:
                agg.trades.extend(b.trades)
            agg.trades.sort(key=lambda t: t.exit_ts)
            agg.signal_count = sum(b.signal_count for b in cb)
            if agg.n >= 3:
                d0, d1, v0, v1, o0, o1 = _bounds(agg)
                dev = WF.slice_book(agg, d0, d1)
                val = WF.slice_book(agg, v0, v1)
                oos = WF.slice_book(agg, o0, o1)
                net = sum(t.meta.get("net", 0.0) for t in agg.trades)
                held = sum(t.bars_held for t in agg.trades)
                v = evaluate_book("funding_carry", "PORTFOLIO", "CARRY",
                                  dev, val, oos, cfg=gate,
                                  extra_stats=dict(
                                      total_net=round(net, 4),
                                      days_in_market=held,
                                      net_per_year=round(net / max(1, held) * 365, 4)))
                out.rows.append(dict(v.as_row(), note="market-neutral spot+perp (10-asset agg)"))
                out.books["CARRY|funding_carry|PORTFOLIO"] = dict(
                    verdict=v, dev=dev, val=val, oos=oos, full=agg, params={},
                    symbol="PORTFOLIO", family="funding_carry", horizon="CARRY")
    except Exception as e:
        out.data_notes.append(dict(symbol="PORTFOLIO", horizon="CARRY",
                                   reason=f"error:{type(e).__name__}:{e}"))


def run_all(horizons=None, symbols=None, gate: Optional[GateConfig] = None,
            cost: Optional[CostModel] = None, verbose: bool = True,
            include_alloc: bool = True) -> SweepResult:
    """Sweep every (horizon, family, asset) with full walk-forward + gates."""
    cost = cost or DEFAULT
    gate = gate or GateConfig()
    horizons = list(horizons or HORIZON_ORDER)
    symbols = list(symbols or D.ASSETS)
    t0 = time.time()
    out = SweepResult()
    _directional_sweep(out, horizons, symbols, cost, gate, verbose)
    if include_alloc:
        _alloc_sweep(out, symbols, cost, gate)
    out.elapsed_s = round(time.time() - t0, 1)
    return out





def combine_books(books: List[BookResult], strategy: str,
                  horizon: str) -> BookResult:
    """Merge per-asset books into one strategy-level book (equal risk per asset)."""
    merged = BookResult(strategy=strategy, horizon=horizon)
    for b in books:
        merged.trades.extend(b.trades)
    merged.trades.sort(key=lambda t: t.exit_ts)
    merged.signal_count = sum(b.signal_count for b in books)
    merged.skipped_cost = sum(b.skipped_cost for b in books)
    return merged


def economic_screen_rows(cost: Optional[CostModel] = None) -> list:
    """Pre-trade economics table (delegates to horizons.economic_screen)."""
    from .horizons import economic_screen
    return economic_screen(cost)


def measure_median_atr_bps(horizons=None, symbols=None) -> Dict[str, float]:
    """MEDIAN ATR of each horizon's LTF, measured from the actual cache.

    This replaces the hard-coded constants in costs.MEDIAN_ATR_BPS with live
    numbers, so the economics screen reflects the data on disk rather than a
    figure someone typed months ago.
    """
    from .horizons import HORIZONS as _H, HORIZON_ORDER as _O
    horizons = list(horizons or _O)
    symbols = list(symbols or D.ASSETS)
    out: Dict[str, float] = {}
    for key in horizons:
        h = _H[key]
        if h.atr_mult <= 0:
            continue
        vals = []
        for s in symbols:
            d = D.load_ohlcv(s, h.ltf)
            if d is None or d["n"] < 200:
                continue
            a = ind.atr(d["h"], d["l"], d["c"], 14)
            ok = np.isfinite(a) & (a > 0) & np.isfinite(d["c"]) & (d["c"] > 0)
            if ok.sum() < 100:
                continue
            vals.append(float(np.median(a[ok] / d["c"][ok] * 1e4)))
        if vals:
            out[key] = float(np.median(vals))
    return out



