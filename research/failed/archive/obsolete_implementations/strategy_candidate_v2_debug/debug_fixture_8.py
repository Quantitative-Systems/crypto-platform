import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import deterministic_fixtures
import strategy_candidate_v2.run_backtest as rb

d = deterministic_fixtures.TestDeterministicFixtures('test_a_valid_bullish_setup')
d.setUp()
try:
    htf = d.htf
    mtf = d.mtf
    ltf = d.ltf
    
    d._trigger_pullback(htf, 50, 51)
    d._trigger_pullback(mtf, 300, 301)
    
    d._trigger_pullback(ltf, 1300, 1301)
    ltf["k"][1302] = 22.0
    ltf["d"][1302] = 25.0
    ltf["k"][1303] = 30.0
    ltf["d"][1303] = 25.0
    
    original_update_state = rb.update_state
    def tracing_update_state(sm, st_dir, k, d, prev_k, prev_d, direction, is_ltf, swing_cache, candle_idx):
        original_update_state(sm, st_dir, k, d, prev_k, prev_d, direction, is_ltf, swing_cache, candle_idx)
        if candle_idx in [54, 325, 1301, 1302, 1303]:
            print(f"[{'LTF' if is_ltf else 'HTF/MTF'}] dir={direction} st_dir={st_dir} k={k} sm.state={sm.state}")
            
    rb.update_state = tracing_update_state
    
    # We will ALSO trace when the entry check fails!
    original_print = print
    
    res = rb.run_single_set("BTC/USDT", "S3", deterministic_fixtures.make_candles(100, 1440), deterministic_fixtures.make_candles(1000, 240), deterministic_fixtures.make_candles(4000, 60))
    print("Total trades:", res["total_trades"])
finally:
    rb.update_state = original_update_state
    d.tearDown()
