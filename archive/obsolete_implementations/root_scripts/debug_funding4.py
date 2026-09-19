import pandas as pd
from research.economic_evaluation_engine import CertifiedSeriesLoader
from market_data.data_manager import DataManager

df, dataset = CertifiedSeriesLoader().load("BTC/USDT", "4h")
fr = DataManager.get_funding_rates("BTC/USDT")
funding_df = pd.DataFrame([{"timestamp": r.timestamp, "rate": r.funding_rate} for r in fr])

ts = df["timestamp"]
ts_values = ts.astype('int64') // 10**6

funding_map = dict(zip(funding_df["timestamp"], funding_df["rate"]))
f_ts = list(funding_map.keys())

print("First OHLCV ms:", ts_values.iloc[0], ts.iloc[0])
print("First funding ms:", f_ts[0], pd.to_datetime(f_ts[0], unit='ms', utc=True))
print("Last OHLCV ms:", ts_values.iloc[-1], ts.iloc[-1])
print("Last funding ms:", f_ts[-1], pd.to_datetime(f_ts[-1], unit='ms', utc=True))

matches = 0
for i in range(len(ts_values) - 1):
    start = ts_values.iloc[i]
    end = ts_values.iloc[i+1]
    for t in f_ts:
        if start < t <= end:
            matches += 1
print("Matches found:", matches)
