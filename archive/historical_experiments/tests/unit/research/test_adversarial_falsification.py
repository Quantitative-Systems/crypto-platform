"""
Tests for Adversarial Falsification Engine.
"""

from platform_core.alpha_genome import (
    AlphaFamily,
    AlphaGenome,
    AlphaLifecycleState,
    EconomicPerformance,
    MicrostructureProfile,
)
from research.adversarial_falsification_engine import (
    AdversarialFalsificationEngine,
    FalsificationReport,
)


def test_adversarial_falsification_lookahead_detection():
    engine = AdversarialFalsificationEngine()

    # Genome with lookahead leak in execution mechanism
    leaky_genome = AlphaGenome(
        alpha_id="LEAKY-ALPHA-01",
        family=AlphaFamily.DIRECTIONAL,
        version="v1.0",
        asset_universe=["BTC/USDT"],
        venues=["BINANCE"],
        instruments=["SPOT"],
        timeframe="4h",
        expected_holding_period_hours=24.0,
        economic_rationale="Lookahead breakout test.",
        features=["breakout"],
        entry_mechanism="Evaluated at bar-close, executes at same-bar open.",
        exit_mechanism="Fixed stop.",
        performance=EconomicPerformance(gross_edge_r=0.50, net_edge_r=0.35)
    )

    report = engine.audit_candidate(leaky_genome)
    assert isinstance(report, FalsificationReport)
    assert report.causal_lookahead_detected is True
    assert report.is_falsified is True
    assert report.audit_verdict == "FALSIFIED_LOOKAHEAD"


def test_adversarial_falsification_robust_candidate():
    engine = AdversarialFalsificationEngine()

    robust_genome = AlphaGenome(
        alpha_id="ROBUST-ALPHA-01",
        family=AlphaFamily.DIRECTIONAL,
        version="v1.0",
        asset_universe=["SOL/USDT"],
        venues=["BINANCE"],
        instruments=["PERPETUAL"],
        timeframe="4h",
        expected_holding_period_hours=36.0,
        economic_rationale="Causal pullback.",
        features=["trend", "keyzone"],
        entry_mechanism="Bar-close confirmed; next-bar open fill.",
        exit_mechanism="ATR trailing stop.",
        performance=EconomicPerformance(
            gross_edge_r=0.45,
            net_edge_r=0.28,
            uncertainty_se=0.07,
            win_rate=48.0,
            trade_count=200
        )
    )

    report = engine.audit_candidate(robust_genome)
    assert report.causal_lookahead_detected is False
    assert report.is_falsified is False
    assert report.audit_verdict == "QUALIFIED"
