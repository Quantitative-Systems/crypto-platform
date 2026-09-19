import sys
sys.path.insert(0, "/home/mrcn2/crypto-platform")
from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.coordinator import LanguageCoordinator
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
    conf_ts = t["metadata"]["structural_provenance"]["ltf_confirmation_timestamp"]
    retest_ts = t["metadata"]["structural_provenance"]["mtf_retest_timestamp"]
    req_dir = t["direction"]
    
    candles = WarehouseLoader.load_history(sym, ltf_tf, limit=1_000_000, start_time_ms=1609459200000, end_time_ms=1672531200000)
    for i, c in enumerate(candles):
        if c.timestamp == conf_ts:
            payload = coord.run(candles[:i+1], sym, ltf_tf)
            sweeps = [
                e for e in payload.events
                if "LIQUIDITY_SWEEP" in str(getattr(e, "event_type", ""))
                and ("BULLISH" if req_dir=="LONG" else "BEARISH") in (str(getattr(e, "direction", "")) or "")
                and getattr(e, "timestamp", 0) >= retest_ts
            ]
            print("="*60)
            print(f"Trade: {t['trade_id']} | {sym} | {st} | {req_dir}")
            print(f"  MTF Retest TS: {retest_ts}")
            print(f"  LTF Conf TS:   {conf_ts}")
            print(f"  Sweeps found:  {len(sweeps)}")
            for sw in sweeps:
                print(f"    sw: ts={sw.timestamp}, pool={getattr(sw, 'pool_id', None)}, price={getattr(sw, 'price_level', None)}, dir={getattr(sw, 'direction', None)}")
                # Look up pool in payload.liquidity_pools
                p_id = getattr(sw, 'pool_id', None)
                if p_id:
                    # extract swing id
                    parts = p_id.split("_")
                    sw_id = None
                    for k in range(len(parts)-1):
                        if parts[k] == "SW" and parts[k+1] in ("HIGH", "LOW"):
                            sw_id = f"SW_{parts[k+1]}_{parts[k+2]}"
                            break
                    if sw_id:
                        matched_swings = [s for s in payload.swings if getattr(s, 'swing_id', None) == sw_id]
                        if matched_swings:
                            ms = matched_swings[0]
                            print(f"      Matched Raw Swing: id={ms.swing_id} ts={ms.timestamp} price={ms.price} type={ms.swing_type}")
            break
