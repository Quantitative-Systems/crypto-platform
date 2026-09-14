"""
PROJECT TOP1 — Phase 11 Strategy Library & Registry.

Maintains a persistent, versioned registry of all quantitative strategy candidates.
Statuses:
- RESEARCH
- FAILED
- PROMISING
- VALIDATION
- OOS
- ROBUST
- PAPER
- QUALIFIED
- LIVE
- DEGRADED
- RETIRED
"""

import os
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional


class StrategyStatus(str, Enum):
    RESEARCH = "RESEARCH"
    FAILED = "FAILED"
    PROMISING = "PROMISING"
    VALIDATION = "VALIDATION"
    OOS = "OOS"
    ROBUST = "ROBUST"
    PAPER = "PAPER"
    QUALIFIED = "QUALIFIED"
    LIVE = "LIVE"
    DEGRADED = "DEGRADED"
    RETIRED = "RETIRED"


class StrategyRegistry:
    """
    Persistent registry for Project TOP1 Strategy Library.
    Guarantees immutability of historical benchmarks and provenance of candidate evolution.
    """

    def __init__(self, registry_file: Optional[str] = None):
        if registry_file is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            registry_file = os.path.join(base_dir, "strategy_library.json")
        self.registry_file = registry_file
        self.strategies: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r") as f:
                    self.strategies = json.load(f)
            except Exception:
                self.strategies = {}
        else:
            self.strategies = {}

    def save(self):
        with open(self.registry_file, "w") as f:
            json.dump(self.strategies, f, indent=2, default=str)

    def register_candidate(
        self,
        strategy_id: str,
        version: str,
        hypothesis: Dict[str, Any],
        rules: Dict[str, Any],
        assets: List[str],
        timeframes: List[str],
        risk_model: Dict[str, Any],
        status: StrategyStatus = StrategyStatus.RESEARCH,
        development_results: Optional[Dict[str, Any]] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Register a new candidate in the strategy library."""
        record = {
            "strategy_id": strategy_id,
            "version": version,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": status.value if isinstance(status, StrategyStatus) else str(status),
            "hypothesis": hypothesis,
            "rules": rules,
            "assets": assets,
            "timeframes": timeframes,
            "risk_model": risk_model,
            "development_results": development_results or {},
            "validation_results": {},
            "oos_results": {},
            "robustness_results": {},
            "status_history": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": status.value if isinstance(status, StrategyStatus) else str(status),
                    "reason": notes or "Initial registration",
                }
            ],
            "notes": notes,
        }
        self.strategies[strategy_id] = record
        self.save()
        return record

    def update_status(
        self,
        strategy_id: str,
        new_status: StrategyStatus,
        reason: str,
        evidence: Optional[Dict[str, Any]] = None,
    ):
        """Update candidate lifecycle status with audit reason and evidence."""
        if strategy_id not in self.strategies:
            raise KeyError(f"Strategy {strategy_id} not found in registry")

        strat = self.strategies[strategy_id]
        strat["status"] = new_status.value if isinstance(new_status, StrategyStatus) else str(new_status)
        strat["status_history"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": strat["status"],
            "reason": reason,
            "evidence": evidence or {},
        })
        self.save()

    def update_results(
        self,
        strategy_id: str,
        result_type: str,  # 'development_results', 'validation_results', 'oos_results', 'robustness_results'
        results: Dict[str, Any],
    ):
        """Attach verified stage results to the strategy record."""
        if strategy_id not in self.strategies:
            raise KeyError(f"Strategy {strategy_id} not found in registry")
        self.strategies[strategy_id][result_type] = results
        self.save()

    def get_candidate(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        return self.strategies.get(strategy_id)

    def list_by_status(self, status: StrategyStatus) -> List[Dict[str, Any]]:
        target = status.value if isinstance(status, StrategyStatus) else str(status)
        return [s for s in self.strategies.values() if s.get("status") == target]

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self.strategies.values())
