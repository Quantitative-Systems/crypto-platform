import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import deterministic_fixtures
from strategy_candidate_v2.run_backtest import run_single_set, StateMachine
from unittest.mock import patch

d = deterministic_fixtures.TestDeterministicFixtures('test_a_valid_bullish_setup')
d.setUp()
try:
    htf = d.htf
    mtf = d.mtf
    ltf = d.ltf
    
    d._trigger_pullback(htf, 50, 51)
    d._trigger_pullback(mtf, 300, 301)
    
    d._trigger_pullback(ltf, 1300, 1301)
    ltf["k"][1302] = 30.0
    ltf["d"][1302] = 25.0
    ltf["k"][1301] = 20.0
    ltf["d"][1301] = 25.0
    
    htf["swing_cache"].target = 500.0
    
    ltf["st_val"][1302] = 90.0 
    ltf["close"][1302] = 100.0 
    
    # Let's monkey-patch update_state to trace it
    import strategy_candidate_v2.run_backtest as rb
    original_update_state = rb.update_state
    
    def tracing_update_state(sm, st_dir, k, d, prev_k, prev_d, direction, is_ltf, swing_cache, candle_idx):
        original_update_state(sm, st_dir, k, d, prev_k, prev_d, direction, is_ltf, swing_cache, candle_idx)
        if candle_idx in [50, 51, 54, 300, 301, 325, 1300, 1301, 1302]:
            print(f"[{'LTF' if is_ltf else 'HTF/MTF'}] Idx: {candle_idx}, k: {k}, d: {d}, state: {sm.state}")
            
    rb.update_state = tracing_update_state
    
    res = rb.run_single_set("BTC/USDT", "S3", deterministic_fixtures.make_candles(100, 1440), deterministic_fixtures.make_candles(1000, 240), deterministic_fixtures.make_candles(4000, 60))
    print("Total trades:", res["total_trades"])
finally:
    rb.update_state = original_update_state
    d.tearDown()
