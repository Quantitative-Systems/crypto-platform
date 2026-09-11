import json
from market_data.warehouse_loader import WarehouseLoader

candles = WarehouseLoader.load_history("SOL/USDT", "1h", limit=1_000_000, start_time_ms=None, end_time_ms=1672531199000)
for c in candles:
    ts = c.timestamp if c.timestamp < 1e11 else c.timestamp // 1000
    if 1649650000 <= ts <= 1649665000:
        print(f"ts={ts}: O={c.open} H={c.high} L={c.low} C={c.close}")
