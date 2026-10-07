import pytest
from market_intelligence.validation_engine import ValidationEngine, ValidationStatus
from market_intelligence.primitives import Candle, RawSwing, StructureState, KeyZone, MarketEvent, EventType, ZoneType, TrendDirection

from collections import namedtuple
from market_intelligence.keyzone_engine import ZoneStatus

MockStructureState = namedtuple('MockStructureState', ['events'])
MockKeyZone = namedtuple('MockKeyZone', ['status'])
MockEvent = namedtuple('MockEvent', ['event_type'])

@pytest.fixture
def base_candles():
    # 14 candles to satisfy ATR and displacement rules
    return [
        Candle(timestamp=i*1000, open=100.0 + i, high=102.0 + i, low=99.0 + i, close=101.6 + i, volume=1000.0)
        for i in range(14)
    ]

@pytest.fixture
def mitigated_keyzone():
    return MockKeyZone(status=ZoneStatus.MITIGATED)

def test_validation_engine_all_valid(base_candles, mitigated_keyzone):
    engine = ValidationEngine()
    structure = MockStructureState(
        events=[MockEvent(event_type="INTERNAL_BOS")]
    )
    
    result = engine.evaluate(
        candles=base_candles,
        swings=[],
        structure_state=structure,
        keyzones=[mitigated_keyzone]
    )
    
    assert result.status == ValidationStatus.VALID
    assert result.score == 1.0
    assert "BODY_RATIO_SUFFICIENT" in result.reason_codes
    assert "DISPLACEMENT_CONFIRMED" in result.reason_codes
    assert "ATR_THRESHOLD_MET" in result.reason_codes
    assert "BOS_CONFIRMED" in result.reason_codes
    assert "KEYZONE_MITIGATION_VALID" in result.reason_codes

def test_validation_engine_invalid(base_candles):
    engine = ValidationEngine()
    structure = MockStructureState(events=[])
    
    # Intentionally missing KeyZone mitigation and recent BOS event
    result = engine.evaluate(
        candles=base_candles,
        swings=[],
        structure_state=structure,
        keyzones=[]
    )
    
    assert result.status == ValidationStatus.INVALID
    assert result.score < 1.0
    assert "NO_RECENT_BOS" in result.reason_codes
    assert "NO_MITIGATED_KEYZONE" in result.reason_codes
