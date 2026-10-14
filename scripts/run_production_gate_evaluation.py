"""Runs all research streams through the ProductionPromotionGate.

Routes passing models to `crypto_engine/registry/champions.json` and `research/candidates/passed/`.
Routes failing models to `research/candidates/failed/`.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from crypto_engine.pipeline.promotion_gate import ProductionPromotionGate

MASTER_RESULTS = WORKSPACE_ROOT / "research" / "results" / "CASCADING_FRACTAL_RESULTS" / "master_cascading_results.json"


def main():
    if not MASTER_RESULTS.exists():
        print("Master results not found.")
        return

    with open(MASTER_RESULTS, "r", encoding="utf-8") as f:
        data = json.load(f)

    streams = data.get("streams", {})
    print("=" * 80)
    print("RUNNING AUTOMATED PRODUCTION PROMOTION GATE AUDIT")
    print(f"Total Research Streams to Evaluate: {len(streams)}")
    print("=" * 80)

    passed_count = 0
    failed_count = 0

    for stream_id, metrics in streams.items():
        sym = metrics.get("symbol", "UNKNOWN")
        tf_set = metrics.get("timeframe_set", "UNKNOWN")

        verdict = ProductionPromotionGate.evaluate_and_route(
            model_id=stream_id,
            symbol=sym,
            timeframe_set=tf_set,
            stream_metrics=metrics,
            metadata={"origin": "master_cascading_results.json"},
        )

        if verdict.status.value == "PASSED_PRODUCTION_CERTIFIED":
            passed_count += 1
            print(f"  [PASSED] {stream_id:<28} | PF: {verdict.profit_factor:.2f} | R: {verdict.net_r:+.1f}R | N: {verdict.total_trades}")
        else:
            failed_count += 1
            print(f"  [FAILED] {stream_id:<28} | PF: {verdict.profit_factor:.2f} | R: {verdict.net_r:+.1f}R | Reasons: {'; '.join(verdict.reasons)}")

    print("=" * 80)
    print(f"SUMMARY: {passed_count} Models Certified to Production | {failed_count} Quarantined to Research Failed")
    champions = ProductionPromotionGate.list_live_champions()
    print(f"Active Champions in `crypto_engine/registry/champions.json`: {len(champions)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
