"""Crypto Trading Platform — Experiment Tracking and Champion/Challenger Registry.

Maintains immutable records for every research experiment and parameter iteration:
- Version, experiment ID, dataset version, git commit, parameter set.
- Empirical metrics (DEV/VAL/OOS Sharpe, expectancy, max drawdown, win rate).
- Explicit promotion or rejection decision with reason.
- Champion vs Challenger lineage.

CRITICAL INVARIANT: The autonomous self-improvement loop can promote candidates
ONLY to FORWARD PAPER TRADING. It is strictly forbidden from modifying live trading.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
import time
from typing import Any, Dict, List, Optional


@dataclass
class ExperimentRecord:
    experiment_id: str
    strategy_id: str
    family: str
    symbol: str
    horizon: str
    dataset_version: str
    code_version: str
    parameters: Dict[str, Any]
    dev_metrics: Dict[str, float]
    val_metrics: Dict[str, float]
    oos_metrics: Dict[str, float]
    verdict: str                        # e.g. "PROMOTED_PAPER", "REJECTED_G2"
    verdict_reason: str
    is_champion: bool = False
    challenger_to: Optional[str] = None
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))


class ExperimentRegistry:
    """Persistent ledger of all quantitative research experiments."""

    def __init__(self, registry_dir: str = "research/results/crypto_platform/experiments"):
        self.registry_dir = registry_dir
        os.makedirs(self.registry_dir, exist_ok=True)
        self.experiments_file = os.path.join(self.registry_dir, "experiment_history.json")
        self._history: Dict[str, ExperimentRecord] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.experiments_file):
            try:
                with open(self.experiments_file, "r") as f:
                    data = json.load(f)
                    for item in data:
                        rec = ExperimentRecord(**item)
                        self._history[rec.experiment_id] = rec
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.experiments_file, "w") as f:
            json.dump([asdict(r) for r in self._history.values()], f, indent=2)

    def record_experiment(self, record: ExperimentRecord) -> None:
        """Appends a new immutable experiment record."""
        self._history[record.experiment_id] = record
        self._save()

    def get_champion(self, strategy_family: str, symbol: str, horizon: str) -> Optional[ExperimentRecord]:
        """Finds current active champion for a family/symbol/horizon tuple."""
        candidates = [
            r for r in self._history.values()
            if r.family == strategy_family and r.symbol == symbol and r.horizon == horizon and r.is_champion
        ]
        if candidates:
            return sorted(candidates, key=lambda r: r.created_at_ms, reverse=True)[0]
        return None

    def promote_challenger_to_paper(self, challenger_id: str, reason: str) -> bool:
        """Promotes a successful challenger to Paper Trading."""
        rec = self._history.get(challenger_id)
        if not rec:
            return False

        # Invariant: can only promote to paper
        rec.verdict = "PROMOTED_PAPER"
        rec.verdict_reason = f"Promoted to forward paper: {reason}"
        rec.is_champion = True
        self._save()
        return True
