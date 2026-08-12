import pytest
from market_intelligence.validation_engine import ValidationEngine, ValidationStatus
from market_intelligence.primitives import Candle, RawSwing, StructureState, KeyZone, MarketEvent, EventType, ZoneType, TrendDirection

@pytest.fixture
def base_candles():
    # 14 candles to satisfy ATR and displacement rules
    return [
        Candle(timestamp=i*1000, open=100.0 + i, high=102.0 + i, low=99.0 + i, close=101.6 + i, volume=1000.0)
        for i in range(14)
    ]

@pytest.fixture
def mitigated_keyzone():
    return KeyZone(
        zone_id="KZ_1",
        zone_type=ZoneType.BULLISH_OB,
        direction=TrendDirection.BULLISH,
        high=102.0,
        low=99.0,
        timeframe="1H",
        creation_timestamp=1000,
        is_mitigated=True
    )

def test_validation_engine_all_valid(base_candles, mitigated_keyzone):
    engine = ValidationEngine()
    structure = StructureState(
        last_event=MarketEvent(
            timestamp=14000,
            timeframe="1H",
            symbol="BTCUSD",
            event_type=EventType.INTERNAL_BOS,
            price_level=115.0
        )
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
    structure = StructureState()
    
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
