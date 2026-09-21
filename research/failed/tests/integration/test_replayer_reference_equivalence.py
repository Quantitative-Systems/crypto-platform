"""
Test script to prove mathematical and state equivalence between the original 
stateless reference replayer and the new incremental cached replayer.
"""

import pytest
import os
import sys

from market_data.warehouse_loader import WarehouseLoader
from research.replayer.causal_replayer import CausalReplayer

ASSET = "BTC"
TF_SET = "SET_4" # 4H -> 1H -> 15M (Highest tick density)
LIMIT = 2000 # Enough to trigger trades and run both reasonably fast

def test_replayer_reference_equivalence():
    """
    Runs both replayers on a deterministic slice of data and asserts that 
    the resulting trades, metrics, and equity curves are identical.
    """
    
    # 1. Load Data
    print(f"\nLoading deterministic fixture for {ASSET} {TF_SET} (Limit {LIMIT})...")
    htf_candles = WarehouseLoader.load_history(f"{ASSET}/USDT", "4H", limit=LIMIT)
    mtf_candles = WarehouseLoader.load_history(f"{ASSET}/USDT", "1H", limit=LIMIT)
    ltf_candles = WarehouseLoader.load_history(f"{ASSET}/USDT", "15M", limit=LIMIT)
    
    assert len(htf_candles) > 0
    assert len(mtf_candles) > 0
    assert len(ltf_candles) > 0

    # 2. Run Reference (Unoptimized)
    print("Running REFERENCE implementation (cache_htf_mtf=False)...")
    ref_replayer = CausalReplayer(timeframe_set_id=TF_SET, enable_mtf_trailing=True, cache_htf_mtf=False)
    ref_output = ref_replayer.run(symbol=f"{ASSET}USDT", htf_candles=htf_candles, mtf_candles=mtf_candles, ltf_candles=ltf_candles)
    ref_trades = ref_output["closed_trades"]
    ref_curve = ref_output["equity_curve"]
    ref_runs = ref_output["engine_runs"]

    # 3. Run Optimized (Cached)
    print("Running OPTIMIZED implementation (cache_htf_mtf=True)...")
    opt_replayer = CausalReplayer(timeframe_set_id=TF_SET, enable_mtf_trailing=True, cache_htf_mtf=True)
    opt_output = opt_replayer.run(symbol=f"{ASSET}USDT", htf_candles=htf_candles, mtf_candles=mtf_candles, ltf_candles=ltf_candles)
    opt_trades = opt_output["closed_trades"]
    opt_curve = opt_output["equity_curve"]
    opt_runs = opt_output["engine_runs"]

    print("\n--- RESULTS ---")
    print(f"Ref Trades: {len(ref_trades)}")
    print(f"Opt Trades: {len(opt_trades)}")
    
    print("\nRef Engine Runs: ", ref_runs)
    print("Opt Engine Runs: ", opt_runs)
    
    # Assert Exact Equivalence
    assert len(ref_trades) == len(opt_trades), f"Mismatch in total trades: {len(ref_trades)} vs {len(opt_trades)}"
    
    for i in range(len(ref_trades)):
        rt = ref_trades[i]
        ot = opt_trades[i]
        
        assert rt["trade_id"] == ot["trade_id"]
        assert rt["entry_price"] == ot["entry_price"]
        assert rt["exit_price"] == ot["exit_price"]
        assert rt["exit_reason"] == ot["exit_reason"]
        assert rt["net_r"] == ot["net_r"]
        assert rt["setup_timestamp"] == ot["setup_timestamp"]
        
    # Assert Curve Equivalence
    assert len(ref_curve) == len(opt_curve)
    for rc, oc in zip(ref_curve, opt_curve):
        assert rc["equity"] == oc["equity"]

    # Ensure optimization actually happened!
    assert opt_runs["htf"] < ref_runs["htf"], "HTF optimization failed to reduce recalculations!"
    assert opt_runs["mtf"] < ref_runs["mtf"], "MTF optimization failed to reduce recalculations!"
    assert opt_runs["ltf"] == ref_runs["ltf"], "LTF ticks should be perfectly matched!"
