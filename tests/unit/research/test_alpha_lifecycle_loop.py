"""
Tests for Alpha Lifecycle Manager and Autonomous Replacement Loop.
"""

from platform_core.alpha_genome import (
    AlphaFamily,
    AlphaGenome,
    AlphaLifecycleState,
    EconomicPerformance,
)
from research.alpha_lifecycle_loop import (
    AlphaLifecycleManager,
    LifecycleTransitionEvent,
)
from research.autonomous_research_factory import AutonomousResearchFactory


def test_alpha_lifecycle_transitions(tmp_path):
    manager = AlphaLifecycleManager(storage_dir=tmp_path)
    factory = AutonomousResearchFactory()

    genome = AlphaGenome(
        alpha_id="LIFECYCLE-TEST-01",
        family=AlphaFamily.DIRECTIONAL,
        version="v1.0",
        asset_universe=["SOL/USDT"],
        venues=["BINANCE"],
        instruments=["PERPETUAL"],
        timeframe="4h",
        expected_holding_period_hours=24.0,
        economic_rationale="Lifecycle test.",
        features=["feat1"],
        entry_mechanism="e",
        exit_mechanism="x",
        lifecycle_state=AlphaLifecycleState.RESEARCH
    )

    ev = manager.transition_state(
        genome,
        AlphaLifecycleState.PAPER,
        "Passed adversarial falsification."
    )
    assert isinstance(ev, LifecycleTransitionEvent)
    assert genome.lifecycle_state == AlphaLifecycleState.PAPER
    assert ev.from_state == "RESEARCH"
    assert ev.to_state == "PAPER"

    # Degradation and replacement
    from research.autonomous_research_governor import ResearchHypothesis
    hypotheses = [
        ResearchHypothesis(
            hypothesis_id="HYP-REPLACE-01",
            target_family="DIRECTIONAL",
            symbol="SOL/USDT",
            timeframe="4h",
            priority_score=9.5,
            required_data=["OHLCV_4h_SOL"],
            economic_rationale="Replacement for degraded strategy."
        )
    ]

    replacement = manager.evaluate_degradation_and_replace(
        genome,
        is_degraded=True,
        diagnosis_reason="Edge dropped below hurdle.",
        factory=factory,
        hypotheses=hypotheses
    )
    assert genome.lifecycle_state == AlphaLifecycleState.QUARANTINED
    assert replacement is not None
    assert replacement.alpha_id != genome.alpha_id
