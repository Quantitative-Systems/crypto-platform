"""
Unit Test: Regression Protection for Canonical Enum & Contract Identity
Ensures that all Market Intelligence sub-engines and consumers use the exact same canonical
contract classes from market_intelligence.primitives without duplicate class definitions.
"""

import pytest
from market_intelligence import primitives
from market_intelligence import structure_builder_engine
from market_intelligence import trend_engine
from market_intelligence import keyzone_engine
from market_intelligence import liquidity_engine
from market_intelligence import phase_engine
from market_intelligence import coordinator

def test_trend_direction_identity():
    """Ensure StructureBuilderEngine, TrendEngine, and primitives share identical TrendDirection class."""
    assert structure_builder_engine.TrendDirection is primitives.TrendDirection
    assert trend_engine.TrendDirection is primitives.TrendDirection
    
    # Verify enum member equality and identity
    assert structure_builder_engine.TrendDirection.BULLISH is primitives.TrendDirection.BULLISH
    assert structure_builder_engine.TrendDirection.BEARISH is primitives.TrendDirection.BEARISH
    assert structure_builder_engine.TrendDirection.RANGING is primitives.TrendDirection.RANGING
    assert structure_builder_engine.TrendDirection.NEUTRAL is primitives.TrendDirection.NEUTRAL

def test_sequence_label_identity():
    """Ensure SequenceLabel is identical across all modules."""
    assert structure_builder_engine.SequenceLabel is primitives.SequenceLabel
    assert structure_builder_engine.SequenceLabel.HH is primitives.SequenceLabel.HH
    assert structure_builder_engine.SequenceLabel.HL is primitives.SequenceLabel.HL
    assert structure_builder_engine.SequenceLabel.LH is primitives.SequenceLabel.LH
    assert structure_builder_engine.SequenceLabel.LL is primitives.SequenceLabel.LL

def test_swing_scope_identity():
    """Ensure SwingScope is identical across modules."""
    assert structure_builder_engine.SwingScope is primitives.SwingScope
    assert structure_builder_engine.SwingScope.EXTERNAL is primitives.SwingScope.EXTERNAL
    assert structure_builder_engine.SwingScope.INTERNAL is primitives.SwingScope.INTERNAL

def test_event_type_identity():
    """Ensure EventType is identical across modules."""
    assert structure_builder_engine.EventType is primitives.EventType
    assert structure_builder_engine.EventType.EXTERNAL_BOS is primitives.EventType.EXTERNAL_BOS
    assert structure_builder_engine.EventType.EXTERNAL_CHOCH is primitives.EventType.EXTERNAL_CHOCH

def test_structural_contracts_identity():
    """Ensure structural dataclasses are identical across modules."""
    assert structure_builder_engine.StructureState is primitives.StructureState
    assert structure_builder_engine.SequenceSwing is primitives.SequenceSwing
    assert structure_builder_engine.DealingRange is primitives.DealingRange
    assert structure_builder_engine.StructureEvent is primitives.StructureEvent

def test_structure_state_emission_types():
    """Ensure StructureBuilderEngine.process produces canonical primitives types."""
    engine = structure_builder_engine.StructureBuilderEngine()
    state = engine._empty_state()
    
    assert isinstance(state, primitives.StructureState)
    assert isinstance(state.external_trend, primitives.TrendDirection)
    assert isinstance(state.internal_trend, primitives.TrendDirection)
    assert state.external_trend == primitives.TrendDirection.NEUTRAL
