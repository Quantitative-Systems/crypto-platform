"""Experiment and Strategy Registry Builder.

Aggregates all individual experiment artifacts from research/results/discovery/
and produces:
1. EXPERIMENT_REGISTRY.json (and root copy)
2. STRATEGY_REGISTRY.json (and root copy)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DISCOVERY_RESULTS_DIR = REPO_ROOT / "research" / "results" / "discovery"
REGISTRY_DIR = REPO_ROOT / "research" / "registry"
REGISTRY_DIR.mkdir(parents=True, exist_ok=True)


def build_registries() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    experiments: Dict[str, Any] = {}
    strategies: Dict[str, Any] = {}

    for path in sorted(DISCOVERY_RESULTS_DIR.glob("EXP_*.json")):
        try:
            with open(path, "r") as f:
                record = json.load(f)
            exp_id = record["experiment_id"]
            experiments[exp_id] = record

            # Track strategy candidate metadata
            fam_id = record.get("family_id", "UNKNOWN")
            phase_mode = record.get("phase_mode", "UNKNOWN")
            strat_key = f"{fam_id}_{phase_mode}"

            if strat_key not in strategies:
                strategies[strat_key] = {
                    "strategy_key": strat_key,
                    "family_id": fam_id,
                    "phase_mode": phase_mode,
                    "total_experiments_run": 0,
                    "completed_experiments": 0,
                    "positive_expectancy_runs": 0,
                    "positive_oos_runs": 0,
                    "all_experiment_ids": [],
                    "tested_sets": set(),
                    "tested_assets": set(),
                }

            s = strategies[strat_key]
            s["total_experiments_run"] += 1
            s["all_experiment_ids"].append(exp_id)
            s["tested_sets"].add(record.get("set_id"))
            s["tested_assets"].add(record.get("symbol"))

            if record.get("status") == "COMPLETED":
                s["completed_experiments"] += 1
                if record["overall_metrics"].get("expectancy_r", 0) > 0:
                    s["positive_expectancy_runs"] += 1
                if record["partitioned_walk_forward"]["oos"].get("expectancy_r", 0) > 0:
                    s["positive_oos_runs"] += 1

        except Exception as e:
            continue

    # Convert sets to sorted lists for JSON serialization
    for s in strategies.values():
        s["tested_sets"] = sorted(list(s["tested_sets"]))
        s["tested_assets"] = sorted(list(s["tested_assets"]))

    experiment_registry = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_experiments": len(experiments),
            "completed_count": sum(1 for e in experiments.values() if e.get("status") == "COMPLETED"),
        },
        "experiments": experiments,
    }

    strategy_registry = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_strategy_hypotheses": len(strategies),
        },
        "strategies": strategies,
    }

    # Save to research/registry/ and root
    with open(REGISTRY_DIR / "EXPERIMENT_REGISTRY.json", "w") as f:
        json.dump(experiment_registry, f, indent=2)
    with open(REPO_ROOT / "EXPERIMENT_REGISTRY.json", "w") as f:
        json.dump(experiment_registry, f, indent=2)

    with open(REGISTRY_DIR / "STRATEGY_REGISTRY.json", "w") as f:
        json.dump(strategy_registry, f, indent=2)
    with open(REPO_ROOT / "STRATEGY_REGISTRY.json", "w") as f:
        json.dump(strategy_registry, f, indent=2)

    print(f"Built EXPERIMENT_REGISTRY.json ({len(experiments)} records)")
    print(f"Built STRATEGY_REGISTRY.json ({len(strategies)} strategy keys)")
    return experiment_registry, strategy_registry


if __name__ == "__main__":
    build_registries()
