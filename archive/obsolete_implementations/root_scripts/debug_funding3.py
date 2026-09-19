import pandas as pd
from research.economic_evaluation_engine import CertifiedSeriesLoader
from market_data.data_manager import DataManager

df, dataset = CertifiedSeriesLoader().load("BTC/USDT", "4h")
fr = DataManager.get_funding_rates("BTC/USDT")
funding_df = pd.DataFrame([{"timestamp": r.timestamp, "rate": r.funding_rate} for r in fr])

print("OHLCV df open_time first:", df["open_time"].iloc[0])

ts = pd.to_datetime(df["open_time"], unit="s", utc=True)
ts_values = ts.astype('int64') // 10**6
print("ts_values first ms:", ts_values.iloc[0])

funding_map = dict(zip(funding_df["timestamp"], funding_df["rate"]))
f_ts = list(funding_map.keys())
print("funding_map first key ms:", f_ts[0])

matches = 0
for i in range(len(ts_values) - 1):
    start = ts_values.iloc[i]
    end = ts_values.iloc[i+1]
    for t in f_ts:
        if start < t <= end:
            matches += 1
print("Matches found:", matches)
