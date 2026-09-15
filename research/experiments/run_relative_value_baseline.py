"""
Quantitative Crypto Platform (QCP) — Relative Value Baseline Research Runner.

Executes baseline cross-asset statistical arbitrage evaluation over certified historical data:
- Pairs: BTC/ETH, SOL/ETH, SOL/BTC
- Timeframes: 1D, 4H
- Common Certified Window: 2020-08-15 to 2026-09-01
- Econometrics: Causal Rolling OLS, Engle-Granger, Johansen, OU Half-Life
- Decomposed 32 bps roundtrip friction model

Outputs: research/results/RELATIVE_VALUE_BASELINE_AUDIT.json
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Any

from market_data.binance_fetcher import BinanceFetcher
from research.discovery_lab.relative_value_config import RelativeValueConfig
from research.discovery_lab.relative_value_engine import (
    RelativeValueEngine,
    RelativeValueResearchReport,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RelativeValueBaseline")


def run_relative_value_baseline():
    logger.info("Initializing Relative Value Baseline Research Engine...")
    config = RelativeValueConfig()
    engine = RelativeValueEngine(config=config)

    results: Dict[str, Any] = {
        "platform": "Quantitative Crypto Platform (QCP)",
        "experiment": "RELATIVE_VALUE_BASELINE_RESEARCH",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "friction_model": {
            "taker_fee_bps_per_leg": config.friction.taker_fee_bps_per_leg,
            "slippage_bps_per_leg": config.friction.slippage_bps_per_leg,
            "total_roundtrip_friction_bps": config.friction.total_pair_roundtrip_bps,
        },
        "pairs_evaluated": {},
        "summary": {
            "total_candidates": 0,
            "qualified_candidates": 0,
            "falsified_candidates": 0,
            "fragile_candidates": 0,
        }
    }

    candle_cache: Dict[str, Any] = {}

    for sym_a, sym_b, pair_name in config.pairs:
        for tf in config.timeframes:
            cand_key = f"{pair_name}_{tf}"
            logger.info(f"Evaluating {cand_key} (Symbol A: {sym_a}, Symbol B: {sym_b})...")

            # Load candles from cache
            key_a = f"{sym_a}_{tf}"
            key_b = f"{sym_b}_{tf}"

            if key_a not in candle_cache:
                candle_cache[key_a] = BinanceFetcher.fetch_real_candles(sym_a, tf, limit=50000)
            if key_b not in candle_cache:
                candle_cache[key_b] = BinanceFetcher.fetch_real_candles(sym_b, tf, limit=50000)

            candles_a = candle_cache[key_a]
            candles_b = candle_cache[key_b]

            report: RelativeValueResearchReport = engine.evaluate_pair(
                symbol_a=sym_a,
                symbol_b=sym_b,
                pair_name=pair_name,
                candles_a=candles_a,
                candles_b=candles_b,
                timeframe=tf,
            )

            report_dict = report.to_dict()
            results["pairs_evaluated"][cand_key] = report_dict
            results["summary"]["total_candidates"] += 1

            verdict = report.research_verdict
            if verdict == "QUALIFIED_RESEARCH_CANDIDATE":
                results["summary"]["qualified_candidates"] += 1
            elif "FALSIFIED" in verdict:
                results["summary"]["falsified_candidates"] += 1
            else:
                results["summary"]["fragile_candidates"] += 1

            logger.info(
                f"[{cand_key}] Verdict: {report.research_verdict} | "
                f"Beta: {report.cointegration.hedge_ratio_beta} | "
                f"EG Cointegrated: {report.cointegration.is_engle_granger_cointegrated} | "
                f"Half-Life: {report.cointegration.half_life_bars:.1f} bars | "
                f"OOS Net R: {report.oos_sample.total_net_r:+.2f}R ({report.oos_sample.total_trades} trades)"
            )

    out_path = os.path.abspath("research/results/RELATIVE_VALUE_BASELINE_AUDIT.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Relative Value Baseline Audit saved to {out_path}")
    logger.info(
        f"Baseline Results Summary: {results['summary']['total_candidates']} total, "
        f"{results['summary']['qualified_candidates']} qualified, "
        f"{results['summary']['falsified_candidates']} falsified, "
        f"{results['summary']['fragile_candidates']} fragile"
    )
    return results


if __name__ == "__main__":
    run_relative_value_baseline()
