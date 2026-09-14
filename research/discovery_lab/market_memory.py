"""
Quantitative Systems Platform (QSP) — Market Memory, Strategy Graveyard & Alpha Genome.

Provides institutional persistent memory:
1. MarketMemoryStore: Historical record of regimes, liquidity states, and empirical strategy performance.
2. StrategyGraveyard: Immutable registry of rejected/falsified strategies with exact failure rationales.
   Prevents the autonomous lab from ever repeating known dead ends.
3. AlphaGenome: Encodes strategy DNA to measure genetic similarity and detect disguised beta.
"""

import os
import sys
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
GRAVEYARD_FILE = os.path.join(RESULTS_DIR, "STRATEGY_GRAVEYARD.json")
MARKET_MEMORY_FILE = os.path.join(RESULTS_DIR, "MARKET_MEMORY_STORE.json")


@dataclass
class AlphaGenome:
    """
    Standardized genomic descriptor of a quantitative trading strategy.
    """
    market: str                 # 'CRYPTO_SPOT' or 'CRYPTO_PERP'
    asset: str                  # 'BTC', 'ETH', 'SOL'
    timeframe_set: int          # 1, 2, 3, 4, 5, 6
    primary_factor: str         # 'TREND_BETA', 'MOMENTUM', 'MEAN_REVERSION', 'BREAKOUT', 'RELATIVE_VALUE'
    signal_generator: str       # 'SUPERTREND', 'EMA_CROSS', 'DONCHIAN', 'RSI', 'STOCHASTIC', 'SPREAD_ZSCORE'
    confirmation_filter: str    # 'HTF_TREND', 'ADX_REGIME', 'ATR_EXPANSION', 'NONE'
    entry_mechanism: str        # 'BREAKOUT_STOP', 'PULLBACK_LIMIT', 'MOMENTUM_MARKET'
    exit_mechanism: str         # 'TRAILING_ATR', 'STRUCTURAL_SWING', 'FIXED_R_TP', 'MEAN_REVERSION_Z'
    risk_sizing_model: str      # 'CERTIFIED_FRICTION_ADJUSTED', 'FIXED_FRACTIONAL'

    def compute_similarity(self, other: "AlphaGenome") -> float:
        """
        Calculates genomic similarity score (0.0 to 1.0).
        High similarity (>0.75) indicates shared factor exposure rather than true diversification.
        """
        attributes = [
            ("asset", 0.20),
            ("timeframe_set", 0.15),
            ("primary_factor", 0.25),
            ("signal_generator", 0.15),
            ("confirmation_filter", 0.10),
            ("entry_mechanism", 0.05),
            ("exit_mechanism", 0.05),
            ("risk_sizing_model", 0.05),
        ]
        match_score = 0.0
        for attr, weight in attributes:
            if getattr(self, attr) == getattr(other, attr):
                match_score += weight
        return round(match_score, 3)


@dataclass
class GraveyardRecord:
    candidate_id: str
    genome: Dict[str, Any]
    falsification_stage: str      # 'DEVELOPMENT', 'VALIDATION', 'OOS', 'FRICTION_STRESS', 'ROBUSTNESS'
    rejection_timestamp: str
    failure_mode: str             # 'OPPORTUNITY_STARVATION', 'FRICTION_COLLAPSE', 'OOS_DECAY', 'PROFIT_CONCENTRATION'
    falsification_evidence: Dict[str, Any]
    post_mortem_notes: str


class StrategyGraveyard:
    """
    Permanent institutional archive of falsified ideas.
    Guarantees research efficiency by checking new hypotheses against known dead ends.
    """

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or GRAVEYARD_FILE
        self.records: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    self.records = json.load(f)
            except Exception:
                self.records = {}
        else:
            self.records = {}
            # Seed with baseline known falsifications
            self._seed_baseline_graveyard()

    def _seed_baseline_graveyard(self):
        # Baseline Candidate 001
        self.bury_candidate(
            candidate_id="CANDIDATE-001",
            genome=asdict(AlphaGenome(
                market="CRYPTO_PERP", asset="BTC", timeframe_set=1,
                primary_factor="TREND_BETA", signal_generator="SUPERTREND",
                confirmation_filter="HTF_TREND", entry_mechanism="PULLBACK_LIMIT",
                exit_mechanism="FIXED_R_TP", risk_sizing_model="CERTIFIED_FRICTION_ADJUSTED",
            )),
            falsification_stage="DEVELOPMENT",
            failure_mode="OPPORTUNITY_STARVATION",
            falsification_evidence={"total_trades": 6, "min_required": 100},
            post_mortem_notes="Triple-barrier Stochastic pullbacks on Set 1 Macro produce insufficient trade frequency (N=6 in 2 years).",
        )
        # SOL Breakout Set 2 (Failed OOS)
        self.bury_candidate(
            candidate_id="FAM-03-BREAKOUT_SOLUSDT_Set2",
            genome=asdict(AlphaGenome(
                market="CRYPTO_PERP", asset="SOL", timeframe_set=2,
                primary_factor="BREAKOUT", signal_generator="DONCHIAN",
                confirmation_filter="ATR_EXPANSION", entry_mechanism="BREAKOUT_STOP",
                exit_mechanism="TRAILING_ATR", risk_sizing_model="CERTIFIED_FRICTION_ADJUSTED",
            )),
            falsification_stage="OOS",
            failure_mode="OOS_DECAY",
            falsification_evidence={"dev_r": 29.05, "val_r": 28.06, "oos_r": -2.61},
            post_mortem_notes="Breakout alpha collapsed in 2024-2026 Out-of-Sample regime due to chop and false breakouts.",
        )

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.records, f, indent=2)

    def bury_candidate(
        self,
        candidate_id: str,
        genome: Dict[str, Any],
        falsification_stage: str,
        failure_mode: str,
        falsification_evidence: Dict[str, Any],
        post_mortem_notes: str,
    ):
        self.records[candidate_id] = {
            "candidate_id": candidate_id,
            "genome": genome,
            "falsification_stage": falsification_stage,
            "rejection_timestamp": datetime.now(timezone.utc).isoformat(),
            "failure_mode": failure_mode,
            "falsification_evidence": falsification_evidence,
            "post_mortem_notes": post_mortem_notes,
        }
        self.save()

    def check_for_similar_failure(self, new_genome: AlphaGenome, similarity_threshold: float = 0.85) -> Optional[Dict[str, Any]]:
        """Checks if an identical or near-identical hypothesis has already failed."""
        for rec in self.records.values():
            g_dict = rec.get("genome", {})
            try:
                g = AlphaGenome(**g_dict)
                sim = new_genome.compute_similarity(g)
                if sim >= similarity_threshold:
                    return {
                        "matched_failure_id": rec["candidate_id"],
                        "similarity": sim,
                        "failure_mode": rec["failure_mode"],
                        "post_mortem": rec["post_mortem_notes"],
                    }
            except Exception:
                continue
        return None


class MarketMemoryStore:
    """
    Persistent institutional knowledge store of observed market regimes and empirical performance.
    """

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or MARKET_MEMORY_FILE
        self.memory: Dict[str, Any] = {
            "regime_observations": {},
            "strategy_edge_by_regime": {},
            "microstructure_friction_profiles": {
                "BTCUSDT": {"median_spread_bps": 1.5, "median_slippage_bps": 2.5},
                "ETHUSDT": {"median_spread_bps": 2.0, "median_slippage_bps": 3.0},
                "SOLUSDT": {"median_spread_bps": 3.0, "median_slippage_bps": 4.5},
            },
        }
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    self.memory = json.load(f)
            except Exception:
                pass

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.memory, f, indent=2)

    def record_regime_outcome(
        self,
        symbol: str,
        regime_desc: str,
        strategy_id: str,
        pnl_r: float,
    ):
        key = f"{symbol}:{regime_desc}"
        if key not in self.memory["regime_observations"]:
            self.memory["regime_observations"][key] = {"trades": 0, "total_r": 0.0, "wins": 0}
        obs = self.memory["regime_observations"][key]
        obs["trades"] += 1
        obs["total_r"] = round(obs["total_r"] + pnl_r, 2)
        if pnl_r > 0:
            obs["wins"] += 1
        self.save()
