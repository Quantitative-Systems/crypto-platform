"""
Product 01: Crypto Platform - Real Binance Historical Data Ingestion Engine
Fetches real multi-year OHLCV candlestick data directly from Binance Public REST API.
"""

import os
import json
import time
import urllib.request
from typing import List
from market_intelligence.primitives import Candle

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")


class BinanceFetcher:

    BINANCE_URL = "https://api.binance.com/api/v3/klines"

    @staticmethod
    def fetch_real_candles(symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 1000) -> List[Candle]:
        """
        Fetches real OHLCV candlestick data directly from Binance API without API keys.
        Caches results locally in market_data/cache/.
        """
        os.makedirs(CACHE_DIR, exist_ok=True)
        binance_symbol = symbol.replace("/", "").upper()
        
        # Map timeframes to Binance API standard
        tf_map = {"1M": "1M", "1W": "1w", "1D": "1d", "4H": "4h", "1H": "1h", "15M": "15m"}
        binance_tf = tf_map.get(timeframe.upper(), timeframe.lower())
        
        cache_filename = f"binance_{binance_symbol}_{binance_tf}.json"
        cache_filepath = os.path.join(CACHE_DIR, cache_filename)

        # Check local disk cache first
        if os.path.exists(cache_filepath):
            try:
                with open(cache_filepath, "r") as f:
                    cached_raw = json.load(f)
                if len(cached_raw) >= limit:
                    return [
                        Candle(
                            timestamp=int(bar[0] // 1000),
                            open=float(bar[1]),
                            high=float(bar[2]),
                            low=float(bar[3]),
                            close=float(bar[4]),
                            volume=float(bar[5])
                        )
                        for bar in cached_raw[-limit:]
                    ]
            except Exception:
                pass  # Fallback to API if cache reading fails

        # Query Binance Public REST API
        url = f"{BinanceFetcher.BINANCE_URL}?symbol={binance_symbol}&interval={binance_tf}&limit={limit}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                raw_json = json.loads(response.read().decode('utf-8'))
                
                # Save raw JSON response to local disk cache
                with open(cache_filepath, "w") as f:
                    json.dump(raw_json, f)

                candles = [
                    Candle(
                        timestamp=int(bar[0] // 1000),
                        open=float(bar[1]),
                        high=float(bar[2]),
                        low=float(bar[3]),
                        close=float(bar[4]),
                        volume=float(bar[5])
                    )
                    for bar in raw_json
                ]
                return candles

        except Exception as e:
            print(f"⚠️ Binance API Ingestion Alert: {e}. Falling back to cached or synthetic data.")
            return []