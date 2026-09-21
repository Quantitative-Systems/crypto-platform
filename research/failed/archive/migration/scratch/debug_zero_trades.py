import os
import sys
import json
from market_data.warehouse_loader import WarehouseLoader
from research.replayer.causal_replayer import CausalReplayer
from research.replayer.timeframe_aligner import TimeframeAligner
from risk_engine.contracts.risk_config import RiskConfig

def run_diagnostic():
    tf_set_id = "SET_3"
    symbol = "BTCUSDT"
    tf_set = TimeframeAligner.get_set(tf_set_id)
    
    htf_candles = WarehouseLoader.load_history("BTC/USDT", tf_set.htf, limit=5000)
    mtf_candles = WarehouseLoader.load_history("BTC/USDT", tf_set.mtf, limit=5000)
    ltf_candles = WarehouseLoader.load_history("BTC/USDT", tf_set.ltf, limit=5000)
    
    research_risk_cfg = RiskConfig(
        enable_circuit_breakers=False,
        max_risk_fraction=0.01,
        min_rr_floor=4.0
    )
    
    replayer = CausalReplayer(
        timeframe_set_id=tf_set_id,
        initial_balance=10000.0,
        maker_fee_rate=0.0000,
        taker_fee_rate=0.0005,
        slippage_bps=5.0,
        enable_mtf_trailing=True,
        enable_profit_lock=False,
        cache_htf_mtf=True,
        risk_config=research_risk_cfg
    )
    
    results = replayer.run(
        symbol=symbol,
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles
    )
    
    print(f"Closed trades: {len(results['closed_trades'])}")
    
    print("Rejections:")
    rejections = results.get("rejected_candidates", [])
    if rejections:
        import pandas as pd
        df = pd.DataFrame(rejections)
        print(df['rejection_reason'].value_counts())
    else:
        print("No rejections.")

if __name__ == "__main__":
    run_diagnostic()
