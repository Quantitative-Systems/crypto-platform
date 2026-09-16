"""
Tests for Universal Market Data Fabric.
"""

from market_data.universal_data_fabric import (
    UniversalMarketDataFabric,
    Venue,
    InstrumentType,
)


def test_data_fabric_canonical_series():
    fabric = UniversalMarketDataFabric()
    df = fabric.get_canonical_series("SOL/USDT", timeframe="4h")
    assert not df.empty
    assert "close" in df.columns
    assert "open" in df.columns
    assert "high" in df.columns
    assert "low" in df.columns
    assert len(df) > 50


def test_data_fabric_order_book_and_funding():
    fabric = UniversalMarketDataFabric()
    book = fabric.get_order_book_snapshot("BTC/USDT", reference_price=60000.0)
    assert book.symbol == "BTC/USDT"
    assert len(book.bids) == 10
    assert len(book.asks) == 10
    assert book.mid_price > 0
    assert book.spread_bps > 0
    assert book.bid_depth_usd > 0

    rates = fabric.get_funding_rates("ETH/USDT", lookback_intervals=10)
    assert len(rates) == 10
    assert rates[0].annualized_rate_pct != 0.0
