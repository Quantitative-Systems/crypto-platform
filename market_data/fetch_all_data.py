import time
from warehouse_loader import WarehouseLoader

assets = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", 
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "LINK/USDT", "LTC/USDT"
]

tf_limits = {
    "1w": 300,
    "1d": 1000,
    "4h": 3000,
    "15m": 5000,
    "5m": 10000,
    "1m": 15000
}

for asset in assets:
    for tf, limit in tf_limits.items():
        print(f"Fetching {tf} for {asset} (limit={limit})...")
        WarehouseLoader.load_history(symbol=asset, timeframe=tf, limit=limit)
        time.sleep(1) # Extra buffer between bulk fetches
