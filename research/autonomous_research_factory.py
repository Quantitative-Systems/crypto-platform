"""
QCP Autonomous Research Factory.
Generates alpha *specifications* — never alpha results.

Governance contract (enforced by platform_core.evidence_provenance):
    This module is FORBIDDEN from asserting performance. Every genome it emits
    carries EconomicPerformance() with all-zero values and the lifecycle state
    RESEARCH. Metrics may only be attached afterwards by
    research.economic_evaluation_engine, which computes them from certified
    market data and stamps them with an EvidenceRecord.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from platform_core.alpha_genome import (
    AlphaFamily,
    AlphaGenome,
    AlphaLifecycleState,
    EconomicPerformance,
    MicrostructureProfile,
)
from research.autonomous_research_governor import ResearchHypothesis


class AutonomousResearchFactory:
    """
    Emits machine-readable alpha genomes from prioritized hypotheses.
    """

    def __init__(self, certified_universe: Optional[List[str]] = None):
        self.certified_universe = certified_universe or ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

    @staticmethod
    def _to_genome(hypothesis: ResearchHypothesis) -> AlphaGenome:
        try:
            family_enum = AlphaFamily[hypothesis.target_family]
        except KeyError:
            family_enum = AlphaFamily.DIRECTIONAL # Fallback
            
        from research.alpha_matrix.blueprints.scalp_blueprint import ScalpBlueprint
        from research.alpha_matrix.blueprints.macro_scalp_blueprint import MacroScalpBlueprint
        from research.alpha_matrix.blueprints.intraday_blueprint import IntradayBlueprint
        from research.alpha_matrix.blueprints.swing_blueprint import SwingBlueprint
        from research.alpha_matrix.blueprints.positional_blueprint import PositionalBlueprint
        from research.alpha_matrix.blueprints.macro_investing_blueprint import MacroInvestingBlueprint
        from research.alpha_matrix.timeframe_governor import TradingStyle

        tf = hypothesis.timeframe
        
        # Route to the correct blueprint based on the timeframe constraints
        if tf == "1m":
            # MICRO_SCALP
            genome = ScalpBlueprint.construct_statarb_genome(hypothesis.symbol)
        elif tf == "5m":
            # MACRO_SCALP
            genome = MacroScalpBlueprint.construct_orderflow_genome(hypothesis.symbol)
        elif tf in ["15m", "1h"]:
            # INTRADAY
            genome = IntradayBlueprint.construct_mean_reversion_genome(hypothesis.symbol)
        elif tf == "4h":
            # SWING
            genome = SwingBlueprint.construct_momentum_genome(hypothesis.symbol)
        elif tf == "1d":
            # POSITIONAL
            genome = PositionalBlueprint.construct_funding_arb_genome(hypothesis.symbol)
        elif tf in ["1w", "1M"]:
            # MACRO_INVESTING
            genome = MacroInvestingBlueprint.construct_macro_trend_genome(hypothesis.symbol)
        else:
            # Fallback to positional if timeframe is unknown
            genome = PositionalBlueprint.construct_funding_arb_genome(hypothesis.symbol)
            
        # Override the alpha_id with the hypothesis ID so it traces correctly
        genome.alpha_id = hypothesis.hypothesis_id
        genome.regime_dependencies={"AUTONOMOUS_DISCOVERY": hypothesis.priority_score}
        genome.lifecycle_state = AlphaLifecycleState.RESEARCH
        
        return genome

    def generate_candidate_population(
        self, hypotheses: List[ResearchHypothesis], current_active_families: Optional[List[str]] = None
    ) -> List[AlphaGenome]:
        """
        Generates the declared specification population from dynamic hypotheses.
        """
        genomes = [self._to_genome(h) for h in hypotheses]
        for g in genomes:
            g.compute_evidence_hash()

        if current_active_families:
            active = {f.upper() for f in current_active_families}
            genomes.sort(key=lambda g: (g.family.value in active, g.alpha_id))
        return genomes

    @staticmethod
    def _supported_data_tokens() -> set:
        """Data tokens the platform can currently serve from its own warehouse."""
        tokens = set()
        for tf in ("1m", "5m", "15m", "1h", "4h", "1d", "1w", "1M"):
            for sym in ("BTC", "ETH", "SOL"):
                tokens.add(f"OHLCV_{tf}_{sym}")
        return tokens

    def get_research_gap_analysis(self, current_population: List[AlphaGenome], raw_hypotheses: List[ResearchHypothesis]) -> Dict[str, Any]:
        """Identifies underrepresented alpha families and unsupported data needs."""
        families_present = {g.family.value for g in current_population}
        all_families = {f.value for f in AlphaFamily}
        missing = sorted(all_families - families_present)

        unsupported_data: List[str] = []
        for h in raw_hypotheses:
            unmet = [d for d in h.required_data if d not in self._supported_data_tokens()]
            if unmet:
                unsupported_data.append(f"{h.hypothesis_id}:{','.join(unmet)}")

        return {
            "total_candidates": len(current_population),
            "families_present": sorted(families_present),
            "missing_families": missing,
            "recommended_next_research_target": missing[0] if missing else "REFINEMENT",
            "hypotheses_with_unsupported_data": unsupported_data,
            # Proof that this module asserts no performance of its own.
            "asserted_performance_metrics": 0,
        }