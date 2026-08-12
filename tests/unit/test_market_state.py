import pytest
from market_intelligence.market_state import MarketStateAggregator
from market_intelligence.primitives import MarketStatePayload, StructureState, TrendDirection

def test_market_state_aggregator_success():
    aggregator = MarketStateAggregator()
    inputs = {
        "symbol": "BTCUSD",
        "timeframe": "1H",
        "timestamp": 1000,
        "current_price": 50000.0,
        "current_candle": None,
        "events": [],
        "swings": [],
        "structure_state": StructureState(),
        "liquidity_pools": [],
        "keyzones": [],
        "trend_state": TrendDirection.BULLISH
    }
    
    payload = aggregator.aggregate(inputs)
    assert isinstance(payload, MarketStatePayload)
    assert payload.symbol == "BTCUSD"
    assert payload.trend_state == TrendDirection.BULLISH
    
def test_market_state_aggregator_missing_key():
    aggregator = MarketStateAggregator()
    inputs = {
        "symbol": "BTCUSD",
        "timeframe": "1H"
    }
    
    with pytest.raises(ValueError, match="Missing required input for aggregation"):
        aggregator.aggregate(inputs)
