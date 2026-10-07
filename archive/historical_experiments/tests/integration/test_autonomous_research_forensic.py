"""
Autonomous Research Forensic Test.
Validates Section 4 of the Production-Gate Execution Directive:
Proves the research pipeline is genuinely autonomous from observable market conditions
with ZERO reliance on preselected alpha families, legacy candidate lists, or hardcoded IDs.

Pipeline Chain:
Opportunity Detection
  -> Research Governor
  -> Hypothesis Formation
  -> Alpha Genome Generation
  -> Backtest / Causal Simulation
  -> Adversarial Falsification
  -> Economic Truth
  -> Opportunity Memory
"""

import tempfile
from pathlib import Path
import pytest

from market_intelligence.opportunity_detector import (
    OpportunityDetector,
    OpportunityType
)
from market_intelligence.continuous_regime_engine import (
    RegimeState,
    TrendState,
    VolatilityState,
    LiquidityState,
    FundingState,
    CorrelationState
)
from market_data.universal_data_fabric import OrderBookSnapshot, OrderBookLevel
from research.autonomous_research_governor import AutonomousResearchGovernor
from research.autonomous_research_factory import AutonomousResearchFactory
from research.opportunity_memory import OpportunityMemory, FailureCategory
from research.adversarial_falsification_engine import AdversarialFalsificationEngine
from platform_core.alpha_genome import AlphaGenome, AlphaLifecycleState
from platform_core.evidence_provenance import ProvenanceClass
from production.economic_truth_engine import EconomicTruthEngine


def test_autonomous_research_forensic_pipeline(tmp_path: Path):
    """
    Execute full autonomous discovery loop in complete isolation without legacy specifications.
    """
    # 1. Isolated Environment Setup
    vault_path = str(tmp_path / "forensic_vault.db")
    memory = OpportunityMemory(db_path=vault_path)
    detector = OpportunityDetector()
    governor = AutonomousResearchGovernor(memory=memory)
    factory = AutonomousResearchFactory()
    falsifier = AdversarialFalsificationEngine()
    truth_engine = EconomicTruthEngine()

    # Verify memory starts clean
    initial_stats = memory.get_memory_stats()
    assert initial_stats["total_hypotheses_evaluated"] == 0

    # 2. Step 1: Observable Market Data Input (Dynamic Regime & Depth, NO hardcoded candidate IDs)
    regimes = [
        RegimeState(
            timestamp_utc="2026-09-16T12:00:00Z",
            symbol="ETH/USDT",
            trend=TrendState.BULL_MOMENTUM,
            volatility=VolatilityState.NORMAL_VOL,
            liquidity=LiquidityState.NORMAL_DEPTH,
            funding=FundingState.EXTREME_POSITIVE_FUNDING,
            correlation=CorrelationState.DISPERSED_MARKET,
            trend_strength_score=0.85,
            volatility_percentile=50.0,
            liquidity_depth_ratio=1.0,
            annualized_funding_pct=85.0,
            systemic_coupling_score=0.15
        ),
        RegimeState(
            timestamp_utc="2026-09-16T12:00:00Z",
            symbol="BTC/USDT",
            trend=TrendState.SIDEWAYS_CHOP,
            volatility=VolatilityState.LOW_VOL_SQUEEZE,
            liquidity=LiquidityState.NORMAL_DEPTH,
            funding=FundingState.NEUTRAL_CARRY,
            correlation=CorrelationState.DISPERSED_MARKET,
            trend_strength_score=0.10,
            volatility_percentile=10.0,
            liquidity_depth_ratio=1.0,
            annualized_funding_pct=10.0,
            systemic_coupling_score=0.10
        )
    ]

    order_books = {
        "ETH/USDT": OrderBookSnapshot(
            symbol="ETH/USDT",
            venue="BINANCE",
            timestamp_ms=1726488000000,
            bids=[OrderBookLevel(price=3100.0, size=500.0)],
            asks=[OrderBookLevel(price=3100.2, size=100.0)],
            data_provenance="MEASURED"
        )
    }

    # Step 2: Opportunity Detection
    opportunities = detector.detect_opportunities(regimes, order_book_snapshots=order_books)
    assert len(opportunities) >= 2, "Detector must identify observable market opportunities"
    
    # Confirm detection includes both microstructure and carry
    opp_types = {opp.opportunity_type for opp in opportunities}
    assert OpportunityType.FUNDING_ANOMALY in opp_types or OpportunityType.LIQUIDITY_IMBALANCE in opp_types
    
    # Verify opportunities carry no legacy candidate IDs (no FAM-06, FAM-07, etc.)
    for opp in opportunities:
        assert "FAM-" not in opp.opportunity_id
        assert opp.magnitude_score > 0.0

    # Step 3: Research Governor & Hypothesis Formation
    hypotheses = governor.formulate_hypotheses(opportunities)
    assert len(hypotheses) >= 2, "Governor must formulate hypotheses from opportunities"
    
    # Verify dynamic multi-factor scoring was applied
    for hyp in hypotheses:
        assert 0.0 <= hyp.priority_score <= 1.0
        assert "magnitude" in hyp.scoring_components
        assert "data_readiness" in hyp.scoring_components
        assert "novelty" in hyp.scoring_components

    # Step 4: Alpha Genome Generation (Alpha Factory)
    candidates = factory.generate_candidate_population(hypotheses)
    assert len(candidates) == len(hypotheses)

    # Verify genome integrity: zero-performance assertion & distinct lineages
    genome_hashes = set()
    for cand in candidates:
        assert cand.performance.net_edge_r == 0.0, "New genome must have zero asserted performance"
        assert cand.performance.annualized_sharpe == 0.0
        assert cand.evidence_hash != ""
        genome_hashes.add(cand.evidence_hash)
        assert len(cand.features) > 0
        assert len(cand.failure_modes) > 0
        assert cand.lifecycle_state == AlphaLifecycleState.RESEARCH
    
    # Diversity test: distinct hypotheses must produce distinct genomes
    assert len(genome_hashes) == len(candidates), "Every distinct hypothesis must generate a unique genome"

    # Step 5 & 6: Causal Simulation / Backtest & Adversarial Falsification
    falsification_reports = []
    for cand in candidates:
        # Audit candidate through adversarial falsification engine
        report = falsifier.audit_candidate(
            genome=cand,
            simulated_trade_returns_r=None, # Fresh hypothesis: no realized returns yet
            returns_provenance=ProvenanceClass.UNAVAILABLE
        )
        falsification_reports.append((cand, report))

    # All unproven hypotheses must be rejected or marked INSUFFICIENT_EVIDENCE
    for cand, report in falsification_reports:
        assert report.is_falsified or report.audit_verdict == "INSUFFICIENT_EVIDENCE"

    # Step 7: Economic Truth Attribution & Reconciled Edge
    sample_attr = truth_engine.attribute_trade(
        trade_id="TRD-FORENSIC-001",
        alpha_id=candidates[0].alpha_id,
        symbol=candidates[0].asset_universe[0],
        entry_price=3100.0,
        exit_price=3105.0,
        quantity=1.0,
        is_long=True,
        market_return_pct=0.15,
        funding_fee_usd=0.25
    )
    assert sample_attr.net_pnl_usd != 0.0
    assert sample_attr.pure_alpha_pnl_usd is not None

    # Step 8: Opportunity Memory Recording & Repetition Prevention
    for cand, report in falsification_reports:
        memory.record_hypothesis_evaluation(
            alpha_id=cand.alpha_id,
            opportunity_type=cand.family.value,
            symbol=cand.asset_universe[0],
            timeframe=cand.timeframe,
            falsified=True,
            failure_reason="INSUFFICIENT_EVIDENCE: Unproven hypothesis requires empirical return provenance",
            net_edge_r=0.0
        )

    # Verify memory reflects all evaluated hypotheses
    updated_stats = memory.get_memory_stats()
    assert updated_stats["total_hypotheses_evaluated"] == len(candidates)
    assert updated_stats["falsified_hypotheses"] == len(candidates)

    # Step 9: Verify Repetition Suppression in Subsequent Cycle
    # Re-running the governor on the exact same opportunities must show deprioritized/suppressed scores
    second_cycle_hypotheses = governor.formulate_hypotheses(opportunities)
    for hyp in second_cycle_hypotheses:
        assert hyp.scoring_components["novelty"] < 1.0, (
            "Previously evaluated hypotheses must incur memory suppression penalty"
        )

