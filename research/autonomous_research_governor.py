"""
QCP Autonomous Research Governor.
Prioritizes raw opportunities through dynamic multi-factor economic scoring,
filters them through OpportunityMemory (to prevent redundant compute while allowing
legitimate reopening under changed market regimes), and frames formal ResearchHypotheses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from market_intelligence.opportunity_detector import OpportunityObservation, OpportunityType
from research.opportunity_memory import OpportunityMemory


@dataclass
class ResearchHypothesis:
    """A formal mandate for the Alpha Factory to synthesize into an AlphaGenome."""
    hypothesis_id: str
    target_family: str
    symbol: str
    timeframe: str
    economic_rationale: str
    required_data: List[str]
    priority_score: float
    scoring_components: Dict[str, float] = field(default_factory=dict)


class AutonomousResearchGovernor:
    """
    Evaluates data-ready opportunities using multi-factor economic criteria:
    - Opportunity magnitude
    - Data readiness
    - Expected portfolio diversification
    - Novelty & memory status
    - Research / compute cost
    - Regime compatibility
    """

    def __init__(self, memory: OpportunityMemory):
        self.memory = memory

    def _map_opportunity_to_family(self, obs: OpportunityObservation) -> str:
        if obs.opportunity_type in (OpportunityType.TREND_MOMENTUM, OpportunityType.VOLATILITY_SQUEEZE):
            return "DIRECTIONAL"
        elif obs.opportunity_type == OpportunityType.FUNDING_ANOMALY:
            return "CARRY"
        elif obs.opportunity_type == OpportunityType.DISPERSION_DIVERGENCE:
            return "RELATIVE_VALUE"
        elif obs.opportunity_type == OpportunityType.LIQUIDITY_IMBALANCE:
            return "MICROSTRUCTURE"
        elif obs.opportunity_type == OpportunityType.CROSS_EXCHANGE_DISLOCATION:
            return "ARBITRAGE"
        elif obs.opportunity_type == OpportunityType.LIQUIDATION_CASCADE:
            return "EVENT_DRIVEN"
        elif obs.opportunity_type == OpportunityType.MARKET_MAKING_SPREAD:
            return "MARKET_MAKING"
        return "UNKNOWN"

    def _determine_timeframe(self, obs: OpportunityObservation) -> str:
        if obs.opportunity_type in (OpportunityType.LIQUIDITY_IMBALANCE, OpportunityType.MARKET_MAKING_SPREAD):
            return "1m"
        elif obs.opportunity_type == OpportunityType.CROSS_EXCHANGE_DISLOCATION:
            return "5m"
        elif obs.opportunity_type == OpportunityType.LIQUIDATION_CASCADE:
            return "15m"
        return "4h"

    def calculate_priority_score(
        self,
        obs: OpportunityObservation,
        target_family: str,
        active_portfolio_families: Optional[List[str]] = None,
        current_regime: Optional[str] = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Computes deterministic multi-factor priority score:
        Priority = (0.35 * Magnitude) + (0.25 * DataReadiness) + (0.20 * Diversification) + (0.10 * Novelty) - (0.10 * ResearchCost)
        """
        # 1. Magnitude [0.0, 1.0]
        mag = max(0.0, min(1.0, obs.magnitude_score))

        # 2. Data Readiness [0.0, 1.0]
        has_unavailable = any(
            any(kw in t for kw in ("ORDER_BOOK", "LIQUIDATION", "FUNDING", "TICK", "DEPTH", "BASIS"))
            for t in obs.required_data_tokens
        )
        if has_unavailable:
            data_readiness = 0.0
        elif all("OHLCV" in t for t in obs.required_data_tokens):
            data_readiness = 1.0
        else:
            data_readiness = 0.5

        # 3. Expected Portfolio Diversification [0.0, 1.0]
        active_set = set(active_portfolio_families or ["DIRECTIONAL"])
        if target_family not in active_set:
            diversification = 1.0  # High diversification value for underrepresented engines
        else:
            diversification = 0.3  # Lower diversification if family already present

        # 4. Novelty / Memory Factor [0.0, 1.0]
        is_falsified = (
            self.memory.is_recently_falsified(obs.opportunity_type.value, obs.symbol)
            or self.memory.is_recently_falsified(target_family, obs.symbol)
        )
        novelty = 0.4 if is_falsified else 1.0

        # 5. Research Cost [0.0, 1.0]
        cost = 0.3 if "ORDER_BOOK" in str(obs.required_data_tokens) else 0.1

        # Calculate final weighted score
        score = (
            (0.35 * mag)
            + (0.25 * data_readiness)
            + (0.20 * diversification)
            + (0.10 * novelty)
            - (0.10 * cost)
        )
        score = max(0.0, min(1.0, score))

        components = {
            "magnitude": round(mag, 3),
            "data_readiness": round(data_readiness, 3),
            "diversification": round(diversification, 3),
            "novelty": round(novelty, 3),
            "cost": round(cost, 3),
            "total_score": round(score, 3)
        }
        return score, components

    def formulate_hypotheses(
        self,
        ready_opportunities: List[OpportunityObservation],
        active_portfolio_families: Optional[List[str]] = None,
        current_regime: Optional[str] = None,
        new_features: Optional[List[str]] = None,
        has_new_features: bool = False
    ) -> List[ResearchHypothesis]:
        """
        Translates raw data-ready opportunities into prioritized research hypotheses.
        """
        hypotheses = []

        for obs in ready_opportunities:
            family = self._map_opportunity_to_family(obs)

            # 1. Filter against memory: check if suppressed or legitimately reopenable
            can_reopen, reopen_reason = self.memory.can_reopen_hypothesis(
                obs.opportunity_type.value,
                obs.symbol,
                current_regime=current_regime,
                new_features=new_features,
                has_new_features=has_new_features
            )
            if not can_reopen:
                continue

            # 2. Formulate Rationale & Multi-Factor Priority
            timeframe = self._determine_timeframe(obs)
            priority_score, components = self.calculate_priority_score(
                obs=obs,
                target_family=family,
                active_portfolio_families=active_portfolio_families,
                current_regime=current_regime
            )

            rationale = (
                f"Detected {obs.opportunity_type.value} in {obs.symbol} (Priority: {priority_score:.2f}). "
                f"Description: {obs.description}"
            )

            # 3. Create Hypothesis
            hypothesis = ResearchHypothesis(
                hypothesis_id=f"HYP-{obs.opportunity_id}",
                target_family=family,
                symbol=obs.symbol,
                timeframe=timeframe,
                economic_rationale=rationale,
                required_data=obs.required_data_tokens,
                priority_score=priority_score,
                scoring_components=components
            )
            hypotheses.append(hypothesis)

        # Sort by highest priority first
        hypotheses.sort(key=lambda h: h.priority_score, reverse=True)
        return hypotheses
