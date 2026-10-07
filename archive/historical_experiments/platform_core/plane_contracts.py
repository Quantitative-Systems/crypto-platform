"""
Platform Core: Institutional 3-Plane Architectural System Contracts
Formalizes the strict separation between:
Plane 1: Research Plane (Lab, Data Lake, Causal Replay, Experimentation, Statistical Validation)
Plane 2: Decision Plane (Market State, Signal Engine, Risk Firewall, Portfolio Constraints, Capital Barrier)
Plane 3: Production Plane (Execution Gateway, Order State Machine, Persistence, Reconciliation, Alerting)
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional


class SystemPlane(str, Enum):
    RESEARCH = "RESEARCH_PLANE"
    DECISION = "DECISION_PLANE"
    PRODUCTION = "PRODUCTION_PLANE"


class IResearchPlane(ABC):
    """
    Contract for Plane 1: Quantitative Research Laboratory.
    Must guarantee causal zero-lookahead state isolation and empirical auditability.
    """

    @abstractmethod
    def run_experiment(self, hypothesis_id: str, stream_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def validate_statistical_significance(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        pass


class IDecisionPlane(ABC):
    """
    Contract for Plane 2: Decision, Risk & Capital Barrier.
    Evaluates real-time market state against Risk Firewalls and enforces capital deployment gates.
    """

    @abstractmethod
    def evaluate_risk_firewall(self, trade_plan: Any) -> Any:
        pass

    @abstractmethod
    def evaluate_capital_barrier(self, hypothesis_metrics: Dict[str, Any]) -> Any:
        pass


class IProductionPlane(ABC):
    """
    Contract for Plane 3: 24/7 Production Execution & Reliability.
    Maintains atomic state persistence, sub-millisecond order lifecycle, and daily reconciliation.
    """

    @abstractmethod
    def submit_order(self, allocated_plan: Any) -> Any:
        pass

    @abstractmethod
    def reconcile_positions(self) -> Any:
        pass
