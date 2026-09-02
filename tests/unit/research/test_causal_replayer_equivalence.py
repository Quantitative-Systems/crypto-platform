"""
Product 04 — CausalReplayer Reference-Equivalence Suite

Validates that the optimized incremental-state CausalReplayer (cache_htf_mtf=True)
produces IDENTICAL canonical decisions to the original recompute-every-tick reference
implementation (cache_htf_mtf=False).

This is a RESEARCH ENGINE PERFORMANCE refactor audit. It proves:
  - same HTF/MFT/LTF causal visibility
  - same structure / swings / BOS / CHOCH / KeyZones / phases / trend derivation
  - same candidate admission, entry price, SL, TP, R:R, position sizing
  - same MTF structural trailing ratchet, exits and friction
  - same trade lifecycle and equity curve

while additionally proving the optimized engine performs far fewer redundant
P01 (market-intelligence) rebuilds of the higher timeframes.
"""

import pytest
from market_intelligence.primitives import Candle
from research.replayer.causal_replayer import CausalReplayer

CANONICAL_SETS = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]

# Mappings of canonical set -> (htf_ms, mtf_ms, ltf_ms) candle alignment step
SET_STEPS_MS = {
    "SET_1": (30 * 24 * 3600 * 1000, 7 * 24 * 3600 * 1000, 24 * 3600 * 1000),
    "SET_2": (7 * 24 * 3600 * 1000, 24 * 3600 * 1000, 4 * 3600 * 1000),
    "SET_3": (24 * 3600 * 1000, 4 * 3600 * 1000, 3600 * 1000),
    "SET_4": (4 * 3600 * 1000, 3600 * 1000, 15 * 60 * 1000),
    "SET_5": (15 * 60 * 1000, 5 * 60 * 1000, 60 * 1000),
}

LTF_COUNTS = {
    "SET_1": 260,
    "SET_2": 460,
    "SET_3": 900,
    "SET_4": 900,
    "SET_5": 900,
}


def _make_series(
    count: int,
    start_ts: int,
    step_ms: int,
    base_price: float,
    seed: int,
):
    """Deterministic but structurally rich zig-zag price series."""
    candles = []
    p = base_price
    for i in range(count):
        # Broad alternating impulses + small jitter create swings/retests.
        if seed % 3 == 0:
            delta = 3.0 if (i // 6) % 2 == 0 else -2.5
        elif seed % 3 == 1:
            delta = -3.0 if (i // 7) % 2 == 0 else 2.5
        else:
            delta = 2.2 if (i // 5) % 2 == 0 else -1.8
        p += delta
        candles.append(Candle(
            timestamp=start_ts + (i * step_ms),
            open=p - delta,
            high=max(p, p - delta) + 4.0,
            low=min(p, p - delta) - 4.0,
            close=p,
            volume=100.0 + (i % 50),
        ))
    return candles


def _strip_state_identifiers(result: dict):
    """Remove run-specific UUID identifiers so reference/optimized can be compared."""
    stripped = {
        "metrics": result["metrics"],
        "exit_attribution": result["exit_attribution"],
        "failure_modes": result["failure_modes"],
        "equity_curve": result["equity_curve"],
    }
    # closed trades: compare every field except the run-unique trade_id
    trades = []
    for t in result["closed_trades"]:
        t2 = dict(t)
        t2.pop("trade_id", None)
        trades.append(t2)
    stripped["closed_trades"] = trades
    return stripped


@pytest.mark.parametrize("set_id", CANONICAL_SETS)
@pytest.mark.parametrize("seed", [0, 1])
def test_optimized_replayer_matches_reference_decision_for_every_stream(set_id, seed):
    htf_ms, mtf_ms, ltf_ms = SET_STEPS_MS[set_id]
    ltf_count = LTF_COUNTS[set_id]
    mtf_count = int(ltf_count * ltf_ms / mtf_ms) + 4
    htf_count = int(ltf_count * ltf_ms / htf_ms) + 4

    symbol = "BTCUSDT"
    htf = _make_series(htf_count, 0, htf_ms, 60000.0, seed)
    mtf = _make_series(mtf_count, 0, mtf_ms, 60000.0, seed)
    ltf = _make_series(ltf_count, 0, ltf_ms, 60000.0, seed)

    reference = CausalReplayer(timeframe_set_id=set_id, initial_balance=10000.0, cache_htf_mtf=False)
    optimized = CausalReplayer(timeframe_set_id=set_id, initial_balance=10000.0, cache_htf_mtf=True)

    ref_result = reference.run(symbol=symbol, htf_candles=htf, mtf_candles=mtf, ltf_candles=ltf)
    opt_result = optimized.run(symbol=symbol, htf_candles=htf, mtf_candles=mtf, ltf_candles=ltf)

    assert _strip_state_identifiers(ref_result) == _strip_state_identifiers(opt_result), \
        f"Reference vs Optimized decision mismatch on {set_id} (seed={seed})"
    assert len(ref_result["closed_trades"]) == len(opt_result["closed_trades"])


@pytest.mark.parametrize("set_id", CANONICAL_SETS)
def test_optimized_replayer_dramatically_reduces_htf_mtf_rebuilds(set_id):
    """Prove the caching actually engages and removes redundant P01 rebuilds."""
    htf_ms, mtf_ms, ltf_ms = SET_STEPS_MS[set_id]
    ltf_count = LTF_COUNTS[set_id]
    mtf_count = int(ltf_count * ltf_ms / mtf_ms) + 4
    htf_count = int(ltf_count * ltf_ms / htf_ms) + 4

    symbol = "BTCUSDT"
    htf = _make_series(htf_count, 0, htf_ms, 60000.0, 0)
    mtf = _make_series(mtf_count, 0, mtf_ms, 60000.0, 0)
    ltf = _make_series(ltf_count, 0, ltf_ms, 60000.0, 0)

    optimized = CausalReplayer(timeframe_set_id=set_id, initial_balance=10000.0, cache_htf_mtf=True)
    opt_result = optimized.run(symbol=symbol, htf_candles=htf, mtf_candles=mtf, ltf_candles=ltf)

    runs = opt_result["engine_runs"]
    # With caching, HTF/MTF state is rebuilt far fewer times than there are LTF ticks.
    assert runs["htf"] < runs["ltf_ticks"], f"HTF cache not reducing rebuilds on {set_id}"
    assert runs["mtf"] < runs["ltf_ticks"], f"MTF cache not reducing rebuilds on {set_id}"
    # And the higher the timeframe, the rarer the rebuilds should be.
    assert runs["htf"] <= runs["mtf"], f"HTF should rebuild <= MTF on {set_id}"


def test_optimized_replayer_used_by_default():
    """The default execution path must run the optimized engine."""
    assert CausalReplayer().cache_htf_mtf is True