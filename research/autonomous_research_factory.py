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

        # V2: Map abstract hypotheses to tangible entry/exit heuristics dynamically
        if hypothesis.target_family == "CARRY":
            entry = "Harvest when net funding APR clears borrow + friction hurdle."
            exit_m = "Exit when net funding APR decays below the hurdle."
            features = ["annualized_funding_rate_bps", "spot_perp_basis_bps", "borrow_rate_apr"]
            failure_modes = ["REGIME_FLIP", "FUNDING_INVERSION", "BORROW_SPIKE"]
            holding_hours = 48.0
        elif hypothesis.target_family == "RELATIVE_VALUE":
            entry = "Enter on statistical divergence of z-score (> 2.0 sigma)."
            exit_m = "Exit on mean reversion to fair value (z-score < 0.5 sigma)."
            features = ["spread_zscore_4h", "cointegration_residual", "rolling_beta"]
            failure_modes = ["STRUCTURAL_BREAK", "CORRELATION_BREAKDOWN"]
            holding_hours = 24.0
        elif hypothesis.target_family == "MICROSTRUCTURE":
            entry = "Enter on order flow imbalance (OFI) skew with queue priority."
            exit_m = "Micro-horizon scalp on book replenishment or latency timeout."
            features = ["book_imbalance_top10", "trade_flow_skew", "spread_bps"]
            failure_modes = ["LATENCY_DECAY", "ADVERSE_SELECTION", "QUEUE_CANCELLATION"]
            holding_hours = 0.5
        elif hypothesis.target_family == "ARBITRAGE":
            entry = "Simultaneously execute opposing legs on cross-venue spread > 2x roundtrip fee."
            exit_m = "Convergence of cross-venue price spread."
            features = ["cross_venue_spread_bps", "venue_fill_probability", "transfer_latency_ms"]
            failure_modes = ["LEG_EXECUTION_RISK", "WITHDRAWAL_HALT", "EXCHANGE_OUTAGE"]
            holding_hours = 0.1
        elif hypothesis.target_family == "MARKET_MAKING":
            entry = "Post symmetric passive limit orders around mid-price adjusted for inventory skew."
            exit_m = "Passive execution or inventory rebalancing threshold breach."
            features = ["bid_ask_spread_bps", "order_book_depth_usd", "inventory_ratio"]
            failure_modes = ["TOXIC_FLOW", "INVENTORY_ACCUMULATION", "FLASH_CRASH"]
            holding_hours = 0.25
        elif hypothesis.target_family == "EVENT_DRIVEN":
            entry = "Fade post-liquidation cascade exhaustion with trailing stop."
            exit_m = "Mean reversion to pre-shock VWAP or fixed R target."
            features = ["liquidation_volume_usd", "cvd_exhaustion_print", "rebound_velocity"]
            failure_modes = ["CASCADE_CONTINUATION", "LIQUIDITY_VACUUM"]
            holding_hours = 4.0
        elif hypothesis.target_family == "MACHINE_LEARNING":
            entry = "Execute on non-linear ensemble probability forecast > threshold."
            exit_m = "Time-decay horizon or forecast confidence degradation."
            features = ["multi_scale_wavelet", "volatility_dispersion", "regime_entropy"]
            failure_modes = ["OVERFITTING", "CONCEPT_DRIFT", "REGIME_SHIFT"]
            holding_hours = 12.0
        else: # DIRECTIONAL
            entry = "Enter on momentum breakout confirmation above swing high."
            exit_m = "ATR-based stop with trailing take-profit."
            features = ["donchian_breakout_score", "volume_expansion_ratio", "adx_trend_strength"]
            failure_modes = ["FALSE_BREAKOUT", "WHIPSAW", "REGIME_FLIP"]
            holding_hours = 24.0

        return AlphaGenome(
            alpha_id=hypothesis.hypothesis_id,
            family=family_enum,
            version="v2.0",
            asset_universe=[hypothesis.symbol],
            venues=["BINANCE"],
            instruments=["PERPETUAL"],
            timeframe=hypothesis.timeframe,
            expected_holding_period_hours=holding_hours,
            economic_rationale=hypothesis.economic_rationale,
            features=features,
            entry_mechanism=entry,
            exit_mechanism=exit_m,
            microstructure=MicrostructureProfile(),
            # ZERO performance: metrics are attached only by the evaluation engine.
            performance=EconomicPerformance(),
            regime_dependencies={"AUTONOMOUS_DISCOVERY": hypothesis.priority_score},
            failure_modes=failure_modes,
            lifecycle_state=AlphaLifecycleState.RESEARCH,
        )

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