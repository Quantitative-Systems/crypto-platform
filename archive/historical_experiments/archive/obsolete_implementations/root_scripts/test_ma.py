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
signal = generate_carry_signal(df, funding_df)
print(f"Total bars: {len(df)}")
print(f"Total 1 signals: {sum(signal)}")
print(f"Max funding MA: {funding_df['funding_rate'].rolling(21).mean().max()}")
