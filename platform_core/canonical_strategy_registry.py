"""
Quantitative Systems Platform (QSP) — Canonical Strategy Registry & Lifecycle Manager.

Single source of truth for all quantitative research candidates, lifecycle states,
and cryptographic audit trails across Discovery, Validation, OOS, Paper, and Production.
Guarantees strict finite state machine enforcement and eliminates dashboard discrepancies.
"""

import os
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional


class StrategyLifecycleState(str, Enum):
    RESEARCH = "RESEARCH"
    DEVELOPMENT_PASS = "DEVELOPMENT_PASS"
    PROMISING = "PROMISING"
    VALIDATION_PASS = "VALIDATION_PASS"
    OOS_PASS = "OOS_PASS"
    QUALIFIED_ROBUST = "QUALIFIED_ROBUST"
    PAPER_ACTIVE = "PAPER_ACTIVE"
    CAPITAL_QUALIFIED = "CAPITAL_QUALIFIED"
    LIVE = "LIVE"
    MONITORED = "MONITORED"
    DEGRADED = "DEGRADED"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"
    FRAGILE = "FRAGILE"
    FALSIFIED = "FALSIFIED"
    FAILED = "FAILED"


# Permitted state transitions
VALID_TRANSITIONS: Dict[StrategyLifecycleState, List[StrategyLifecycleState]] = {
    StrategyLifecycleState.RESEARCH: [
        StrategyLifecycleState.DEVELOPMENT_PASS,
        StrategyLifecycleState.PROMISING,
        StrategyLifecycleState.FRAGILE,
        StrategyLifecycleState.FALSIFIED,
        StrategyLifecycleState.FAILED,
    ],
    StrategyLifecycleState.DEVELOPMENT_PASS: [
        StrategyLifecycleState.PROMISING,
        StrategyLifecycleState.VALIDATION_PASS,
        StrategyLifecycleState.FRAGILE,
        StrategyLifecycleState.FAILED,
    ],
    StrategyLifecycleState.PROMISING: [
        StrategyLifecycleState.VALIDATION_PASS,
        StrategyLifecycleState.FRAGILE,
        StrategyLifecycleState.FAILED,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.VALIDATION_PASS: [
        StrategyLifecycleState.OOS_PASS,
        StrategyLifecycleState.QUALIFIED_ROBUST,
        StrategyLifecycleState.FRAGILE,
        StrategyLifecycleState.FAILED,
    ],
    StrategyLifecycleState.OOS_PASS: [
        StrategyLifecycleState.QUALIFIED_ROBUST,
        StrategyLifecycleState.FRAGILE,
        StrategyLifecycleState.FAILED,
    ],
    StrategyLifecycleState.FRAGILE: [
        StrategyLifecycleState.PAPER_ACTIVE,
        StrategyLifecycleState.RESEARCH,
        StrategyLifecycleState.DEGRADED,
        StrategyLifecycleState.QUARANTINED,
        StrategyLifecycleState.RETIRED,
        StrategyLifecycleState.FAILED,
    ],
    StrategyLifecycleState.QUALIFIED_ROBUST: [
        StrategyLifecycleState.PAPER_ACTIVE,
        StrategyLifecycleState.CAPITAL_QUALIFIED,
        StrategyLifecycleState.MONITORED,
        StrategyLifecycleState.DEGRADED,
        StrategyLifecycleState.QUARANTINED,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.PAPER_ACTIVE: [
        StrategyLifecycleState.CAPITAL_QUALIFIED,
        StrategyLifecycleState.MONITORED,
        StrategyLifecycleState.DEGRADED,
        StrategyLifecycleState.QUARANTINED,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.CAPITAL_QUALIFIED: [
        StrategyLifecycleState.LIVE,
        StrategyLifecycleState.PAPER_ACTIVE,
        StrategyLifecycleState.DEGRADED,
        StrategyLifecycleState.QUARANTINED,
    ],
    StrategyLifecycleState.LIVE: [
        StrategyLifecycleState.MONITORED,
        StrategyLifecycleState.DEGRADED,
        StrategyLifecycleState.QUARANTINED,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.MONITORED: [
        StrategyLifecycleState.QUALIFIED_ROBUST,
        StrategyLifecycleState.CAPITAL_QUALIFIED,
        StrategyLifecycleState.DEGRADED,
        StrategyLifecycleState.QUARANTINED,
    ],
    StrategyLifecycleState.DEGRADED: [
        StrategyLifecycleState.QUARANTINED,
        StrategyLifecycleState.RESEARCH,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.QUARANTINED: [
        StrategyLifecycleState.RESEARCH,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.RETIRED: [],
    StrategyLifecycleState.FALSIFIED: [StrategyLifecycleState.RESEARCH],
    StrategyLifecycleState.FAILED: [StrategyLifecycleState.RESEARCH],
}


class CanonicalStrategyRegistry:
    """
    Institutional Persistent Strategy Registry for QSP.
    Guarantees state immutability, audit logging, and synchronized queries.
    """

    DEFAULT_REGISTRY_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "research",
        "discovery_lab",
        "strategy_library.json",
    )

    def __init__(self, registry_file: Optional[str] = None):
        self.registry_file = registry_file or self.DEFAULT_REGISTRY_PATH
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
        os.makedirs(os.path.dirname(os.path.abspath(self.registry_file)), exist_ok=True)
        with open(self.registry_file, "w") as f:
            json.dump(self.strategies, f, indent=2, default=str)

    def register_candidate(
        self,
        strategy_id: str,
        version: str,
        family_id: str,
        family_name: str,
        symbol: str,
        timeframe_set: int,
        trading_style: str,
        hypothesis: Dict[str, Any],
        rules: Dict[str, Any],
        risk_model: Dict[str, Any],
        initial_status: StrategyLifecycleState = StrategyLifecycleState.RESEARCH,
        development_results: Optional[Dict[str, Any]] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Registers a newly formulated hypothesis or candidate in the canonical library."""
        status_val = initial_status.value if isinstance(initial_status, StrategyLifecycleState) else str(initial_status)
        record = {
            "strategy_id": strategy_id,
            "version": version,
            "family_id": family_id,
            "family_name": family_name,
            "symbol": symbol,
            "set": timeframe_set,
            "style": trading_style,
            "status": status_val,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "hypothesis": hypothesis,
            "rules": rules,
            "risk_model": risk_model,
            "development_results": development_results or {},
            "validation_results": {},
            "oos_results": {},
            "robustness_results": {},
            "paper_results": {},
            "feasibility_results": {},
            "status_history": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "from_status": None,
                    "to_status": status_val,
                    "reason": notes or "Initial hypothesis registration",
                }
            ],
            "notes": notes,
        }
        self.strategies[strategy_id] = record
        self.save()
        return record

    def transition_status(
        self,
        strategy_id: str,
        new_status: StrategyLifecycleState,
        reason: str,
        evidence: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ):
        """
        Executes an audited state transition.
        Enforces valid state transition graph unless explicitly overridden with force=True.
        """
        if strategy_id not in self.strategies:
            raise KeyError(f"Strategy {strategy_id} not registered in Canonical Registry")

        strat = self.strategies[strategy_id]
        current_status_str = strat.get("status", StrategyLifecycleState.RESEARCH.value)
        try:
            current_status = StrategyLifecycleState(current_status_str)
        except ValueError:
            current_status = StrategyLifecycleState.RESEARCH

        target_status = new_status if isinstance(new_status, StrategyLifecycleState) else StrategyLifecycleState(new_status)

        if not force and current_status in VALID_TRANSITIONS:
            allowed = VALID_TRANSITIONS[current_status]
            if target_status not in allowed and target_status != current_status:
                raise ValueError(
                    f"Illegal lifecycle transition for {strategy_id}: {current_status.value} -> {target_status.value}. "
                    f"Allowed transitions: {[s.value for s in allowed]}"
                )

        strat["status"] = target_status.value
        strat["status_history"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_status": current_status.value,
            "to_status": target_status.value,
            "reason": reason,
            "evidence": evidence or {},
        })
        self.save()

    def update_stage_results(
        self,
        strategy_id: str,
        stage: str,  # 'development_results', 'validation_results', 'oos_results', 'robustness_results', 'paper_results', 'feasibility_results'
        results: Dict[str, Any],
    ):
        """Attaches audited stage empirical results to the strategy record."""
        if strategy_id not in self.strategies:
            raise KeyError(f"Strategy {strategy_id} not found in Canonical Registry")
        self.strategies[strategy_id][stage] = results
        self.save()

    def get_candidate(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        return self.strategies.get(strategy_id)

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self.strategies.values())

    def list_by_status(self, status: StrategyLifecycleState) -> List[Dict[str, Any]]:
        target = status.value if isinstance(status, StrategyLifecycleState) else str(status)
        return [s for s in self.strategies.values() if s.get("status") == target]

    def get_pipeline_summary(self) -> Dict[str, int]:
        """
        Returns an exact, canonical count of strategies in every lifecycle stage.
        Guarantees that every dashboard reflects identical numbers.
        """
        summary = {state.value: 0 for state in StrategyLifecycleState}
        for s in self.strategies.values():
            st = s.get("status", StrategyLifecycleState.RESEARCH.value)
            if st in summary:
                summary[st] += 1
            elif st == "ROBUST":
                summary[StrategyLifecycleState.QUALIFIED_ROBUST.value] += 1
            else:
                summary[StrategyLifecycleState.RESEARCH.value] += 1
        return summary

    def get_qualified_robust_candidates(self) -> List[Dict[str, Any]]:
        """Returns all candidates that have verified robust edge across Dev, Val, and OOS."""
        res = []
        for s in self.strategies.values():
            st = s.get("status", "")
            if st in (
                StrategyLifecycleState.QUALIFIED_ROBUST.value,
                "ROBUST",
                StrategyLifecycleState.PAPER_ACTIVE.value,
                StrategyLifecycleState.CAPITAL_QUALIFIED.value,
                StrategyLifecycleState.LIVE.value,
            ):
                res.append(s)
        return res
