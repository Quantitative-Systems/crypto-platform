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
        Supports paginated fetching for limits > 1000.
        Caches results locally in market_data/cache/.
        """
        os.makedirs(CACHE_DIR, exist_ok=True)
        binance_symbol = symbol.replace("/", "").upper()
        
        # Map timeframes to Binance API standard
        # 1M (Month), 1w (Week), 1d, 4h, 1h, 15m
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
                    print(f"✅ Loaded {limit} {timeframe} candles for {symbol} from cache.")
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
                else:
                    # We have cache, but it's not enough. We could append, but for simplicity, we'll refetch.
                    print(f"⚠️ Cache has {len(cached_raw)} candles, but {limit} requested. Refetching...")
            except Exception:
                pass  # Fallback to API if cache reading fails

        print(f"📥 Fetching {limit} {timeframe} candles for {symbol} from Binance API...")
        
        all_bars = []
        end_time_ms = int(time.time() * 1000)
        
        while len(all_bars) < limit:
            fetch_limit = min(1000, limit - len(all_bars))
            url = f"{BinanceFetcher.BINANCE_URL}?symbol={binance_symbol}&interval={binance_tf}&limit={fetch_limit}&endTime={end_time_ms}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    raw_json = json.loads(response.read().decode('utf-8'))
                    
                    if not raw_json:
                        break
                        
                    # Binance returns oldest to newest. Prepend to our list.
                    all_bars = raw_json + all_bars
                    
                    # Next request's endTime is just before the oldest candle in this chunk
                    end_time_ms = raw_json[0][0] - 1
                    
                    # Respect rate limit
                    time.sleep(0.2)
            except Exception as e:
                print(f"⚠️ Binance API Ingestion Alert: {e}. Stopping fetch.")
                break

        if all_bars:
            # Save raw JSON response to local disk cache
            try:
                with open(cache_filepath, "w") as f:
                    json.dump(all_bars, f)
            except Exception as e:
                print(f"⚠️ Failed to write cache: {e}")

        candles = [
            Candle(
                timestamp=int(bar[0] // 1000),
                open=float(bar[1]),
                high=float(bar[2]),
                low=float(bar[3]),
                close=float(bar[4]),
                volume=float(bar[5])
            )
            for bar in all_bars[-limit:]
        ]
        return candles