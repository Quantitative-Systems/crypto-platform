import json
import sys
from market_data.warehouse_loader import WarehouseLoader
from research.replayer.causal_replayer import CausalReplayer
from risk_engine.contracts.risk_config import RiskConfig

asset = "BTC"
tf_set_id = "SET_4"
symbol = "BTCUSDT"

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

original_close = replayer.ledger.close_trade
def hooked_close(*c_args, **c_kwargs):
    trade = original_close(*c_args, **c_kwargs)
    if trade:
        print("="*60)
        print("TRADE CLOSED!")
        import json
        print(json.dumps(trade.to_dict(), indent=2))
        
        entry_p = trade.fill_entry_price
        init_sl = trade.initial_stop_price
        qty = trade.position_units
        is_long = trade.directional_permission == "PERMIT_LONG"
        
        if is_long:
            risk_dist = entry_p - init_sl
        else:
            risk_dist = init_sl - entry_p
            
        print(f"Risk Dist: {risk_dist}")
        print(f"Calculated Qty (dollar_risk / dist): {trade.dollar_risk / risk_dist if risk_dist > 0 else 'DIV_0'}")
        print(f"Actual Qty: {qty}")
        sys.exit(0)
    return trade

replayer.ledger.close_trade = hooked_close

results = replayer.run(
    symbol=symbol,
    htf_candles=htf_candles,
    mtf_candles=mtf_candles,
    ltf_candles=ltf_candles
)

print("No trades found.")
