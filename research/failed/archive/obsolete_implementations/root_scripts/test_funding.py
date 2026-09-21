from research.economic_evaluation_engine import EconomicEvaluationEngine
engine = EconomicEvaluationEngine()
df, dataset = engine.loader.load("BTC/USDT", "4h")
from market_data.data_manager import DataManager
funding_rates = DataManager.get_funding_rates("BTC/USDT")
print(f"DF TS type: {type(df['timestamp'].iloc[0])} val: {df['timestamp'].iloc[0]}")
print(f"Funding TS type: {type(funding_rates[0].timestamp)} val: {funding_rates[0].timestamp}")
print(f"Funding rate val: {funding_rates[0].funding_rate}")
