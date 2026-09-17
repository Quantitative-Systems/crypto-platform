import pandas as pd
import pandas_ta as ta
df = pd.DataFrame({'high': [10, 11, 12, 11, 10]*10, 'low': [9, 10, 11, 10, 9]*10, 'close': [9.5, 10.5, 11.5, 10.5, 9.5]*10})
df.ta.supertrend(length=10, multiplier=3, append=True)
print(df.columns)
df.ta.stoch(k=14, d=3, smooth_k=3, append=True)
print(df.columns)
