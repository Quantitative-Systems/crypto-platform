"""
Quantitative Crypto Platform (QCP) — Executable Reality Funding Arbitrage Audit Runner.

Fetches real historical 8-hour funding rates from Binance public futures REST API
for SOLUSDT, BTCUSDT, ETHUSDT and computes the institutional Deployable Capital
Audit comparing Theoretical Position APY vs Real Deployable Capital Net APY.
Outputs results to research/results/EXECUTABLE_FUNDING_ARBITRAGE_AUDIT.json.
"""

import os
import json
import logging
from research.arbitrage.executable_funding_research import (
    ExecutableFundingResearchEngine,
    DeployableCapitalConfig,
    ExecutableCostConfig,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ExecutableFundingAudit")


def run_audit():
    logger.info("Initializing Executable Funding Arbitrage Research Engine...")
    engine = ExecutableFundingResearchEngine(
        capital_config=DeployableCapitalConfig(
            total_deployable_capital_usd=10000.0,
            spot_allocation_pct=50.0,
            perp_margin_pct=25.0,
            liquidation_buffer_pct=25.0,
            perp_leverage=2.0,
        ),
        cost_config=ExecutableCostConfig(
            spot_taker_fee_bps=5.0,
            perp_taker_fee_bps=5.0,
            spot_slippage_bps=3.0,
            perp_slippage_bps=3.0,
            borrow_apr_pct=6.0,
        ),
    )

    symbols = ["SOLUSDT", "BTCUSDT", "ETHUSDT"]
    results = {
        "platform": "Quantitative Crypto Platform (QCP)",
        "audit_name": "EXECUTABLE_FUNDING_ARBITRAGE_DEPLOYABLE_CAPITAL_AUDIT",
        "pipeline_stage": "RESEARCH_ONLY_STRICTLY_LOCKED",
        "methodology": {
            "deployable_capital_denominator": "Total cash ($10k) = 50% spot long + 25% perp margin (2x short) + 25% unencumbered buffer",
            "friction_model": "32 bps round-trip (10 bps spot taker, 10 bps perp taker, 12 bps bid-ask crossing/slippage)",
            "borrow_model": "6.0% annual financing rate on margin collateral",
            "source": "Binance Public Futures REST API (/fapi/v1/fundingRate)",
        },
        "assets": {},
    }

    for symbol in symbols:
        logger.info(f"Fetching real historical funding records for {symbol}...")
        records = engine.fetch_binance_funding_history(symbol=symbol, limit=1000)
        logger.info(f"Retrieved {len(records)} funding intervals for {symbol}.")
        
        report = engine.audit_executable_arbitrage(symbol=symbol, funding_records=records)
        results["assets"][symbol] = report.to_dict()
        
        logger.info(
            f"[{symbol}] Theoretical APY: {report.theoretical_position_net_apy_pct:.2f}% | "
            f"Deployable Capital Net APY: {report.deployable_capital_net_apy_pct:.2f}% | "
            f"Verdict: {report.research_qualification_verdict}"
        )

    out_path = os.path.abspath("research/results/EXECUTABLE_FUNDING_ARBITRAGE_AUDIT.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Executable funding arbitrage audit written to {out_path}")
    return results


if __name__ == "__main__":
    run_audit()
