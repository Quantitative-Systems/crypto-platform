"""
Product 01: Crypto Platform - Historical Data Warehouse Loader
Connects BinanceFetcher real market data into the APEX Quant Warehouse.
"""

import os
from typing import List
from market_intelligence.primitives import Candle
from market_data.binance_fetcher import BinanceFetcher


class WarehouseLoader:

    @staticmethod
    def load_history(symbol: str = "BTC/USDT", timeframe: str = "1H", limit: int = 50000, start_time_ms: int = None, end_time_ms: int = None) -> List[Candle]:
        """Loads real historical market data from Binance or cached warehouse storage."""
        real_candles = BinanceFetcher.fetch_real_candles(symbol=symbol, timeframe=timeframe, limit=limit, start_time_ms=start_time_ms, end_time_ms=end_time_ms)
        
        if real_candles and len(real_candles) >= 10:
            return real_candles

        # Fail closed: never fabricate synthetic market data
        raise RuntimeError(f"Dataset unavailable for symbol={symbol}, timeframe={timeframe}")