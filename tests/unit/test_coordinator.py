import pytest
from market_intelligence.coordinator import LanguageCoordinator, CoordinatorError
from market_intelligence.primitives import Candle, MarketStatePayload

def generate_candles(count: int) -> list[Candle]:
    return [
        Candle(
            timestamp=i * 1000,
            open=100.0 + (i % 5),
            high=102.0 + (i % 5),
            low=99.0 + (i % 5),
            close=101.0 + (i % 5),
            volume=1000.0,
        )
        for i in range(count)
    ]

def test_coordinator_success():
    coordinator = LanguageCoordinator(buffer_size=50)
    candles = generate_candles(100)
    
    # Should only process the last 50 candles
    payload = coordinator.run(candles)
    
    assert isinstance(payload, MarketStatePayload)
    assert payload.symbol == "BTCUSD"
    assert payload.current_price == candles[-1].close
    assert payload.trend_state is not None
    assert payload.phase_state is not None
    
    # Assert scorecard is present
    assert payload.scorecard is not None
    assert "validation_score" in payload.scorecard

def test_coordinator_empty_candles():
    coordinator = LanguageCoordinator()
    
    with pytest.raises(CoordinatorError, match="Empty candle list"):
        coordinator.run([])

def test_coordinator_engine_error():
    coordinator = LanguageCoordinator()
    
    # Intentionally malformed candle to trigger an error in an engine
    bad_candle = Candle(
        timestamp=1000,
        open=100.0,
        high=90.0,  # High is lower than open/low, which should fail validation
        low=110.0,
        close=101.0,
        volume=1000.0
    )
    
    with pytest.raises(CoordinatorError, match="Pipeline execution failed"):
        coordinator.run([bad_candle, bad_candle])
