"""
Quantitative Crypto Platform (QCP) — Dynamic Funding Carry Research Audit Runner.

Evaluates regime-filtered dynamic spot-perp carry on real Binance historical funding records:
- Assets: SOLUSDT, BTCUSDT, ETHUSDT
- Dynamic entry: annualized funding >= 15.0%
- Dynamic exit: annualized funding <= 5.0% or negative (inversion)
- Capital architecture: Total Deployable Capital ($10k base: 50% spot, 25% perp margin, 25% buffer)
- Friction: 32 bps roundtrip per active cycle
- Borrow: 6.0% APR on margin collateral

Outputs: research/results/DYNAMIC_FUNDING_CARRY_AUDIT.json
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, List

from research.arbitrage.executable_funding_research import ExecutableFundingResearchEngine, DeployableCapitalConfig, ExecutableCostConfig
from research.arbitrage.dynamic_funding_carry import (
    DynamicFundingCarryEngine,
    DynamicCarryConfig,
    DynamicCarryAuditReport,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DynamicFundingAudit")


def run_dynamic_funding_carry_audit() -> Dict[str, Any]:
    logger.info("=" * 70)
    logger.info("QCP — DYNAMIC FUNDING & BASIS CARRY COMPREHENSIVE AUDIT")
    logger.info("=" * 70)

    # Re-use funding fetcher from ExecutableFundingResearchEngine
    fetcher_engine = ExecutableFundingResearchEngine()
    carry_engine = DynamicFundingCarryEngine(
        config=DynamicCarryConfig(
            entry_annual_funding_pct=15.0,
            exit_annual_funding_pct=5.0,
            borrow_apr_pct=6.0,
            roundtrip_friction_bps=32.0,
            min_holding_intervals=3,
            total_deployable_capital_usd=10_000.0,
        )
    )

    symbols = ["SOLUSDT", "BTCUSDT", "ETHUSDT"]
    results = {
        "platform": "Quantitative Crypto Platform (QCP)",
        "audit_name": "DYNAMIC_FUNDING_CARRY_AUDIT",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "methodology": {
            "strategy_id": "FAM-10-FUNDINGCARRY",
            "mechanism": "Dynamic spot-perp basis carry entered only during elevated positive funding regimes",
            "entry_rule": "8h funding rate >= 15.0% APR",
            "exit_rule": "8h funding rate <= 5.0% APR or negative (inversion)",
            "capital_architecture": "Total Deployable Capital ($10k: 50% spot long, 25% perp margin 2x short, 25% buffer)",
            "friction_model": "32.0 bps round-trip per cycle",
            "borrow_model": "6.0% APR on margin collateral accrued hourly during active cycles",
            "source": "Binance Public Futures REST API (/fapi/v1/fundingRate)",
        },
        "assets": {},
        "summary": {
            "total_assets_evaluated": len(symbols),
            "qualified_robust_count": 0,
            "fragile_count": 0,
            "falsified_count": 0,
        },
    }

    for sym in symbols:
        logger.info(f"Fetching historical funding records for {sym}...")
        records = fetcher_engine.fetch_binance_funding_history(symbol=sym, limit=1000)
        logger.info(f"Retrieved {len(records)} funding intervals for {sym}.")

        report: DynamicCarryAuditReport = carry_engine.evaluate_dynamic_carry(
            symbol=sym,
            funding_records=records,
        )

        results["assets"][sym] = report.to_dict()

        if report.qualification_verdict == "QUALIFIED_ROBUST":
            results["summary"]["qualified_robust_count"] += 1
        elif report.qualification_verdict == "FALSIFIED":
            results["summary"]["falsified_count"] += 1
        else:
            results["summary"]["fragile_count"] += 1

        logger.info(
            f"[{sym}] Verdict: {report.qualification_verdict} | Active Utilization: {report.active_utilization_pct:.1f}% | "
            f"Trades: {report.trades_count} (Win Rate: {report.win_rate_pct:.1f}%) | "
            f"Net PnL: ${report.total_net_pnl_usd:,.2f} | Deployable APY: {report.deployable_capital_annualized_net_apy_pct:.2f}% | "
            f"Max DD: {report.max_drawdown_pct:.2f}%"
        )

    out_path = os.path.abspath("research/results/DYNAMIC_FUNDING_CARRY_AUDIT.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nDynamic funding carry audit saved to {out_path}")
    return results


if __name__ == "__main__":
    run_dynamic_funding_carry_audit()
