import time
from warehouse_loader import WarehouseLoader

assets = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
tf_limits = {
    "1M": 200,
    "1W": 1000,
    "1D": 3000,
    "4H": 15000,
    "1H": 50000,
    "15M": 50000
}

for asset in assets:
    for tf, limit in tf_limits.items():
        print(f"Fetching {tf} for {asset} (limit={limit})...")
        WarehouseLoader.load_history(symbol=asset, timeframe=tf, limit=limit)
        time.sleep(1) # Extra buffer between bulk fetches
