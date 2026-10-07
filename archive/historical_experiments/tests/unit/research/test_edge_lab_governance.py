"""Edge Lab governance tests: causality, cost-awareness, no-OOS-tune, gates."""
import numpy as np
from research.edge_lab.engine import run_stream
from research.edge_lab.indicators import donchian
from research.edge_lab.promotion import evaluate


def test_next_bar_open_no_lookahead():
    n = 50
    o = np.arange(n, dtype=float) + 100
    h = o + 1
    l = o - 1
    c = o.copy()
    a = np.ones(n)
    sL = np.zeros(n, dtype=bool)
    sS = np.zeros(n, dtype=bool)
    sL[10] = True
    r = run_stream(sL, sS, o, h, l, c, a, 2.0, 2.0, 10)
    assert r.n >= 1
    assert int(r.entry_idx[0]) == 11  # signal bar 10 -> fill bar 11 open


def test_adverse_first_collision_prefers_sl():
    n = 20
    o = np.full(n, 100.0)
    h = np.full(n, 110.0)
    l = np.full(n, 90.0)
    c = np.full(n, 100.0)
    a = np.full(n, 1.0)
    sL = np.zeros(n, dtype=bool)
    sS = np.zeros(n, dtype=bool)
    sL[5] = True
    # stop=99ish (atr 2*1=2 -> sl=98+slip), tp=102+ -> both inside [90,110]
    r = run_stream(sL, sS, o, h, l, c, a, 2.0, 2.0, 10)
    assert r.n >= 1
    assert r.exit_reason[0] == "SL"


def test_costs_reduce_edge_monotonically():
    rng = np.random.default_rng(0)
    n = 500
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    o = np.roll(c, 1)
    o[0] = c[0]
    h = np.maximum(o, c) + 0.5
    l = np.minimum(o, c) - 0.5
    a = np.full(n, 2.0)
    sL = np.zeros(n, dtype=bool)
    sS = np.zeros(n, dtype=bool)
    sL[::10] = True
    r0 = run_stream(sL, sS, o, h, l, c, a, 1.5, 2.0, 10,
                    fee_pct=0.0, slip_pct=0.0, spread_pct=0.0)
    r1 = run_stream(sL, sS, o, h, l, c, a, 1.5, 2.0, 10)
    assert r1.net_r <= r0.net_r + 1e-9


def test_promotion_gate_rejects_sign_flip():
    row = dict(status="MEASURED",
               best=dict(dev_n=50, dev_exp=0.3, dev_pf=1.5, dev_dd=5.0),
               val=dict(n=25, exp=-0.1, pf=0.9, dd=5.0),
               oos=dict(n=20, exp=0.2, pf=1.3, dd=5.0))
    v, _ = evaluate(row, np.ones(20) * 0.1, 0.1)
    assert v == "REJECTED"
