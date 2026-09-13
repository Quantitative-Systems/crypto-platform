import sys
sys.path.insert(0, "/home/mrcn2/crypto-platform")
from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.entry.ltf_entry_model import LTFEntryModel
import json

with open("scratch/exp_d1_dev.json") as f:
    d = json.load(f)

sweep_trades = [t for t in d["all_trades"] if "SWEEP" in t["metadata"]["structural_provenance"].get("ltf_entry_reason", "")]
coord = LanguageCoordinator()

tf_map = {"SET_2": ("1d", "4h"), "SET_3": ("4h", "1h"), "SET_4": ("1h", "15m")}

for t in sweep_trades:
    sym = t["symbol"]
    st = t["timeframe_set"]
    mtf_tf, ltf_tf = tf_map[st]
    entry_ts = t["metadata"]["structural_provenance"]["ltf_confirmation_timestamp"]
    retest_ts = t["metadata"]["structural_provenance"]["mtf_retest_timestamp"]
    req_dir = t["direction"]
    
    candles = WarehouseLoader.load_history(sym, ltf_tf, limit=1_000_000, start_time_ms=1609459200000, end_time_ms=1672531200000)
    for i, c in enumerate(candles):
        if c.timestamp == entry_ts:
            payload = coord.run(candles[:i+1], sym, ltf_tf)
            sweeps = [
                e for e in payload.events
                if "LIQUIDITY_SWEEP" in str(getattr(e, "event_type", ""))
                and ("BULLISH" if req_dir=="LONG" else "BEARISH") in (str(getattr(e, "direction", "")) or "")
                and getattr(e, "timestamp", 0) >= retest_ts
            ]
            disp_model = LTFEntryModel._sweep_displacement.displacement_model
            disp_res = disp_model.evaluate(payload, "BULLISH" if req_dir=="LONG" else "BEARISH", retest_ts)
            tid = t["trade_id"]
            print(f"{tid} | sweeps={len(sweeps)} | disp_confirmed={disp_res.is_confirmed} reason={disp_res.reversal_reason}")
            break
