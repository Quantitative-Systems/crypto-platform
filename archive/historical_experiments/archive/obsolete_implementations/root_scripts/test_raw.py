from research.economic_evaluation_engine import EconomicEvaluationEngine
import pandas as pd
engine = EconomicEvaluationEngine()
df, _ = engine.loader.load("BTC/USDT", "4h")
print(df["timestamp"].astype('int64').head(3).tolist())
print(df["timestamp"].head(3))
