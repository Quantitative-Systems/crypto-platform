import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, '/home/mrcn2/crypto-platform')

from market_data.warehouse_loader import WarehouseLoader
from research.replayer.timeframe_aligner import TimeframeAligner
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.context.htf_destination_engine import HTFDestinationEngine

with open('scratch/composite_01_dev_results.json') as f:
    comp = json.load(f)

trades = comp.get('all_trades', [])
print(f"Auditing {len(trades)} Composite Trades...")

TF_SET_MAP = {
    "SET_1": {"htf": "1M", "mtf": "1w", "ltf": "1d"},
    "SET_2": {"htf": "1w", "mtf": "1d", "ltf": "4h"},
    "SET_3": {"htf": "1d", "mtf": "4h", "ltf": "1h"},
    "SET_4": {"htf": "4h", "mtf": "1h", "ltf": "15m"},
    "SET_5": {"htf": "15m", "mtf": "5m", "ltf": "1m"},
}

lang_coord = LanguageCoordinator(buffer_size=300)

trade_audits = []

for idx, t in enumerate(trades, 1):
    tid = t['trade_id']
    asset = t['symbol'].split('/')[0]
    symbol = t['symbol']
    tf_set = t['timeframe_set']
    tf_info = TF_SET_MAP[tf_set]
    dir_perm = t['directional_permission']
    is_long = ("LONG" in str(dir_perm))
    entry_ts = t['setup_timestamp']
    entry_p = t.get('fill_entry_price') or t['entry_price']
    sl_p = t['initial_stop_price']
    chosen_tp = t['target_price']
    planned_rr = t['raw_rr']
    mfe_r = t['mfe_r']
    net_r = t['net_r']
    exit_reason = t['exit_reason']
    prov = t.get('metadata', {}).get('structural_provenance', {})
    
    # Load HTF candles visible at entry_ts
    end_ms = entry_ts * 1000
    htf_candles = WarehouseLoader.load_history(symbol, tf_info['htf'], limit=1000, end_time_ms=end_ms)
    htf_slice = TimeframeAligner.filter_visible_candles(htf_candles, entry_ts, tf_info['htf'], buffer_size=80)
    
    # Compute HTF state at entry
    htf_state = lang_coord.run(htf_slice, symbol=symbol, timeframe=tf_info['htf'])
    
    # Evaluate HTF Destination Engine with candidate pool extraction
    # Candidate Pool 1: Opposing HTF KeyZones
    opposing_kzs = []
    for kz in (htf_state.keyzones or []):
        kz_type = str(getattr(kz, 'zone_type', ''))
        status = str(getattr(kz, 'status', ''))
        if "INVALIDATED" in status:
            continue
        low_b = getattr(kz, 'low_boundary', getattr(kz, 'low', None))
        high_b = getattr(kz, 'high_boundary', getattr(kz, 'high', None))
        if low_b is not None and high_b is not None and low_b > high_b:
            low_b, high_b = high_b, low_b
        zone_id = getattr(kz, 'zone_id', 'unknown_kz')
        if is_long and "BEARISH" in kz_type and low_b is not None and low_b > entry_p:
            opposing_kzs.append({"target": low_b, "type": "OPPOSING_KEYZONE", "id": zone_id, "dist_p": low_b - entry_p})
        elif (not is_long) and "BULLISH" in kz_type and high_b is not None and high_b < entry_p:
            opposing_kzs.append({"target": high_b, "type": "OPPOSING_KEYZONE", "id": zone_id, "dist_p": entry_p - high_b})

    # Candidate Pool 2: Liquidity Pools
    liq_pools = []
    for pool in (htf_state.liquidity_pools or []):
        if getattr(pool, 'is_swept', False):
            continue
        p_price = getattr(pool, 'price_level', None)
        p_id = getattr(pool, 'pool_id', 'unknown_pool')
        if p_price is None:
            continue
        if is_long and p_price > entry_p:
            liq_pools.append({"target": p_price, "type": "LIQUIDITY_POOL", "id": p_id, "dist_p": p_price - entry_p})
        elif (not is_long) and p_price < entry_p:
            liq_pools.append({"target": p_price, "type": "LIQUIDITY_POOL", "id": p_id, "dist_p": entry_p - p_price})

    # Candidate Pool 3: Weak Swing
    weak_swings = []
    struct = htf_state.structure_state
    if struct:
        ws = struct.weak_high if is_long else struct.weak_low
        if ws and ws.raw_swing:
            ws_p = ws.raw_swing.price
            ws_id = getattr(ws.raw_swing, 'swing_id', 'weak_swing')
            if is_long and ws_p > entry_p:
                weak_swings.append({"target": ws_p, "type": "WEAK_SWING", "id": ws_id, "dist_p": ws_p - entry_p})
            elif (not is_long) and ws_p < entry_p:
                weak_swings.append({"target": ws_p, "type": "WEAK_SWING", "id": ws_id, "dist_p": entry_p - ws_p})

    # Candidate Pool 4: Dealing Range 1.0x Expansion
    dr_expansions = []
    if struct and struct.dealing_range:
        dr = struct.dealing_range
        rw = dr.high_price - dr.low_price
        if rw > 0:
            if is_long:
                exp_tgt = dr.high_price + (rw * 1.0)
                if exp_tgt > entry_p:
                    dr_expansions.append({"target": exp_tgt, "type": "FORWARD_STRUCTURAL_EXPANSION", "id": f"DR_EXP_{dr.low_price}_{dr.high_price}", "dist_p": exp_tgt - entry_p})
            else:
                exp_tgt = dr.low_price - (rw * 1.0)
                if exp_tgt < entry_p:
                    dr_expansions.append({"target": exp_tgt, "type": "FORWARD_STRUCTURAL_EXPANSION", "id": f"DR_EXP_{dr.high_price}_{dr.low_price}", "dist_p": entry_p - exp_tgt})

    all_visible_candidates = opposing_kzs + liq_pools + weak_swings + dr_expansions
    all_visible_candidates.sort(key=lambda x: x["dist_p"]) # Sorted by closest

    stop_dist = abs(entry_p - sl_p)

    audit_entry = {
        "index": idx,
        "trade_id": tid,
        "asset": asset,
        "timeframe_set": tf_set,
        "direction": "LONG" if is_long else "SHORT",
        "entry_timestamp": entry_ts,
        "entry_datetime_utc": datetime.fromtimestamp(entry_ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        "entry_price": entry_p,
        "initial_sl": sl_p,
        "stop_distance": stop_dist,
        "chosen_target": chosen_tp,
        "chosen_target_provenance": prov.get("htf_target_provenance"),
        "planned_rr": planned_rr,
        "realized_net_r": net_r,
        "mfe_r": mfe_r,
        "exit_reason": exit_reason,
        "total_visible_candidates": len(all_visible_candidates),
        "closest_candidate": all_visible_candidates[0] if all_visible_candidates else None,
        "closest_dist_r": (all_visible_candidates[0]["dist_p"] / stop_dist) if (all_visible_candidates and stop_dist > 0) else None,
        "visible_candidates_breakdown": {
            "opposing_keyzones_count": len(opposing_kzs),
            "liquidity_pools_count": len(liq_pools),
            "weak_swings_count": len(weak_swings),
            "dr_expansions_count": len(dr_expansions)
        },
        "all_candidates": all_visible_candidates[:5] # Top 5 closest
    }
    trade_audits.append(audit_entry)
    print(f"[{idx:2d}/13] {tid[:30]}... | Asset: {asset} {tf_set} | Target: {chosen_tp} ({prov.get('htf_target_provenance')}) | Closest: {all_visible_candidates[0]['type'] if all_visible_candidates else 'None'} ({all_visible_candidates[0]['target'] if all_visible_candidates else 'N/A'})")

with open('scratch/composite_13_target_forensics.json', 'w') as f:
    json.dump(trade_audits, f, indent=2)

print("\nSaved detailed audit to scratch/composite_13_target_forensics.json")
