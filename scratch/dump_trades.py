import json
import numpy as np
from market_data.warehouse_loader import WarehouseLoader
from research.replayer.causal_replayer import CausalReplayer
from risk_engine.contracts.risk_config import RiskConfig
from research.simulation.trade_ledger import SimulatedTrade
from typing import List
import sys

asset = sys.argv[1]
tf_set_id = sys.argv[2]
symbol = f"{asset}USDT"

if tf_set_id == "SET_3":
    htf = "1D"
    mtf = "4H"
    ltf = "1H"
else:
    htf = "4H"
    mtf = "1H"
    ltf = "15M"

htf_candles = WarehouseLoader.load_history(f"{asset}/USDT", htf, limit=50000)
mtf_candles = WarehouseLoader.load_history(f"{asset}/USDT", mtf, limit=50000)
ltf_candles = WarehouseLoader.load_history(f"{asset}/USDT", ltf, limit=50000)

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

print(f"Replaying {asset} {tf_set_id}...")
results = replayer.run(
    symbol=symbol,
    htf_candles=htf_candles,
    mtf_candles=mtf_candles,
    ltf_candles=ltf_candles
)

trades = results["closed_trades"]
print(f"Total trades: {len(trades)}")

if len(trades) > 0:
    for i, t in enumerate(trades[:5]):
        print(f"TRADE {i+1}: {t.get('trade_id')} | R: {t.get('net_r')} | PnL: {t.get('net_pnl')}")

with open(f"scratch/trades_{symbol}_{tf_set_id}.json", "w") as f:
    json.dump(trades, f, indent=2)
