"""
Unit tests for Market Memory, Strategy Graveyard & Alpha Genome.
"""

import os
import pytest
from dataclasses import asdict
from research.discovery_lab.market_memory import (
    AlphaGenome,
    StrategyGraveyard,
    MarketMemoryStore,
)


def test_alpha_genome_similarity():
    g1 = AlphaGenome(
        market="CRYPTO_PERP", asset="BTC", timeframe_set=2,
        primary_factor="TREND_BETA", signal_generator="SUPERTREND",
        confirmation_filter="HTF_TREND", entry_mechanism="PULLBACK_LIMIT",
        exit_mechanism="TRAILING_ATR", risk_sizing_model="CERTIFIED_FRICTION_ADJUSTED",
    )
    # Identical genome
    g2 = AlphaGenome(
        market="CRYPTO_PERP", asset="BTC", timeframe_set=2,
        primary_factor="TREND_BETA", signal_generator="SUPERTREND",
        confirmation_filter="HTF_TREND", entry_mechanism="PULLBACK_LIMIT",
        exit_mechanism="TRAILING_ATR", risk_sizing_model="CERTIFIED_FRICTION_ADJUSTED",
    )
    assert g1.compute_similarity(g2) == 1.0

    # Different asset and factor
    g3 = AlphaGenome(
        market="CRYPTO_PERP", asset="SOL", timeframe_set=4,
        primary_factor="BREAKOUT", signal_generator="DONCHIAN",
        confirmation_filter="ATR_EXPANSION", entry_mechanism="BREAKOUT_STOP",
        exit_mechanism="FIXED_R_TP", risk_sizing_model="CERTIFIED_FRICTION_ADJUSTED",
    )
    assert g1.compute_similarity(g3) < 0.30


def test_strategy_graveyard_failure_lookup(tmp_path):
    grave_file = str(tmp_path / "test_graveyard.json")
    graveyard = StrategyGraveyard(filepath=grave_file)

    failed_genome = AlphaGenome(
        market="CRYPTO_PERP", asset="AVAX", timeframe_set=4,
        primary_factor="MOMENTUM", signal_generator="ROC_RSI",
        confirmation_filter="EMA_ALIGNMENT", entry_mechanism="MOMENTUM_EXPANSION",
        exit_mechanism="FIXED_R_TP", risk_sizing_model="CERTIFIED_FRICTION_ADJUSTED",
    )
    graveyard.bury_candidate(
        candidate_id="FAILED-HYP-1",
        genome=asdict(failed_genome),
        falsification_stage="DEVELOPMENT",
        failure_mode="OPPORTUNITY_STARVATION",
        falsification_evidence={"n": 6},
        post_mortem_notes="Macro Set 4 generates zero opportunity.",
    )

    # Now check if new hypothesis matches
    match = graveyard.check_for_similar_failure(failed_genome, similarity_threshold=0.85)
    assert match is not None
    assert match["matched_failure_id"] == "FAILED-HYP-1"
    assert match["failure_mode"] == "OPPORTUNITY_STARVATION"
