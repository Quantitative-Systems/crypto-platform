import json

with open("scratch/exp_e1_dev.json") as f:
    d = json.load(f)

trades = d["all_trades"]
print(f"Total E1 Trades: {len(trades)}")
for i, t in enumerate(trades):
    sym = t.get("symbol")
    st = t.get("timeframe_set")
    dir_ = t.get("direction")
    ts = t.get("entry_timestamp")
    prov = t.get("metadata", {}).get("structural_provenance", {})
    trig = prov.get("ltf_entry_reason")
    nr = t.get("net_r")
    mfe = t.get("mfe_r")
    mae = t.get("mae_r")
    ex = t.get("exit_reason")
    sp = prov.get("sweep_provenance")
    tid = t.get("trade_id")
    print(f"[{i+1:02d}] {sym:8s} | {st:6s} | {dir_:7s} | ts={ts} | Net={nr:+.4f}R | MFE={mfe:.2f}R | MAE={mae:.2f}R | Exit={ex:20s} | {tid}")
    if sp:
        print(f"     Sweep Provenance: swept_swing_ts={sp.get('swept_ltf_swing_timestamp')} | swept_price={sp.get('swept_swing_price')} | sweep_dir={sp.get('sweep_direction')} | sweep_conf_ts={sp.get('sweep_confirmation_timestamp')} | disp_conf_ts={sp.get('displacement_confirmation_timestamp')} | bars_between={sp.get('number_of_ltf_bars_between')} | retest_ts={sp.get('mtf_retest_timestamp')} | causally_after={sp.get('sweep_occurred_causally_after_retest')}")
    else:
        print("     NO SWEEP PROVENANCE RECORDED")
