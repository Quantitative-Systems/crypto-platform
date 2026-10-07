"""Autonomous Edge Discovery & Generalization Engine.

Chief Quant Research & Systems Engineering Engine for the crypto-platform:
1. Systematic Multi-Dimensional Search across:
   STRUCTURE x KEY ZONE x PHASE x HTF BIAS x MTF SETUP x LTF ENTRY
   x TRADE MANAGEMENT x REGIME x ASSET x SCALE x CONTEXT
2. Standardized Benchmark Lab Integration (Benchmarks 0 to 8).
3. Falsification Controls via Null Hypothesis Lab (Placebo, Random Direction/Timing).
4. Multi-Dimensional Edge Quality Scoring (EQS 0-100).
5. Champion / Challenger Governance & Lineage Tracking.
6. Strict No-Degradation Promotion Law:
   Upgrades accepted ONLY if they improve OOS expectancy, transferability,
   cost resilience, or statistical edge quality without unacceptable degradation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
from execution.backtest.engine import CausalBacktestEngine, TradeRecord
from research.discovery.benchmark_lab import BenchmarkLab, BenchmarkResult
from research.discovery.edge_quality_scorer import EdgeQualityScore, EdgeQualityScorer
from research.discovery.null_hypothesis_lab import NullHypothesisLab, NullTestResult

RESULTS_DIR = WORKSPACE_ROOT / "research" / "results" / "discovery_engine"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ChampionRecord:
    candidate_id: str
    symbol: str
    timeframe_set: str
    phase_mode: str
    expectancy_r: float
    total_r: float
    profit_factor: float
    win_rate: float
    eqs_score: float
    classification: str
    promoted_at_utc: str
    lineage_version: int
    evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "timeframe_set": self.timeframe_set,
            "phase_mode": self.phase_mode,
            "expectancy_r": round(self.expectancy_r, 4),
            "total_r": round(self.total_r, 2),
            "profit_factor": round(self.profit_factor, 3),
            "win_rate": round(self.win_rate, 4),
            "eqs_score": round(self.eqs_score, 1),
            "classification": self.classification,
            "promoted_at_utc": self.promoted_at_utc,
            "lineage_version": self.lineage_version,
            "evidence": self.evidence,
        }


class EdgeDiscoveryEngine:
    """Autonomous Research & Generalization Engine."""

    def __init__(
        self,
        taker_fee_bps: float = 5.0,
        slippage_bps: float = 2.0,
        min_target_r: float = 4.0,
    ):
        self.taker_fee_bps = taker_fee_bps
        self.slippage_bps = slippage_bps
        self.min_target_r = min_target_r

        self.benchmark_lab = BenchmarkLab(taker_fee_bps=taker_fee_bps, slippage_bps=slippage_bps)
        self.null_lab = NullHypothesisLab(
            taker_fee_bps=taker_fee_bps, slippage_bps=slippage_bps, min_target_r=min_target_r
        )
        self.scorer = EdgeQualityScorer()

        self.registry_file = RESULTS_DIR / "CHAMPION_CHALLENGER_REGISTRY.json"
        self.champions: Dict[str, ChampionRecord] = self._load_champions()

    def _load_champions(self) -> Dict[str, ChampionRecord]:
        if not self.registry_file.exists():
            return {}
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {
                k: ChampionRecord(
                    candidate_id=v["candidate_id"],
                    symbol=v["symbol"],
                    timeframe_set=v["timeframe_set"],
                    phase_mode=v["phase_mode"],
                    expectancy_r=v["expectancy_r"],
                    total_r=v["total_r"],
                    profit_factor=v["profit_factor"],
                    win_rate=v["win_rate"],
                    eqs_score=v["eqs_score"],
                    classification=v["classification"],
                    promoted_at_utc=v["promoted_at_utc"],
                    lineage_version=v.get("lineage_version", 1),
                    evidence=v.get("evidence", {}),
                )
                for k, v in raw.items()
            }
        except Exception:
            return {}

    def _save_champions(self) -> None:
        serialized = {k: v.to_dict() for k, v in self.champions.items()}
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2)

    def evaluate_and_govern_challenger(
        self,
        challenger_id: str,
        symbol: str,
        timeframe_set: str,
        phase_mode: str,
        metrics_full: Dict[str, Any],
        metrics_dev: Dict[str, Any],
        metrics_val: Dict[str, Any],
        metrics_oos: Dict[str, Any],
        ltf_data: Dict[str, np.ndarray],
        real_candidates: List[Dict[str, Any]],
        real_trades: List[TradeRecord],
        asset_transfer_results: Optional[Dict[str, float]] = None,
        scale_transfer_results: Optional[Dict[str, float]] = None,
        cost_stress_2x: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluates challenger through Benchmark, Null Test, and No-Degradation Governance."""
        # 1. Null Hypothesis Placebo Test
        null_res = self.null_lab.test_random_direction(
            symbol=symbol,
            timeframe_set=timeframe_set,
            hypothesis=phase_mode,
            ltf_data=ltf_data,
            real_candidates=real_candidates,
            real_trades=real_trades,
            n_permutations=30,
        )

        # 2. Benchmark Comparisons
        bm4 = self.benchmark_lab.run_benchmark_4_trend_breakout(symbol, timeframe_set, ltf_data)
        bm6 = self.benchmark_lab.run_benchmark_6_mean_reversion(symbol, timeframe_set, ltf_data)

        # 3. Edge Quality Score
        eqs = self.scorer.score_candidate(
            candidate_id=challenger_id,
            metrics_full=metrics_full,
            metrics_dev=metrics_dev,
            metrics_val=metrics_val,
            metrics_oos=metrics_oos,
            asset_transfer_results=asset_transfer_results,
            scale_transfer_results=scale_transfer_results,
            cost_stress_2x=cost_stress_2x,
            null_test_p_value=null_res.empirical_p_value,
        )

        slot_key = f"{symbol}_{timeframe_set}_{phase_mode}"
        current_champ = self.champions.get(slot_key)

        # 4. Strict No-Degradation Evaluation
        promotion_verdict = "REJECTED_NO_EDGE"
        promotion_reason = "Did not meet institutional quality threshold"

        if eqs.classification in ("STRONG_EDGE", "PROMISING") and not null_res.is_falsified:
            if current_champ is None:
                promotion_verdict = "PROMOTED_INITIAL_CHAMPION"
                promotion_reason = f"First qualified champion for slot {slot_key} (EQS: {eqs.total_score:.1f})"
                new_champ = ChampionRecord(
                    candidate_id=challenger_id,
                    symbol=symbol,
                    timeframe_set=timeframe_set,
                    phase_mode=phase_mode,
                    expectancy_r=metrics_full.get("expectancy_r", 0.0),
                    total_r=metrics_full.get("total_r", 0.0),
                    profit_factor=metrics_full.get("profit_factor", 0.0),
                    win_rate=metrics_full.get("win_rate", 0.0),
                    eqs_score=eqs.total_score,
                    classification=eqs.classification,
                    promoted_at_utc=datetime.now(timezone.utc).isoformat(),
                    lineage_version=1,
                    evidence={"eqs": eqs.to_dict(), "null_test": null_res.to_dict()},
                )
                self.champions[slot_key] = new_champ
                self._save_champions()
            else:
                # Compare against champion under No-Degradation Rule
                # Upgrade accepted ONLY if improves OOS expectancy or EQS without degrading risk
                champ_oos_exp = current_champ.evidence.get("eqs", {}).get("details", {}).get("exp_oos", 0.0)
                challenger_oos_exp = metrics_oos.get("expectancy_r", 0.0)

                if challenger_oos_exp > champ_oos_exp and eqs.total_score >= current_champ.eqs_score:
                    promotion_verdict = "PROMOTED_NEW_CHAMPION"
                    promotion_reason = f"Outperformed previous champion in OOS ({challenger_oos_exp:.3f}R vs {champ_oos_exp:.3f}R) and EQS ({eqs.total_score:.1f} vs {current_champ.eqs_score:.1f})"
                    new_champ = ChampionRecord(
                        candidate_id=challenger_id,
                        symbol=symbol,
                        timeframe_set=timeframe_set,
                        phase_mode=phase_mode,
                        expectancy_r=metrics_full.get("expectancy_r", 0.0),
                        total_r=metrics_full.get("total_r", 0.0),
                        profit_factor=metrics_full.get("profit_factor", 0.0),
                        win_rate=metrics_full.get("win_rate", 0.0),
                        eqs_score=eqs.total_score,
                        classification=eqs.classification,
                        promoted_at_utc=datetime.now(timezone.utc).isoformat(),
                        lineage_version=current_champ.lineage_version + 1,
                        evidence={"eqs": eqs.to_dict(), "null_test": null_res.to_dict()},
                    )
                    self.champions[slot_key] = new_champ
                    self._save_champions()
                else:
                    promotion_verdict = "REJECTED_CHAMPION_SUPERIOR"
                    promotion_reason = f"Existing champion remains superior (Champ OOS: {champ_oos_exp:.3f}R, Challenger: {challenger_oos_exp:.3f}R)"
        elif null_res.is_falsified:
            promotion_verdict = "REJECTED_FALSIFIED"
            promotion_reason = f"Falsified by null hypothesis test (p={null_res.empirical_p_value:.4f})"
        else:
            promotion_verdict = "REJECTED_SUBPAR_SCORE"
            promotion_reason = f"EQS {eqs.total_score:.1f} below qualifying threshold (Classification: {eqs.classification})"

        return {
            "challenger_id": challenger_id,
            "slot_key": slot_key,
            "promotion_verdict": promotion_verdict,
            "promotion_reason": promotion_reason,
            "eqs": eqs.to_dict(),
            "null_test": null_res.to_dict(),
            "benchmarks": {
                "BM_4_trend_following": bm4.to_dict(),
                "BM_6_mean_reversion": bm6.to_dict(),
            },
        }
