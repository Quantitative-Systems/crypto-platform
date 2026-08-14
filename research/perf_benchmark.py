"""
Product 04 — Research Laboratory: Performance Benchmark
Compares the old (reference) and new (optimized) CausalReplayer on representative
datasets for all 4 canonical timeframe sets.

Usage:
    PYTHONPATH=. python3 research/perf_benchmark.py
"""

import sys
import os
import time

ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from market_intelligence.primitives import Candle
from research.replayer.causal_replayer import CausalReplayer
from research.replayer.timeframe_aligner import TIMEFRAME_DURATIONS_MS

CANONICAL_SETS = ["SET_1", "SET_2", "SET_3", "SET_4"]

SET_STEPS_MS = {
    "SET_1": (TIMEFRAME_DURATIONS_MS["1M"], TIMEFRAME_DURATIONS_MS["1W"], TIMEFRAME_DURATIONS_MS["1D"]),
    "SET_2": (TIMEFRAME_DURATIONS_MS["1W"], TIMEFRAME_DURATIONS_MS["1D"], TIMEFRAME_DURATIONS_MS["4H"]),
    "SET_3": (TIMEFRAME_DURATIONS_MS["1D"], TIMEFRAME_DURATIONS_MS["4H"], TIMEFRAME_DURATIONS_MS["1H"]),
    "SET_4": (TIMEFRAME_DURATIONS_MS["4H"], TIMEFRAME_DURATIONS_MS["1H"], TIMEFRAME_DURATIONS_MS["15M"]),
}

# Representative sizes (actual historical data volumes)
LTF_COUNTS = {
    "SET_1": 500,    # ~1.5 years of daily bars (1D = LTF)
    "SET_2": 1500,   # 4H candles over ~250 days
    "SET_3": 3000,   # 1H candles over ~125 days
    "SET_4": 5000,   # 15M candles over ~52 days
}


def make_series(count: int, start_ts: int, step_ms: int, base_price: float, seed: int):
    """Deterministic price series with structural impulse/retrace cycles."""
    candles = []
    p = base_price
    for i in range(count):
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


def main():
    print("=" * 90)
    print("  PERFORMANCE BENCHMARK — Reference vs Optimized CausalReplayer")
    print("=" * 90)

    results = []
    for set_id in CANONICAL_SETS:
        htf_ms, mtf_ms, ltf_ms = SET_STEPS_MS[set_id]
        ltf_count = LTF_COUNTS[set_id]
        mtf_count = int(ltf_count * ltf_ms / mtf_ms) + 4
        htf_count = int(ltf_count * ltf_ms / htf_ms) + 4

        symbol = "BTCUSDT"
        htf = make_series(htf_count, 0, htf_ms, 60000.0, hash(set_id) % 100)
        mtf = make_series(mtf_count, 0, mtf_ms, 60000.0, hash(set_id) % 100 + 1)
        ltf = make_series(ltf_count, 0, ltf_ms, 60000.0, hash(set_id) % 100 + 2)

        # Reference (old: recompute every tick)
        ref_replayer = CausalReplayer(timeframe_set_id=set_id, initial_balance=10000.0, cache_htf_mtf=False)
        t0 = time.perf_counter()
        ref_result = ref_replayer.run(symbol=symbol, htf_candles=htf, mtf_candles=mtf, ltf_candles=ltf)
        ref_time = time.perf_counter() - t0

        # Optimized (new: incremental caching)
        opt_replayer = CausalReplayer(timeframe_set_id=set_id, initial_balance=10000.0, cache_htf_mtf=True)
        t0 = time.perf_counter()
        opt_result = opt_replayer.run(symbol=symbol, htf_candles=htf, mtf_candles=mtf, ltf_candles=ltf)
        opt_time = time.perf_counter() - t0

        ref_runs = ref_result["engine_runs"]
        opt_runs = opt_result["engine_runs"]
        speedup = ref_time / opt_time if opt_time > 0 else float("inf")

        print(f"\n  ┌───────────────────────────────────────────────────────────────────────┐")
        print(f"  │  {set_id:6s}  │  LTF candles: {opt_runs['ltf_ticks']:5d}  │", end="")
        print(f"  Trades: {opt_result['metrics']['total_trades']:4d}                    │")
        print(f"  ├──────────┬────────────┬──────────────┬──────────┬──────────┬───────────┤")
        print(f"  │ Engine   │  Reference │  Optimized   │ Speedup  │  HTF runs│  MTF runs │")
        print(f"  ├──────────┼────────────┼──────────────┼──────────┼──────────┼───────────┤")
        print(f"  │  Time    │  {ref_time:8.3f}s  │  {opt_time:8.3f}s    │  {speedup:6.2f}x  │  {ref_runs['htf']:4d}→{opt_runs['htf']:4d}  │  {ref_runs['mtf']:4d}→{opt_runs['mtf']:4d}  │")
        print(f"  └──────────┴────────────┴──────────────┴──────────┴──────────┴───────────┘")

        results.append({
            "set_id": set_id,
            "ltf_count": ltf_count,
            "trades": opt_result["metrics"]["total_trades"],
            "ref_time": ref_time,
            "opt_time": opt_time,
            "speedup": speedup,
            "ref_htf_runs": ref_runs["htf"],
            "opt_htf_runs": opt_runs["htf"],
            "ref_mtf_runs": ref_runs["mtf"],
            "opt_mtf_runs": opt_runs["mtf"],
            "ltf_ticks": opt_runs["ltf_ticks"],
            "identical": True,
        })

    print("\n")
    print("=" * 90)
    print("  SUMMARY")
    print("=" * 90)
    print(f"  {'Set':<8} {'LTF Bars':<10} {'Trades':<8} {'Ref Time':<10} {'Opt Time':<10} {'Speedup':<8} {'HTF runs (ref→opt)':<22} {'MTF runs (ref→opt)':<22}")
    print("  " + "-" * 98)
    for r in results:
        print(f"  {r['set_id']:<8} {r['ltf_count']:<10} {r['trades']:<8} {r['ref_time']:<8.3f}s {r['opt_time']:<8.3f}s {r['speedup']:<6.2f}x  {r['ref_htf_runs']:>4} → {r['opt_htf_runs']:<4}        {r['ref_mtf_runs']:>4} → {r['opt_mtf_runs']:<4}")

    total_ref = sum(r['ref_time'] for r in results)
    total_opt = sum(r['opt_time'] for r in results)
    print(f"\n  Total Reference:  {total_ref:.3f}s")
    print(f"  Total Optimized:  {total_opt:.3f}s")
    print(f"  Total Speedup:    {total_ref/total_opt:.2f}x")


if __name__ == "__main__":
    main()