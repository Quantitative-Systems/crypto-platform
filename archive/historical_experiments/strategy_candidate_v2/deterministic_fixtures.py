import os
import sys
import unittest
import numpy as np
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy_candidate_v2.run_backtest import run_single_set, StateMachine, update_state, SwingCache
from market_intelligence.primitives import Candle

def make_candles(num, interval_minutes):
    candles = []
    base_ts = 1600000000
    for i in range(num):
        ts = base_ts + i * interval_minutes * 60
        candles.append(Candle(
            timestamp=int(ts),
            open=100.0, high=101.0, low=99.0, close=100.0, volume=1000
        ))
    return candles

def synthetic_indicators(num, interval_sec, start_ts=1600000000):
    return {
        "ts": np.array([start_ts + i * interval_sec for i in range(num)], dtype=np.float64),
        "open": np.full(num, 100.0),
        "high": np.full(num, 101.0),
        "low": np.full(num, 99.0),
        "close": np.full(num, 100.0),
        "interval": interval_sec,
        "k": np.full(num, 50.0),
        "d": np.full(num, 50.0),
        "st_dir": np.full(num, 1),
        "st_val": np.full(num, 90.0)
    }

class MockSwingCache:
    def __init__(self, target=0.0):
        self.target = target
    def get_target(self, idx, direction):
        return self.target

class TestDeterministicFixtures(unittest.TestCase):
    
    def setUp(self):
        self.htf = synthetic_indicators(100, 86400) # 1D
        self.mtf = synthetic_indicators(1000, 14400) # 4H
        self.ltf = synthetic_indicators(4000, 3600) # 1H
        
        # Inject realistic swing caches
        self.htf["swing_cache"] = MockSwingCache()
        self.mtf["swing_cache"] = MockSwingCache()
        self.ltf["swing_cache"] = MockSwingCache()
        
        self.patcher = patch('strategy_candidate_v2.run_backtest.compute_all_indicators')
        self.mock_compute = self.patcher.start()
        self.mock_compute.side_effect = [self.htf, self.mtf, self.ltf]

    def tearDown(self):
        self.patcher.stop()

    def _trigger_pullback(self, ind_dict, idx_peak, idx_pullback, direction=1):
        if direction == 1:
            ind_dict["k"][idx_peak] = 80.0
            ind_dict["k"][idx_pullback] = 20.0
            ind_dict["st_dir"][:] = 1
        else:
            ind_dict["k"][idx_peak] = 20.0
            ind_dict["k"][idx_pullback] = 80.0
            ind_dict["st_dir"][:] = -1

    def test_a_valid_bullish_setup(self):
        self._trigger_pullback(self.htf, 50, 51)
        self._trigger_pullback(self.mtf, 300, 301)
        
        self._trigger_pullback(self.ltf, 1300, 1301)
        self.ltf["k"][1302] = 22.0
        self.ltf["d"][1302] = 25.0
        self.ltf["k"][1303] = 30.0
        self.ltf["d"][1303] = 25.0
        
        self.htf["swing_cache"] = MockSwingCache(500.0)
        
        self.ltf["st_val"][1303] = 90.0 
        self.ltf["close"][1303] = 100.0 
        self.ltf["high"][1306] = 600.0
        
        res = run_single_set("BTC/USDT", "S3", make_candles(100, 1440), make_candles(1000, 240), make_candles(4000, 60))
        self.assertGreater(res["total_trades"], 0)
        self.assertEqual(res["trades"][0]["direction"], "LONG")

    def test_b_valid_bearish_setup(self):
        self._trigger_pullback(self.htf, 50, 51, direction=-1)
        self._trigger_pullback(self.mtf, 300, 301, direction=-1)
        
        self._trigger_pullback(self.ltf, 1300, 1301, direction=-1)
        self.ltf["k"][1302] = 78.0
        self.ltf["d"][1302] = 75.0
        self.ltf["k"][1303] = 70.0
        self.ltf["d"][1303] = 75.0
        
        self.htf["swing_cache"] = MockSwingCache(10.0)
        
        self.ltf["st_val"][1303] = 110.0 
        self.ltf["close"][1303] = 100.0 
        self.ltf["low"][1306] = 5.0
        
        res = run_single_set("BTC/USDT", "S3", make_candles(100, 1440), make_candles(1000, 240), make_candles(4000, 60))
        self.assertGreater(res["total_trades"], 0)
        self.assertEqual(res["trades"][0]["direction"], "SHORT")

    def test_g_wrong_direction_tp3_fails(self):
        # Even if bullish setup, if st_dir is wrong, it fails.
        self._trigger_pullback(self.htf, 50, 51)
        self._trigger_pullback(self.mtf, 300, 301)
        self._trigger_pullback(self.ltf, 1300, 1301)
        self.ltf["k"][1302] = 22.0
        self.ltf["d"][1302] = 25.0
        self.ltf["k"][1303] = 30.0
        self.ltf["d"][1303] = 25.0
        self.htf["swing_cache"] = MockSwingCache(10.0) # below entry = invalid for long
        
        self.ltf["st_val"][1303] = 90.0 
        self.ltf["close"][1303] = 100.0 
        
        res = run_single_set("BTC/USDT", "S3", make_candles(100, 1440), make_candles(1000, 240), make_candles(4000, 60))
        self.assertGreater(res["rejected_6r"], 0)
        self.assertEqual(res["total_trades"], 0)

    def test_h_tp3_less_than_6r_fails(self):
        self._trigger_pullback(self.htf, 50, 51)
        self._trigger_pullback(self.mtf, 300, 301)
        self._trigger_pullback(self.ltf, 1300, 1301)
        self.ltf["k"][1302] = 22.0
        self.ltf["d"][1302] = 25.0
        self.ltf["k"][1303] = 30.0
        self.ltf["d"][1303] = 25.0
        
        self.htf["swing_cache"] = MockSwingCache(150.0)
        
        self.ltf["st_val"][1303] = 90.0  # risk 10, reward 50, rr 5
        self.ltf["close"][1303] = 100.0 
        
        res = run_single_set("BTC/USDT", "S3", make_candles(100, 1440), make_candles(1000, 240), make_candles(4000, 60))
        self.assertGreater(res["rejected_6r"], 0)
        self.assertEqual(res["total_trades"], 0)

if __name__ == "__main__":
    unittest.main()
