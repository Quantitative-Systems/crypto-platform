"""
Unit tests for H_MOM_01 (Momentum Continuation without Mandatory HTF KeyZone Retest).
Verifies:
1. require_htf_keyzone=True (Canonical default): No candidate spawned when price has not interacted with an HTF KeyZone.
2. require_htf_keyzone=False (H_MOM_01): Candidate IS spawned during confirmed HTF directional bias even without an HTF KeyZone.
3. CausalReplayer passes require_htf_keyzone correctly to StrategyCoordinator.
4. Preserves downstream invariants (target anchor, directional permission, candidate state).
"""

import pytest
from market_intelligence.primitives import TrendDirection
from market_intelligence.phase_engine import MarketPhase
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from research.replayer.causal_replayer import CausalReplayer
from tests.unit.strategy_engine.test_bias_classifier import create_mock_payload


def test_canonical_default_requires_htf_keyzone():
    """Default StrategyCoordinator must reject candidate spawning when no HTF KeyZone interacts."""
    coord = StrategyCoordinator(require_htf_keyzone=True)
    htf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    mtf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    ltf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)

    plans = coord.evaluate(htf, mtf, ltf)
    assert len(plans) == 0
    assert len(coord.candidate_tracker.active_candidates) == 0


def test_h_mom_01_spawns_candidate_without_htf_keyzone():
    """When require_htf_keyzone=False (H_MOM_01), candidate setup IS spawned during confirmed trend."""
    coord = StrategyCoordinator(require_htf_keyzone=False)
    htf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    mtf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    ltf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)

    plans = coord.evaluate(htf, mtf, ltf)
    assert len(plans) == 0
    assert len(coord.candidate_tracker.active_candidates) == 1

    cand = list(coord.candidate_tracker.active_candidates.values())[0]
    assert cand.directional_permission == DirectionalPermission.PERMIT_LONG
    assert cand.htf_keyzone_id is None
    assert cand.state.value == "WAIT_MTF_ALIGNMENT"


def test_causal_replayer_wiring_h_mom_01():
    """Verify CausalReplayer passes require_htf_keyzone to StrategyCoordinator."""
    replayer = CausalReplayer(timeframe_set_id="SET_3", require_htf_keyzone=False)
    assert replayer.require_htf_keyzone is False
    assert replayer.strategy_coordinator.require_htf_keyzone is False

    replayer_default = CausalReplayer(timeframe_set_id="SET_3")
    assert replayer_default.require_htf_keyzone is True
    assert replayer_default.strategy_coordinator.require_htf_keyzone is True
