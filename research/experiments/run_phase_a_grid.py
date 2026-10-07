"""Phase A Systematic Strategy Discovery Grid Runner.

Runs the foundational Phase A baseline research grid across:
- All 5 Canonical Timeframe Sets (SET 1 to SET 5)
- 4 Supported Crypto Assets (BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT)
- 10 Canonical Strategy Families (F01 to F10)
- 2 Phase Modes (PULLBACK, CONTINUATION)

Produces immutable, machine-readable JSON artifacts in research/results/discovery/.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from research.experiments.discovery_runner import DiscoveryResearchRunner
from strategy.families import FAMILY_REGISTRY

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
SETS = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]
PHASE_MODES = ["PULLBACK", "CONTINUATION"]
FAMILIES = list(FAMILY_REGISTRY.keys())


def run_grid(
    selected_assets: List[str] = ASSETS,
    selected_sets: List[str] = SETS,
    selected_families: List[str] = FAMILIES,
    selected_modes: List[str] = PHASE_MODES,
    max_experiments: int = 500,
) -> List[Dict[str, Any]]:
    runner = DiscoveryResearchRunner()
    completed_records: List[Dict[str, Any]] = []

    total_planned = len(selected_assets) * len(selected_sets) * len(selected_families) * len(selected_modes)
    print(f"==================================================")
    print(f"LAUNCHING STRATEGY DISCOVERY GRID: PHASE A")
    print(f"Total Parameter Permutations: {total_planned}")
    print(f"Assets: {selected_assets}")
    print(f"Sets: {selected_sets}")
    print(f"Families: {len(selected_families)} families")
    print(f"==================================================")

    count = 0
    start_time = time.time()

    for sym in selected_assets:
        for s_id in selected_sets:
            for fam_id in selected_families:
                for mode in selected_modes:
                    count += 1
                    if count > max_experiments:
                        print(f"Reached batch limit of {max_experiments} experiments.")
                        return completed_records

                    exp_id = f"EXP_{sym}_{s_id}_{fam_id}_{mode}_V1"
                    print(f"[{count}/{total_planned}] Executing {exp_id}...", end=" ", flush=True)

                    t0 = time.time()
                    try:
                        record = runner.run_experiment(
                            symbol=sym,
                            set_id=s_id,
                            family_id=fam_id,
                            phase_mode=mode,
                        )
                        t1 = time.time()
                        status = record.get("status", "UNKNOWN")
                        if status == "COMPLETED":
                            m = record["overall_metrics"]
                            oos = record["partitioned_walk_forward"]["oos"]
                            print(f"DONE ({t1 - t0:.1f}s) | Trades: {m['trade_count']} | WinRate: {m['win_rate']*100:.1f}% | TotR: {m['total_r']:+.1f}R | OOS_R: {oos['total_r']:+.1f}R")
                        else:
                            print(f"SKIPPED ({status})")
                        completed_records.append(record)
                    except Exception as e:
                        print(f"FAILED: {e}")

    elapsed = time.time() - start_time
    print(f"==================================================")
    print(f"GRID EXECUTION COMPLETE: {len(completed_records)} experiments evaluated in {elapsed:.1f}s")
    print(f"==================================================")
    return completed_records


if __name__ == "__main__":
    run_grid()
