import json
import numpy as np
from market_data.warehouse_loader import WarehouseLoader
from research.replayer.causal_replayer import CausalReplayer
from risk_engine.contracts.risk_config import RiskConfig

asset = "BTC"
tf_set_id = "SET_4"
symbol = "BTCUSDT"

htf_candles = WarehouseLoader.load_history(f"{asset}/USDT", "4H", limit=50000)
mtf_candles = WarehouseLoader.load_history(f"{asset}/USDT", "1H", limit=50000)
ltf_candles = WarehouseLoader.load_history(f"{asset}/USDT", "15M", limit=50000)

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

print("Replaying BTC SET_4...")
results = replayer.run(
    symbol=symbol,
    htf_candles=htf_candles,
    mtf_candles=mtf_candles,
    ltf_candles=ltf_candles
)

trades = results["closed_trades"]
print(f"Total trades: {len(trades)}")

for t in trades:
    print("="*60)
    print(f"TRADE ID: {t.get('trade_id')}")
    print(f"Symbol: {t.get('symbol')} | Direction: {t.get('directional_permission')}")
    print(f"Entry Time: {t.get('entry_timestamp')} | Exit Time: {t.get('exit_timestamp')}")
    print(f"Entry Price: {t.get('fill_entry_price')}")
    print(f"Init SL: {t.get('initial_stop_price')}")
    print(f"Target: {t.get('target_price')}")
    print(f"Quantity: {t.get('position_units')}")
    print(f"Risk $: {t.get('dollar_risk')}")
    
    entry_p = t.get('fill_entry_price')
    init_sl = t.get('initial_stop_price')
    qty = t.get('position_units')
    is_long = t.get('directional_permission') == "PERMIT_LONG"
    
    if is_long:
        risk_dist = entry_p - init_sl
    else:
        risk_dist = init_sl - entry_p
        
    print(f"Risk Dist: {risk_dist}")
    print(f"Calculated Qty (dollar_risk / dist): {t.get('dollar_risk') / risk_dist if risk_dist > 0 else 'DIV_0'}")
    print(f"Actual Qty: {qty}")
    
    print(f"Exit Price: {t.get('exit_price')} | Reason: {t.get('exit_reason')}")
    print(f"Realized PnL: {t.get('net_pnl')} | Realized R: {t.get('net_r')}")
    print(f"Total Friction: {t.get('total_friction_usd')}")
