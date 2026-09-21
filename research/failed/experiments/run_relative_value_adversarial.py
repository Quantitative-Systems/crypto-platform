"""
Quantitative Crypto Platform (QCP) — Relative Value Adversarial Research Runner.

Executes 7-point adversarial stress testing over Relative Value candidates:
1. Baseline
2. 2x Friction (64 bps roundtrip)
3. 1-Bar Execution Latency
4. Outlier / Windfall Removal (remove top 10% winners)
5. Parameter Perturbation (z_entry = 2.2)
6. Regime Breakdown (Dev 2020-2022, Val 2023, OOS 2024-2026)

Outputs: research/results/RELATIVE_VALUE_ADVERSARIAL_AUDIT.json
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Any
import numpy as np

from market_data.binance_fetcher import BinanceFetcher
from research.discovery_lab.relative_value_config import (
    RelativeValueConfig,
    DecomposedFrictionModel,
)
from research.discovery_lab.relative_value_engine import (
    RelativeValueEngine,
    RelativeValuePartitionResult,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RelativeValueAdversarial")


def run_adversarial_battery():
    logger.info("Initializing Relative Value Adversarial Battery...")
    base_config = RelativeValueConfig()
    engine = RelativeValueEngine(config=base_config)

    stress_friction = base_config.get_stress_friction(multiplier=2.0)

    results: Dict[str, Any] = {
        "platform": "Quantitative Crypto Platform (QCP)",
        "audit_name": "RELATIVE_VALUE_ADVERSARIAL_AUDIT",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "candidates": {},
    }

    candle_cache: Dict[str, Any] = {}

    for sym_a, sym_b, pair_name in base_config.pairs:
        for tf in base_config.timeframes:
            cand_key = f"{pair_name}_{tf}"
            logger.info(f"Running Adversarial Battery for {cand_key}...")

            key_a = f"{sym_a}_{tf}"
            key_b = f"{sym_b}_{tf}"

            if key_a not in candle_cache:
                candle_cache[key_a] = BinanceFetcher.fetch_real_candles(sym_a, tf, limit=50000)
            if key_b not in candle_cache:
                candle_cache[key_b] = BinanceFetcher.fetch_real_candles(sym_b, tf, limit=50000)

            candles_a = candle_cache[key_a]
            candles_b = candle_cache[key_b]

            ts, p_a, p_b = engine.align_candle_series(candles_a, candles_b)
            log_a = np.log(p_a)
            log_b = np.log(p_b)
            betas, alphas, spreads, z_scores = engine.compute_causal_rolling_spread(log_a, log_b)

            # 1. Baseline Run
            baseline_res = engine.simulate_pair_trading(
                pair_name, sym_a, sym_b, ts, p_a, p_b, betas, spreads, z_scores,
                start_ts=base_config.dev_start_ts, end_ts=base_config.oos_end_ts,
                friction=base_config.friction, latency_bars=0,
            )

            # 2. 2x Friction Stress (64 bps)
            stress_fric_res = engine.simulate_pair_trading(
                pair_name, sym_a, sym_b, ts, p_a, p_b, betas, spreads, z_scores,
                start_ts=base_config.dev_start_ts, end_ts=base_config.oos_end_ts,
                friction=stress_friction, latency_bars=0,
            )

            # 3. Latency Stress (1 bar execution delay)
            latency_res = engine.simulate_pair_trading(
                pair_name, sym_a, sym_b, ts, p_a, p_b, betas, spreads, z_scores,
                start_ts=base_config.dev_start_ts, end_ts=base_config.oos_end_ts,
                friction=base_config.friction, latency_bars=1,
            )

            # 4. Outlier Removal (Remove top 10% highest R trades)
            trades_r = [t.net_r for t in baseline_res.trades]
            outlier_net_r = 0.0
            outlier_expectancy = 0.0
            if trades_r:
                cutoff_idx = max(1, int(len(trades_r) * 0.90))
                sorted_r = sorted(trades_r)
                truncated_r = sorted_r[:cutoff_idx]
                outlier_net_r = sum(truncated_r)
                outlier_expectancy = outlier_net_r / len(truncated_r)

            # 5. Parameter Perturbation (z_entry = 2.2 instead of 2.0)
            perturbed_config = RelativeValueConfig(entry_z_threshold=2.2)
            perturbed_engine = RelativeValueEngine(config=perturbed_config)
            perturbed_res = perturbed_engine.simulate_pair_trading(
                pair_name, sym_a, sym_b, ts, p_a, p_b, betas, spreads, z_scores,
                start_ts=base_config.dev_start_ts, end_ts=base_config.oos_end_ts,
                friction=base_config.friction, latency_bars=0,
            )

            # 6. Regime Breakdown
            dev_res = engine.simulate_pair_trading(
                pair_name, sym_a, sym_b, ts, p_a, p_b, betas, spreads, z_scores,
                start_ts=base_config.dev_start_ts, end_ts=base_config.dev_end_ts,
            )
            val_res = engine.simulate_pair_trading(
                pair_name, sym_a, sym_b, ts, p_a, p_b, betas, spreads, z_scores,
                start_ts=base_config.val_start_ts, end_ts=base_config.val_end_ts,
            )
            oos_res = engine.simulate_pair_trading(
                pair_name, sym_a, sym_b, ts, p_a, p_b, betas, spreads, z_scores,
                start_ts=base_config.oos_start_ts, end_ts=base_config.oos_end_ts,
            )

            # Classify Failure Mode
            failure_modes = []
            if baseline_res.total_net_r <= 0.0:
                failure_modes.append("NEGATIVE_BASELINE_EDGE")
            if stress_fric_res.total_net_r < baseline_res.total_net_r * 0.5:
                failure_modes.append("HIGH_FRICTION_SENSITIVITY")
            if latency_res.total_net_r < baseline_res.total_net_r * 0.5:
                failure_modes.append("HIGH_LATENCY_SENSITIVITY")
            if outlier_net_r <= 0.0:
                failure_modes.append("WINDFALL_OUTLIER_DEPENDENT")
            if oos_res.total_net_r <= 0.0:
                failure_modes.append("REGIME_INCONSISTENT_OOS_FAILURE")

            if "NEGATIVE_BASELINE_EDGE" in failure_modes or "REGIME_INCONSISTENT_OOS_FAILURE" in failure_modes:
                final_class = "FALSIFIED"
            elif len(failure_modes) > 0:
                final_class = "FRAGILE"
            else:
                final_class = "ROBUST"

            results["candidates"][cand_key] = {
                "pair_name": pair_name,
                "timeframe": tf,
                "baseline": baseline_res.to_dict(),
                "stress_2x_friction": stress_fric_res.to_dict(),
                "latency_1_bar": latency_res.to_dict(),
                "outlier_removal": {
                    "net_r_after_10pct_cut": round(outlier_net_r, 2),
                    "expectancy_after_10pct_cut": round(outlier_expectancy, 4),
                },
                "parameter_perturbation": perturbed_res.to_dict(),
                "regime_breakdown": {
                    "dev_net_r": round(dev_res.total_net_r, 2),
                    "val_net_r": round(val_res.total_net_r, 2),
                    "oos_net_r": round(oos_res.total_net_r, 2),
                },
                "failure_modes": failure_modes,
                "final_classification": final_class,
            }

            logger.info(
                f"[{cand_key}] Adversarial Verdict: {final_class} | "
                f"Failure Modes: {failure_modes} | "
                f"Baseline Net R: {baseline_res.total_net_r:+.2f}R | "
                f"2x Friction Net R: {stress_fric_res.total_net_r:+.2f}R | "
                f"Latency Net R: {latency_res.total_net_r:+.2f}R"
            )

    out_path = os.path.abspath("research/results/RELATIVE_VALUE_ADVERSARIAL_AUDIT.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Relative Value Adversarial Audit saved to {out_path}")
    return results


if __name__ == "__main__":
    run_adversarial_battery()
