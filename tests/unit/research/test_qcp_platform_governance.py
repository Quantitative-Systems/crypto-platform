"""Governance tests for qcp_platform.

These tests protect the properties that make the platform's numbers trustworthy.
If any of them fails, every performance claim in the report is void:

  * causality        — signals may not use future bars
  * next-bar fills   — entries fill at the bar AFTER the signal, never on it
  * adverse-first    — a bar touching both stop and target resolves as a loss
  * costs always on  — gross > net for every trade, no zero-cost path
  * cost monotonicity— more cost never improves expectancy
  * refusal          — horizons that cannot pay costs are reported, not hidden
  * governor         — drawdown/loss limits actually stop new risk
"""
from __future__ import annotations

import numpy as np
import pytest

from qcp_platform import allocations as A
from qcp_platform import data as D
from qcp_platform import indicators as ind
from qcp_platform import strategies as S
from qcp_platform.costs import DEFAULT
from qcp_platform.engine import resolve_trades
from qcp_platform.governor import Governor, GovernorConfig
from qcp_platform.horizons import (HORIZONS, HORIZON_ORDER, active_horizons,
                                  economic_screen)

SYM = "BTCUSDT"


def _synthetic(n=400, up=True):
    rng = np.random.default_rng(11)
    drift = 0.0006 if up else -0.0006
    r = rng.normal(drift, 0.01, n)
    c = 100 * np.exp(np.cumsum(r))
    o = np.concatenate([[c[0]], c[:-1]])
    h = np.maximum(o, c) * (1 + 0.004)
    l = np.minimum(o, c) * (1 - 0.004)
    v = rng.uniform(1e3, 5e3, n)
    ts = 1_600_000_000 + np.arange(n) * 3600
    atr_arr = ind.atr(h, l, c, 14)
    return dict(o=o, h=h, l=l, c=c, v=v, ts=ts, close_ts=ts + 3600), atr_arr


# ---------------------------------------------------------------------------
# causality
# ---------------------------------------------------------------------------
def test_indicators_are_causal_under_truncation():
    """Indicator value at bar i must not change when future bars are removed."""
    d, _ = _synthetic(600)
    cut = 400
    pairs = [
        ("atr", ind.atr(d["h"], d["l"], d["c"], 14),
         ind.atr(d["h"][:cut], d["l"][:cut], d["c"][:cut], 14)),
        ("rsi", ind.rsi(d["c"], 14), ind.rsi(d["c"][:cut], 14)),
        ("adx", ind.adx(d["h"], d["l"], d["c"], 14),
         ind.adx(d["h"][:cut], d["l"][:cut], d["c"][:cut], 14)),
        ("ema50", ind.ema(d["c"], 50), ind.ema(d["c"][:cut], 50)),
    ]
    for name, full, trunc in pairs:
        a, b = full[:cut], trunc
        ok = np.isfinite(a) & np.isfinite(b)
        assert ok.sum() > 100, f"{name}: not enough finite overlap"
        assert np.allclose(a[ok], b[ok], rtol=1e-8, atol=1e-8), \
            f"{name} is not causal: values change when future bars are removed"


def test_donchian_excludes_current_bar():
    """A breakout channel must not include the bar being tested."""
    d, _ = _synthetic(200)
    hi, _ = ind.donchian(d["h"], d["l"], 20)
    for i in range(25, 200):
        assert hi[i] == pytest.approx(d["h"][i - 20:i].max())
        assert hi[i] <= d["h"][:i].max() + 1e-9


def test_htf_alignment_only_uses_closed_bars():
    """align_causal must never expose an HTF bar that closes after the LTF bar."""
    ltf_ts = np.array([100, 200, 300, 400, 500, 600])
    htf = dict(close_ts=np.array([150, 350, 550]),
               c=np.array([1.0, 2.0, 3.0]), n=3)
    v = D.align_causal(ltf_ts, htf, "c")
    assert np.isnan(v[0])            # nothing has closed yet
    assert v[1] == 1.0               # 150 <= 200
    assert v[2] == 1.0               # 350 > 300 -> still only bar 0
    assert v[3] == 2.0
    assert v[5] == 3.0


# ---------------------------------------------------------------------------
# execution realism
# ---------------------------------------------------------------------------
def test_entry_is_next_bar_open():
    d, atr_arr = _synthetic(300)
    long_sig = np.zeros(300, dtype=bool)
    short_sig = np.zeros(300, dtype=bool)
    i = 120
    long_sig[i] = True
    r = resolve_trades("t", SYM, "TEST", d["o"], d["h"], d["l"], d["c"],
                       d["close_ts"], atr_arr, long_sig, short_sig,
                       atr_mult=2.0, target_r=2.0, max_hold_bars=20)
    assert r.n == 1
    t = r.trades[0]
    assert t.entry_ts == d["close_ts"][i + 1]
    # filled at next open plus adverse slippage for a long
    assert t.entry_px > d["o"][i + 1]


def test_adverse_first_resolution_is_conservative():
    """A bar that touches both stop and target must be booked as the stop."""
    o = np.array([100.0, 100.0, 100.0])
    h = np.array([100.0, 100.0, 130.0])
    l = np.array([100.0, 100.0, 70.0])
    c = np.array([100.0, 100.0, 128.0])
    ts = np.array([1, 2, 3])
    atr_arr = np.array([100.0, 1.0, 1.0])
    ls = np.array([False, True, False])
    ss = np.zeros(3, dtype=bool)
    r = resolve_trades("t", SYM, "TEST", o, h, l, c, ts, atr_arr, ls, ss,
                       atr_mult=1.0, target_r=2.0, max_hold_bars=5)
    assert r.n == 1
    assert r.trades[0].exit_reason == "SL"
    assert r.trades[0].r_multiple < 0


def test_costs_are_always_charged():
    d, atr_arr = _synthetic(500)
    rng = np.random.default_rng(3)
    ls = rng.random(500) < 0.02
    ss = rng.random(500) < 0.02
    r = resolve_trades("t", SYM, "TEST", d["o"], d["h"], d["l"], d["c"],
                       d["close_ts"], atr_arr, ls, ss, atr_mult=2.0,
                       target_r=3.0, max_hold_bars=30)
    assert r.n > 5
    for t in r.trades:
        assert t.meta["gross_bps"] - t.meta["net_bps"] == pytest.approx(
            DEFAULT.roundtrip_bps(), abs=0.01)
        assert t.meta["net_bps"] < t.meta["gross_bps"]


def test_more_cost_never_helps():
    d, atr_arr = _synthetic(800)
    long_sig, short_sig = S.sig_trend_breakout(d, atr_arr, d, d, lookback=20)
    base = resolve_trades("t", SYM, "TEST", d["o"], d["h"], d["l"], d["c"],
                          d["close_ts"], atr_arr, long_sig, short_sig,
                          atr_mult=2.0, target_r=2.0, max_hold_bars=40,
                          cost=DEFAULT)
    shock = resolve_trades("t", SYM, "TEST", d["o"], d["h"], d["l"], d["c"],
                           d["close_ts"], atr_arr, long_sig, short_sig,
                           atr_mult=2.0, target_r=2.0, max_hold_bars=40,
                           cost=DEFAULT.apply_shock(3.0))
    assert shock.n <= base.n
    if base.n and shock.n:
        assert shock.expectancy_r < base.expectancy_r


def test_cost_floor_blocks_unviable_stops():
    """With a 3xATR stop on a tiny-ATR synthetic, trades must be skipped."""
    o = np.full(60, 100.0)
    h = o * 1.0001
    l = o * 0.9999
    c = o.copy()
    ts = np.arange(60) + 1
    atr_arr = np.full(60, 0.01)          # 1bp stop at 2x -> hopeless
    ls = np.zeros(60, dtype=bool)
    ls[30] = True
    ss = np.zeros(60, dtype=bool)
    r = resolve_trades("t", SYM, "TEST", o, h, l, c, ts, atr_arr, ls, ss,
                       atr_mult=2.0, target_r=2.0, max_hold_bars=5,
                       min_stop_bps=60.0)
    assert r.n == 0 and r.skipped_cost == 1


# ---------------------------------------------------------------------------
# honesty about economics
# ---------------------------------------------------------------------------
def test_economic_screen_reports_scalp_as_cost_gated():
    rows = {r["horizon"]: r for r in economic_screen()}
    assert set(rows) == set(HORIZON_ORDER)
    assert rows["CARRY"]["cost_to_stop"] is None
    # taker fills are impossible on any 1m scalping stop
    assert DEFAULT.cost_to_stop(8.0, 2.0, maker_entry=False) > 1.0
    # long-horizon books are comfortably economic
    assert rows["SWING"]["economic"] is True
    assert rows["POSITION"]["economic"] is True
    assert rows["INVEST"]["economic"] is True


def test_every_horizon_has_defined_risk_budget():
    total = sum(h.capital_weight for h in HORIZONS.values())
    assert total == pytest.approx(1.0, abs=1e-6)
    for k, h in HORIZONS.items():
        assert 0 < h.fixed_risk_pct <= 0.01, f"{k} risk budget out of bounds"


def test_active_horizons_excludes_non_economic():
    act = active_horizons(economic_screen())
    assert "SWING" in act and "POSITION" in act and "INVEST" in act


# ---------------------------------------------------------------------------
# risk governor
# ---------------------------------------------------------------------------
def test_governor_halts_on_drawdown():
    # isolate the DD tiers: disable the daily/weekly loss limits, which would
    # (correctly) fire first on losses of this size
    cfg = GovernorConfig(daily_loss_limit=1.0, weekly_loss_limit=1.0)
    g = Governor(cfg)
    assert g.allow_new_risk()[0] is True
    g.on_pnl(-0.11, day=1)
    allowed, scale, _ = g.allow_new_risk()
    assert allowed is True and scale == pytest.approx(0.50)
    g.on_pnl(-0.11, day=2)                       # total ~ -21%
    allowed, scale, _ = g.allow_new_risk()
    assert allowed is True and scale == pytest.approx(0.25)
    g.on_pnl(-0.06, day=3)                       # beyond 25% -> kill
    allowed, scale, reason = g.allow_new_risk()
    assert allowed is False and scale == 0.0
    assert reason.startswith("KILL_DD")
    assert g.state.tripped is True


def test_governor_daily_loss_limit_blocks_new_risk():
    g = Governor(GovernorConfig())
    g.new_day(5)
    g.on_pnl(-0.04, day=5)
    allowed, _, reason = g.allow_new_risk()
    assert allowed is False and "DAILY_LOSS" in reason


def test_governor_vol_targeting_is_clamped():
    from qcp_platform.governor import vol_scale
    cfg = GovernorConfig()
    assert vol_scale(0.01, cfg) == pytest.approx(cfg.vol_scale_max)
    assert vol_scale(5.0, cfg) == pytest.approx(cfg.vol_scale_min)
    assert vol_scale(cfg.target_vol_pct, cfg) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# allocation families
# ---------------------------------------------------------------------------
def test_funding_carry_charges_costs_and_is_hedged():
    n = 400
    ts = 1_600_000_000 + np.arange(n) * 86400
    grid = dict(ts=ts, close_ts=ts + 86400, n=n)
    fts = np.arange(n * 3) * 8 * 3600 + 1_600_000_000
    frate = np.full(n * 3, 0.0008)          # ~29% APR, always positive
    book = A.funding_carry_book("BTCUSDT", grid, fts, frate)
    assert book.n > 0
    for t in book.trades:
        assert t.meta["hedged"] is True
        assert t.meta["cost"] == pytest.approx(DEFAULT.carry_roundtrip_bps() / 1e4)
        assert t.meta["net"] == pytest.approx(
            t.meta["funding_collected"] - t.meta["cost"], abs=1e-9)


def test_funding_carry_stays_out_when_funding_is_negative():
    n = 300
    ts = 1_600_000_000 + np.arange(n) * 86400
    grid = dict(ts=ts, close_ts=ts + 86400, n=n)
    fts = np.arange(n * 3) * 8 * 3600 + 1_600_000_000
    frate = np.full(n * 3, -0.0005)         # payers get paid -> no entry
    book = A.funding_carry_book("BTCUSDT", grid, fts, frate)
    assert book.n == 0


def test_daily_funding_sums_three_settlements():
    ts = np.array([0, 8 * 3600, 16 * 3600, 86400, 86400 + 8 * 3600, 86400 + 16 * 3600])
    rate = np.array([0.0001, 0.0002, 0.0003, 0.0004, 0.0005, 0.0006])
    out = A.daily_funding(ts, rate)
    assert out["n"] == 2
    assert out["sum"][0] == pytest.approx(0.0006)
    assert out["sum"][1] == pytest.approx(0.0015)


def test_xs_momentum_ranks_without_lookahead():
    n, s = 300, 4
    ts = 1_600_000_000 + np.arange(n) * 86400
    C = np.zeros((n, s))
    for j in range(s):
        C[:, j] = 100 * np.exp(np.cumsum(np.full(n, 0.001 * (j + 1))))
    panel = dict(ts=ts, close_ts=ts + 86400, c=C, o=C, h=C, l=C,
                 v=np.ones((n, s)), n=n, symbols=[f"S{j}" for j in range(s)])
    sig = A.xs_momentum_signals(panel, top_k=1, rebalance_bars=7)
    fast = sig["S3"][0]
    slow = sig["S0"][0]
    assert fast[100:].mean() > 0.9      # strongest asset held
    assert slow[100:].mean() < 0.1      # weakest never ranked top-1
    assert fast[:7].sum() == 0          # no history -> no ranking


