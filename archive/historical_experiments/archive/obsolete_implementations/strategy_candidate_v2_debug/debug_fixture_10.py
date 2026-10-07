import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import deterministic_fixtures
import strategy_candidate_v2.run_backtest as rb

# Remove the sed patch from run_backtest.py by restoring it
import subprocess
subprocess.run(['git', 'checkout', 'strategy_candidate_v2/run_backtest.py'])

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
    
    htf["swing_cache"] = deterministic_fixtures.MockSwingCache(500.0)
    mtf["swing_cache"] = deterministic_fixtures.MockSwingCache(300.0)
    ltf["swing_cache"] = deterministic_fixtures.MockSwingCache(200.0)
    
    ltf["st_val"][1303] = 90.0 
    ltf["close"][1303] = 100.0 
    
    # Let's monkey patch the entry check itself or just print variables!
    
    original_run = rb.run_single_set
    
    res = rb.run_single_set("BTC/USDT", "S3", deterministic_fixtures.make_candles(100, 1440), deterministic_fixtures.make_candles(1000, 240), deterministic_fixtures.make_candles(4000, 60))
    print("Total trades:", res["total_trades"])
finally:
    d.tearDown()
