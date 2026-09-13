import os
import sys
import json

sys.path.insert(0, "/home/mrcn2/crypto-platform")

from market_data.warehouse_loader import WarehouseLoader
from research.replayer.causal_replayer import CausalReplayer
from risk_engine.contracts.risk_config import RiskConfig
from datetime import datetime, timezone

# Load candles for BTC_SET_3 and SOL_SET_4
def test_stream_variants(asset, tf_set):
    print(f"\n=================== {asset}_{tf_set} ===================")
    tf_info = {
        "SET_3": {"htf": "1d", "mtf": "4h", "ltf": "1h"},
        "SET_4": {"htf": "4h", "mtf": "1h", "ltf": "15m"}
    }[tf_set]

    symbol = f"{asset}/USDT"
    htf_candles = WarehouseLoader.load_history(symbol, tf_info["htf"])
    mtf_candles = WarehouseLoader.load_history(symbol, tf_info["mtf"])
    ltf_candles = WarehouseLoader.load_history(symbol, tf_info["ltf"])

    start_ms = int(datetime(2021, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    ltf_candles = [c for c in ltf_candles if start_ms <= c.timestamp <= end_ms]

    risk_cfg = RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=4.0,
        min_stop_distance_pct=0.001,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False
    )

    # Variant 1: Pure H0 (CLOSEST_OBJECTIVE, all else False)
    rep_h0 = CausalReplayer(
        timeframe_set_id=tf_set,
        initial_balance=10000.0,
        enable_mtf_trailing=True,
        target_hierarchy="CLOSEST_OBJECTIVE",
        enable_forward_expansion=False,
        enforce_displacement_polarity=False,
        enable_breakeven_1r=False,
        risk_config=risk_cfg
    )
    res_h0 = rep_h0.run(f"{asset}/USDT", htf_candles, mtf_candles, ltf_candles)
    t_h0 = res_h0.get("closed_trades", [])
    r_h0 = sum(t.realized_r for t in t_h0)
    print(f"1. Pure H0 (CLOSEST): trades={len(t_h0)}, net_R={r_h0:.2f}R")

    # Variant 2: Pure Single-Variable STRUCTURAL_OBJECTIVE (All else False)
    rep_v2 = CausalReplayer(
        timeframe_set_id=tf_set,
        initial_balance=10000.0,
        enable_mtf_trailing=True,
        target_hierarchy="STRUCTURAL_OBJECTIVE",
        enable_forward_expansion=False,
        enforce_displacement_polarity=False,
        enable_breakeven_1r=False,
        risk_config=risk_cfg
    )
    res_v2 = rep_v2.run(f"{asset}/USDT", htf_candles, mtf_candles, ltf_candles)
    t_v2 = res_v2.get("closed_trades", [])
    r_v2 = sum(t.realized_r for t in t_v2)
    print(f"2. Pure STRUCTURAL_OBJECTIVE (No exp, no pol, no be): trades={len(t_v2)}, net_R={r_v2:.2f}R")

    # Variant 3: STRUCTURAL_OBJECTIVE + Forward Expansion (No pol, no be)
    rep_v3 = CausalReplayer(
        timeframe_set_id=tf_set,
        initial_balance=10000.0,
        enable_mtf_trailing=True,
        target_hierarchy="STRUCTURAL_OBJECTIVE",
        enable_forward_expansion=True,
        enforce_displacement_polarity=False,
        enable_breakeven_1r=False,
        risk_config=risk_cfg
    )
    res_v3 = rep_v3.run(f"{asset}/USDT", htf_candles, mtf_candles, ltf_candles)
    t_v3 = res_v3.get("closed_trades", [])
    r_v3 = sum(t.realized_r for t in t_v3)
    print(f"3. STRUCTURAL_OBJECTIVE + Expansion (No pol, no be): trades={len(t_v3)}, net_R={r_v3:.2f}R")

    # Variant 4: Current user edit (STRUCTURAL_OBJECTIVE + exp + pol + be)
    rep_v4 = CausalReplayer(
        timeframe_set_id=tf_set,
        initial_balance=10000.0,
        enable_mtf_trailing=True,
        target_hierarchy="STRUCTURAL_OBJECTIVE",
        enable_forward_expansion=True,
        enforce_displacement_polarity=True,
        enable_breakeven_1r=True,
        risk_config=risk_cfg
    )
    res_v4 = rep_v4.run(f"{asset}/USDT", htf_candles, mtf_candles, ltf_candles)
    t_v4 = res_v4.get("closed_trades", [])
    r_v4 = sum(t.realized_r for t in t_v4)
    print(f"4. With BE + Polarity + Exp (User edit): trades={len(t_v4)}, net_R={r_v4:.2f}R")

test_stream_variants("BTC", "SET_3")
test_stream_variants("SOL", "SET_4")
