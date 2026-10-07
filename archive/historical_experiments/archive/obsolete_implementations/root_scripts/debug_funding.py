import pandas as pd
from market_data.data_manager import DataManager
from research.data_loader import DatasetLoader

df, _ = DatasetLoader().load("BTC/USDT", "4h")
fr = DataManager.get_funding_rates("BTC/USDT")
funding_df = pd.DataFrame([{"timestamp": r.timestamp, "rate": r.funding_rate} for r in fr])
ts = pd.to_datetime(df["open_time"], unit="s", utc=True)
ts_values = ts.astype("int64") // 10**6
f_ts = funding_df["timestamp"].values
print("First 5 OHLCV ms:", ts_values.head().values)
print("First 5 Funding ms:", f_ts[:5])
matches = 0
for i in range(min(1000, len(ts_values)-1)):
    start = ts_values.iloc[i]
    end = ts_values.iloc[i+1]
    for t in f_ts:
        if start < t <= end:
            matches += 1
print("Matches in first 1000 bars:", matches)
