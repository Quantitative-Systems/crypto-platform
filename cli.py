"""Canonical Crypto Platform CLI.

Provides unified command-line entrypoint for platform health, testing,
data inventory, strategy discovery, and research leaderboard.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))


def cmd_health() -> int:
    """Perform health checks on platform modules, data cache, and invariants."""
    print("Checking platform health...")
    checks_passed = True

    # 1. Market model imports
    try:
        from market_model.contracts import MarketState, StructureSnapshot, KeyZone, PhaseSnapshot
        from market_model.state_generator import MarketStateGenerator
        print(" [PASS] Market Model contracts & generator")
    except Exception as e:
        print(f" [FAIL] Market Model imports: {e}")
        checks_passed = False

    # 2. Strategy family registry
    try:
        from strategy.families import FAMILY_REGISTRY
        print(f" [PASS] Strategy Family Registry ({len(FAMILY_REGISTRY)} canonical families)")
    except Exception as e:
        print(f" [FAIL] Strategy Family Registry: {e}")
        checks_passed = False

    # 3. Observation Registry
    try:
        from market_model.observations import OBSERVATION_REGISTRY
        obs_count = len(OBSERVATION_REGISTRY.list_observations())
        print(f" [PASS] Observation Registry ({obs_count} canonical observations registered)")
    except Exception as e:
        print(f" [FAIL] Observation Registry: {e}")
        checks_passed = False

    # 4. Market data cache
    cache_dir = REPO_ROOT / "market_data" / "cache"
    if cache_dir.exists():
        json_count = len(list(cache_dir.glob("*.json")))
        print(f" [PASS] Market Data Cache ({json_count} files in {cache_dir})")
    else:
        print(" [FAIL] Market Data Cache directory missing")
        checks_passed = False

    # 4. Inventory file
    inv_file = REPO_ROOT / "research" / "datasets" / "DATA_INVENTORY.json"
    if inv_file.exists():
        print(" [PASS] DATA_INVENTORY.json available (research/datasets)")
    else:
        print(" [WARN] DATA_INVENTORY.json not built")

    # 5. Leaderboard file
    lead_file = REPO_ROOT / "research" / "leaderboard" / "RESEARCH_LEADERBOARD.json"
    if lead_file.exists():
        print(" [PASS] RESEARCH_LEADERBOARD.json available (research/leaderboard)")
    else:
        print(" [WARN] RESEARCH_LEADERBOARD.json not built")

    if checks_passed:
        print("\nALL PLATFORM HEALTH CHECKS PASSED.")
        return 0
    else:
        print("\nONE OR MORE HEALTH CHECKS FAILED.")
        return 1


def cmd_status() -> int:
    """Print high-level status of data inventory, experiments, and leaderboard."""
    lead_file = REPO_ROOT / "research" / "leaderboard" / "RESEARCH_LEADERBOARD.json"
    inv_file = REPO_ROOT / "research" / "datasets" / "DATA_INVENTORY.json"

    print("==================================================")
    print("CRYPTO PLATFORM: SYSTEM STATUS")
    print("==================================================")

    if inv_file.exists():
        with open(inv_file, "r") as f:
            inv = json.load(f)
        meta = inv.get("metadata", {})
        print(f"Data Series Audited: {meta.get('total_series_audited', 0)}")
        print(f"Supported Assets: {', '.join(meta.get('supported_assets', []))}")
        print(f"Supported Sets: {', '.join(meta.get('supported_sets', []))}")
    else:
        print("Data Inventory: NOT BUILT")

    if lead_file.exists():
        with open(lead_file, "r") as f:
            lead = json.load(f)
        meta = lead.get("metadata", {})
        print(f"Evaluated Experiments: {meta.get('total_evaluated_experiments', 0)}")
        print(f"Qualified Edge Candidates: {meta.get('qualified_edge_candidates_count', 0)}")
        print(f"Rejected / Failed Hypotheses: {meta.get('rejected_failed_hypotheses_count', 0)}")
    else:
        print("Leaderboard: NOT BUILT")
    print("==================================================")
    return 0


def cmd_leaderboard(top_n: int = 10) -> int:
    """Display top qualified strategy candidates."""
    lead_file = REPO_ROOT / "research" / "leaderboard" / "RESEARCH_LEADERBOARD.json"
    if not lead_file.exists():
        print("RESEARCH_LEADERBOARD.json not found in research/leaderboard. Run discovery first.")
        return 1

    with open(lead_file, "r") as f:
        lead = json.load(f)

    candidates = lead.get("qualified_candidates_leaderboard", [])
    print(f"\nTOP {min(top_n, len(candidates))} QUALIFIED EDGE CANDIDATES (>= 4.0R TARGET FLOOR):")
    print("-" * 105)
    print(f"{'Rank':<5} {'Experiment ID':<48} {'Trades':<8} {'WinRate':<9} {'Total R':<9} {'OOS Exp':<9} {'PF':<6}")
    print("-" * 105)
    for i, c in enumerate(candidates[:top_n], 1):
        print(
            f"{i:<5} {c['experiment_id']:<48} {c['trade_count']:<8} "
            f"{c['win_rate']*100:.1f}%    {c['total_r']:+.1f}R    {c['oos_expectancy_r']:+.3f}R   {c['profit_factor']:.2f}"
        )
    print("-" * 105)
    return 0


def cmd_test() -> int:
    """Execute test suite."""
    from tests.run_tests import run_all_tests
    return run_all_tests()


def main():
    parser = argparse.ArgumentParser(description="Crypto Platform CLI")
    parser.add_argument("command", choices=["health", "status", "leaderboard", "test"], help="Command to run")
    parser.add_argument("--top", type=int, default=10, help="Number of top candidates to display for leaderboard")

    args = parser.parse_args()

    if args.command == "health":
        sys.exit(cmd_health())
    elif args.command == "status":
        sys.exit(cmd_status())
    elif args.command == "leaderboard":
        sys.exit(cmd_leaderboard(args.top))
    elif args.command == "test":
        sys.exit(cmd_test())


if __name__ == "__main__":
    main()
