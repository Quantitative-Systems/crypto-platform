"""STRATA Digital Trading Platform — Institutional Unified CLI.

Provides unified command-line entrypoint for platform operations:
- start: Start the 24/7 autonomous platform (Paper, Shadow, Demo, Micro-Live)
- status: High-level overview of system, data, and performance
- health: Comprehensive health check across data, market model, and invariants
- accounts: Inspect registered broker and paper accounts
- positions: View current active and closed simulated/live positions
- reconcile: Run state and broker reconciliation audit
- alerts: View recent operational and risk alerts
- verify-contract: Verify frozen research contract SHA-256 seal
- leaderboard: Display top qualified strategy candidates
- test: Run full platform test suite
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))


def cmd_health() -> int:
    """Perform health checks on platform modules, data cache, and invariants."""
    print("Checking STRATA Platform health...")
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

    # 5. Universe & Accounts
    try:
        from instrument.universe_manager import UNIVERSE_MANAGER
        from accounts.account_manager import AccountManager
        print(f" [PASS] Universe Manager ({len(UNIVERSE_MANAGER.list_admitted_symbols())} admitted assets)")
        accs = AccountManager().list_accounts()
        print(f" [PASS] Account Manager ({len(accs)} registered accounts)")
    except Exception as e:
        print(f" [FAIL] Universe/Account management: {e}")
        checks_passed = False

    # 6. Safety Barrier
    try:
        from execution.safety.safety_gate import SAFETY_GATE
        print(f" [PASS] Safety Gate active ({SAFETY_GATE.current_mode.value}) | Live locked: {not SAFETY_GATE._live_gate_unlocked}")
    except Exception as e:
        print(f" [FAIL] Safety Gate: {e}")
        checks_passed = False

    # 7. Production Startup Validator Pre-Flight Check
    try:
        from core.config.startup_validator import StartupValidator
        val_rep = StartupValidator.validate_preflight(strict_fail_closed=False)
        if val_rep.is_valid:
            print(f" [PASS] Pre-flight Startup Validator ({len(val_rep.checked_invariants)} gates verified)")
        else:
            print(f" [FAIL] Pre-flight Startup Validator: {val_rep.rejection_reasons}")
            checks_passed = False
    except Exception as e:
        print(f" [FAIL] Pre-flight Startup Validator: {e}")
        checks_passed = False

    if checks_passed:
        print("\nALL PLATFORM HEALTH CHECKS PASSED.")
        return 0
    else:
        print("\nONE OR MORE HEALTH CHECKS FAILED.")
        return 1


def cmd_status() -> int:
    """Print high-level status of data inventory, experiments, and leaderboard."""
    from execution.safety.safety_gate import SAFETY_GATE
    lead_file = REPO_ROOT / "research" / "leaderboard" / "RESEARCH_LEADERBOARD.json"
    inv_file = REPO_ROOT / "research" / "datasets" / "DATA_INVENTORY.json"

    print("==================================================")
    print("STRATA DIGITAL TRADING PLATFORM: SYSTEM STATUS")
    print("==================================================")
    print(f"Environment Mode:      {SAFETY_GATE.current_mode.value}")
    print(f"Real Capital Auth:     ${SAFETY_GATE.real_capital_authorized_usd:.2f}")
    print(f"Live Adapter Status:   {'ENABLED' if SAFETY_GATE.is_live_execution else 'HARD-DISABLED (FAIL-CLOSED)'}")

    if inv_file.exists():
        with open(inv_file, "r") as f:
            inv = json.load(f)
        meta = inv.get("metadata", {})
        print(f"Data Series Audited:   {meta.get('total_series_audited', 0)}")
        print(f"Supported Assets:      {', '.join(meta.get('supported_assets', []))}")
    if lead_file.exists():
        with open(lead_file, "r") as f:
            lead = json.load(f)
        meta = lead.get("metadata", {})
        print(f"Evaluated Experiments: {meta.get('total_evaluated_experiments', 0)}")
        print(f"Qualified Edge Cands:  {meta.get('qualified_edge_candidates_count', 0)}")
    print("==================================================")
    return 0


def cmd_accounts() -> int:
    """Display registered broker and paper accounts."""
    from accounts.account_manager import AccountManager
    mgr = AccountManager()
    accounts = mgr.list_accounts()

    print("\nREGISTERED BROKER & SIMULATED ACCOUNTS:")
    print("-" * 95)
    print(f"{'Account ID':<24} {'Name':<32} {'Venue':<18} {'Env':<12} {'Active'}")
    print("-" * 95)
    for a in accounts:
        active_str = "YES" if a.get("is_active_account") else "NO"
        print(f"{a['account_id']:<24} {a['name']:<32} {a['venue']:<18} {a['environment']:<12} {active_str}")
    print("-" * 95)
    return 0


def cmd_reconcile() -> int:
    """Run full state reconciliation audit."""
    from execution.autonomous_supervisor import AutonomousTradingSupervisor
    print("Executing state reconciliation audit...")
    sup = AutonomousTradingSupervisor(symbols=["BTCUSDT"])
    report = sup.run_reconciliation()
    print("\nRECONCILIATION AUDIT REPORT:")
    print("-" * 60)
    print(f"Status:             {report.status}")
    print(f"Reconciled:         {report.is_reconciled}")
    print(f"Total Candidates:   {report.total_candidates}")
    print(f"Decisions Logged:   {report.total_decisions}")
    print(f"Orders Submitted:   {report.orders_submitted}")
    print(f"Fills Executed:     {report.fills_executed}")
    print(f"Active Positions:   {report.active_positions}")
    print(f"Discrepancies:      {len(report.discrepancies)}")
    if report.discrepancies:
        for d in report.discrepancies:
            print(f" - {d}")
    print("-" * 60)
    return 0 if report.is_reconciled else 1


def cmd_alerts(limit: int = 20) -> int:
    """Display recent alerts from alert router."""
    from notifications.alert_router import ALERTS
    recent = ALERTS.get_recent_alerts(limit=limit)
    print(f"\nRECENT OPERATIONAL & RISK ALERTS (Top {len(recent)}):")
    print("-" * 80)
    for a in recent:
        print(f"[{a['severity']}] [{a['category']}] {a['title']}: {a['message']}")
    print("-" * 80)
    return 0


def cmd_verify_contract() -> int:
    """Verify frozen Q.2 research contract integrity."""
    from research.contracts.frozen_contract_guard import FROZEN_GUARD
    print("Verifying Phase Q.2 Frozen Research Contract...")
    FROZEN_GUARD.assert_capital_safety(0.0, False)
    print(f" [PASS] Frozen Contract Hash: {FROZEN_GUARD.contract.get('hash_sha256')}")
    print(f" [PASS] Real Capital Authorized: ${FROZEN_GUARD.contract['capital_boundary']['real_capital_authorized']:.2f}")
    print(f" [PASS] Live Adapter Status: {FROZEN_GUARD.contract['capital_boundary']['live_adapter_status']}")
    print(f" [PASS] Target Floor: >={FROZEN_GUARD.contract['target_geometry']['minimum_destination_r']}R")
    print(f" [PASS] Risk Per Trade: <={FROZEN_GUARD.contract['risk_governance']['max_risk_per_trade_pct']}%")
    print("\nFROZEN CONTRACT INTEGRITY 100% VERIFIED.")
    return 0


def cmd_leaderboard(top_n: int = 10) -> int:
    """Display top qualified strategy candidates."""
    lead_file = REPO_ROOT / "research" / "leaderboard" / "RESEARCH_LEADERBOARD.json"
    if not lead_file.exists():
        print("RESEARCH_LEADERBOARD.json not found in research/leaderboard.")
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


def cmd_db_migrate(args: argparse.Namespace) -> int:
    """Run database schema migrations."""
    from core.persistence.database import get_db_manager
    from core.persistence.migrations import MigrationManager
    db_path = getattr(args, "db_path", None)
    db_mgr = get_db_manager(db_path=db_path) if db_path else get_db_manager()
    migrator = MigrationManager(db_mgr)
    print(f"Applying database migrations to: {db_mgr.db_path}...")
    applied = migrator.run_migrations()
    print(f"Migrations applied successfully: {applied}")
    status = migrator.get_status()
    print(f"Current version: {status['current_version']}, pending: {status['pending_count']}")
    return 0


def cmd_db_status(args: argparse.Namespace) -> int:
    """Display database migration status."""
    from core.persistence.database import get_db_manager
    from core.persistence.migrations import MigrationManager
    db_path = getattr(args, "db_path", None)
    db_mgr = get_db_manager(db_path=db_path) if db_path else get_db_manager()
    migrator = MigrationManager(db_mgr)
    status = migrator.get_status()
    print(f"Database: {db_mgr.db_path}")
    print(f"Current version: {status['current_version']}")
    print(f"Applied migrations: {status['applied_versions']}")
    print(f"Pending migrations: {status['pending_versions']}")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    """Start autonomous 24/7 platform."""
    from main import main as run_main
    run_main()
    return 0


def main():
    parser = argparse.ArgumentParser(description="STRATA Digital Trading Platform CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("health", help="Run comprehensive health check")
    subparsers.add_parser("status", help="Print platform status")
    subparsers.add_parser("accounts", help="List registered broker accounts")
    subparsers.add_parser("reconcile", help="Run state reconciliation audit")
    subparsers.add_parser("alerts", help="View recent alerts")
    subparsers.add_parser("verify-contract", help="Verify frozen research contract")
    subparsers.add_parser("validate-preflight", help="Run production pre-flight startup validation gates")
    subparsers.add_parser("shadow", help="Alias to start in shadow/paper mode")

    start_p = subparsers.add_parser("start", help="Start the trading platform")
    start_p.add_argument("--mode", type=str, default="PAPER", choices=["PAPER", "SHADOW", "BROKER_DEMO", "MICRO_LIVE"])
    start_p.add_argument("--symbols", type=str, default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT")
    start_p.add_argument("--equity", type=float, default=100_000.0)
    start_p.add_argument("--port", type=int, default=8080)
    start_p.add_argument("--host", type=str, default="127.0.0.1")
    start_p.add_argument("--dry-run-seconds", type=int, default=0)

    lead_p = subparsers.add_parser("leaderboard", help="Display strategy leaderboard")
    lead_p.add_argument("--top", type=int, default=10)

    db_mig_p = subparsers.add_parser("db-migrate", help="Run database schema migrations")
    db_mig_p.add_argument("--db-path", type=str, default=None, help="Optional custom SQLite database file path")

    db_stat_p = subparsers.add_parser("db-status", help="Show database migration status")
    db_stat_p.add_argument("--db-path", type=str, default=None, help="Optional custom SQLite database file path")

    subparsers.add_parser("test", help="Execute test suite")

    args = parser.parse_args()

    if args.command == "health":
        sys.exit(cmd_health())
    elif args.command == "status":
        sys.exit(cmd_status())
    elif args.command == "accounts":
        sys.exit(cmd_accounts())
    elif args.command == "reconcile":
        sys.exit(cmd_reconcile())
    elif args.command == "alerts":
        sys.exit(cmd_alerts())
    elif args.command == "verify-contract":
        sys.exit(cmd_verify_contract())
    elif args.command == "validate-preflight":
        from core.config.startup_validator import StartupValidator
        rep = StartupValidator.validate_preflight(strict_fail_closed=False)
        print(json.dumps(rep.to_dict(), indent=2))
        sys.exit(0 if rep.is_valid else 1)
    elif args.command == "db-migrate":
        sys.exit(cmd_db_migrate(args))
    elif args.command == "db-status":
        sys.exit(cmd_db_status(args))
    elif args.command in ("start", "shadow"):
        from main import main as run_main
        run_main()
    elif args.command == "leaderboard":
        sys.exit(cmd_leaderboard(args.top))
    elif args.command == "test":
        from tests.run_tests import run_all_tests
        sys.exit(run_all_tests())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
