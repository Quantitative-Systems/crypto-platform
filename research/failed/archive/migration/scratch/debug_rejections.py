import os
import json
from research.replayer.causal_replayer import CausalReplayer
from risk_engine.contracts.risk_config import RiskConfig
from research.replayer.timeframe_aligner import TimeframeAligner
from market_data.warehouse_loader import WarehouseLoader

tf_set_id = "SET_3"
symbol = "BTCUSDT"
tf_set = TimeframeAligner.get_set(tf_set_id)

htf_candles = WarehouseLoader.load_history("BTC/USDT", tf_set.htf, limit=500)
mtf_candles = WarehouseLoader.load_history("BTC/USDT", tf_set.mtf, limit=500)
ltf_candles = WarehouseLoader.load_history("BTC/USDT", tf_set.ltf, limit=500)

replayer = CausalReplayer(
    timeframe_set_id=tf_set_id,
    cache_htf_mtf=True,
    risk_config=RiskConfig(enable_circuit_breakers=False, max_risk_fraction=0.01, min_rr_floor=4.0)
)
results = replayer.run(symbol, htf_candles, mtf_candles, ltf_candles)
rejections = results.get("rejected_candidates", [])
print("Rejections:", len(rejections))
if rejections:
    import pandas as pd
    df = pd.DataFrame(rejections)
    print(df['rejection_reason'].value_counts())
print("Trades:", len(results.get("closed_trades", [])))
