import pandas as pd
from research.economic_evaluation_engine import EconomicEvaluationEngine
from research.quant_models.funding_arbitrage_engine import generate_carry_signal

engine = EconomicEvaluationEngine()
df, _ = engine.loader.load("BTC/USDT", "4h")
from market_data.data_manager import DataManager
funding_rates = DataManager.get_funding_rates("BTC/USDT")
funding_df = pd.DataFrame([
    {"timestamp": r.timestamp, "funding_rate": r.funding_rate} 
    for r in funding_rates
])

df_times = df["timestamp"].astype('int64') // 10**6
fund_times = funding_df["timestamp"].astype('int64')

print("DF Times (first 3, last 3):")
print(df_times.head(3).tolist())
print(df_times.tail(3).tolist())

print("Fund Times (first 3, last 3):")
print(fund_times.head(3).tolist())
print(fund_times.tail(3).tolist())
