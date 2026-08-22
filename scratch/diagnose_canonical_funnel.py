"""
Forensic Funnel Diagnostic on Canonical BTC S3 Baseline (50,000 candles).
Traces every step from HTF Context -> MTF Setup -> MTF KeyZone -> Retest -> LTF Trigger -> Entry -> Rejection.
"""

from typing import Dict, List, Any
import time
from collections import Counter

from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.primitives import Candle, TrendDirection, MarketPhase
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from strategy_engine.context.htf_context_engine import HTFContextEngine, ExpectedMove
from strategy_engine.contracts.strategy_state import CandidateState
from research.replayer.timeframe_aligner import TimeframeAligner, TimeframeSet


def diagnose_funnel():
    print("Loading candles...")
    htf_candles = WarehouseLoader.load_history("BTC/USDT", "1d", 50000)
    mtf_candles = WarehouseLoader.load_history("BTC/USDT", "4h", 50000)
    ltf_candles = WarehouseLoader.load_history("BTC/USDT", "1h", 50000)

    timeframe_set = TimeframeAligner.get_set("SET_3")
    lang_coord = LanguageCoordinator(buffer_size=300)
    strat_coord = StrategyCoordinator()

    htf_cache = {"key": None, "state": None}
    mtf_cache = {"key": None, "state": None}

    stats = {
        "total_bars": len(ltf_candles),
        "htf_evals": 0,
        "htf_contexts_by_move": Counter(),
        "candidates_created": 0,
        "candidates_by_hyp": Counter(),
        "state_transitions": Counter(),
        "plans_emitted": 0,
        "plans_by_status": Counter(),
        "rejection_reasons": Counter()
    }

    # Trace candidate tracking events
    print("Running diagnostic loop over 50,000 candles...")
    t0 = time.time()

    for i in range(15, len(ltf_candles)):
        current_bar = ltf_candles[i]
        decision_timestamp = current_bar.timestamp

        ltf_slice = ltf_candles[max(0, i - 150):i + 1]
        mtf_slice = TimeframeAligner.filter_visible_candles(
            mtf_candles, decision_timestamp, timeframe_set.mtf, buffer_size=100
        )
        htf_slice = TimeframeAligner.filter_visible_candles(
            htf_candles, decision_timestamp, timeframe_set.htf, buffer_size=80
        )

        if len(htf_slice) < 5 or len(mtf_slice) < 5 or len(ltf_slice) < 5:
            continue

        htf_key = htf_slice[-1].timestamp if htf_slice else None
        if htf_cache["key"] != htf_key:
            htf_state = lang_coord.run(htf_slice, symbol="BTCUSDT", timeframe=timeframe_set.htf)
            htf_cache = {"key": htf_key, "state": htf_state}
        else:
            htf_state = htf_cache["state"]

        mtf_key = mtf_slice[-1].timestamp if mtf_slice else None
        if mtf_cache["key"] != mtf_key:
            mtf_state = lang_coord.run(mtf_slice, symbol="BTCUSDT", timeframe=timeframe_set.mtf)
            mtf_cache = {"key": mtf_key, "state": mtf_state}
        else:
            mtf_state = mtf_cache["state"]

        ltf_state = lang_coord.run(ltf_slice, symbol="BTCUSDT", timeframe=timeframe_set.ltf)

        # Evaluate HTF Context
        htf_ctx = HTFContextEngine.evaluate(htf_state)
        stats["htf_contexts_by_move"][str(htf_ctx.expected_move)] += 1

        # Track candidate count before evaluate
        prev_cand_count = len(strat_coord.candidate_tracker.active_candidates)

        plans = strat_coord.evaluate(htf_state, mtf_state, ltf_state)

        for p in plans:
            stats["plans_emitted"] += 1
            stats["plans_by_status"][p.status] += 1
            if p.rejection_reason:
                stats["rejection_reasons"][p.rejection_reason] += 1

    t_dur = time.time() - t0
    print(f"\nDiagnostic finished in {t_dur:.2f}s")
    print("=" * 60)
    print("FUNNEL DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Total LTF Bars Replayed: {stats['total_bars']:,}")
    print("\nHTF Expected Move Distribution:")
    for move, count in stats["htf_contexts_by_move"].items():
        print(f"  * {move}: {count:,}")

    print(f"\nTotal Plans Emitted: {stats['plans_emitted']}")
    print("Plans by Status:")
    for status, count in stats["plans_by_status"].items():
        print(f"  * {status}: {count}")

    print("\nRejection Reasons Breakdown:")
    for reason, count in stats["rejection_reasons"].items():
        print(f"  * {reason}: {count}")

    print(f"\nActive Candidates Remaining in Tracker: {len(strat_coord.candidate_tracker.active_candidates)}")
    for c_id, c in list(strat_coord.candidate_tracker.active_candidates.items())[:10]:
        print(f"  * Candidate {c_id[:8]} | Hyp: {c.hypothesis_id} | State: {c.state} | Dir: {c.directional_permission}")


if __name__ == "__main__":
    diagnose_funnel()
