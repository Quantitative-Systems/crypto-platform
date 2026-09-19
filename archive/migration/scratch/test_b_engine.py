import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_intelligence.primitives import Candle
from strategy_candidate.indicators import SupertrendEngine, StochasticEngine

def generate_dummy_candles(num=100):
    candles = []
    # Create an uptrend then downtrend
    for i in range(num):
        ts = 1600000000 + i * 3600
        if i < 50:
            open_p = 100 + i
            high_p = 102 + i
            low_p = 98 + i
            close_p = 101 + i
        else:
            open_p = 150 - (i - 50)
            high_p = 152 - (i - 50)
            low_p = 98 - (i - 50) # Big drop
            close_p = 99 - (i - 50)
        
        candles.append(Candle(
            timestamp=ts,
            open=float(open_p),
            high=float(high_p),
            low=float(low_p),
            close=float(close_p),
            volume=100.0
        ))
    return candles

def run_tests():
    candles = generate_dummy_candles(100)
    
    # 1. Test Supertrend
    print("Testing Supertrend 6/5...")
    st_res = SupertrendEngine.calculate(candles, atr_length=6, factor=5.0)
    assert len(st_res) == len(candles), "Result length mismatch"
    # Basic check
    last_res = st_res[-1]
    print(f"Last ST: {last_res}")
    
    # Check causality: re-calculating up to i should yield same result for i
    partial_res = SupertrendEngine.calculate(candles[:50], atr_length=6, factor=5.0)
    assert st_res[49]["supertrend"] == partial_res[-1]["supertrend"], "Causality check failed for Supertrend"
    print("Supertrend Causality OK")

    # 2. Test Stochastic 25/5/3
    print("Testing Stochastic 25/5/3...")
    stoch_res = StochasticEngine.calculate(candles, k_length=25, k_smooth=5, d_smooth=3)
    assert len(stoch_res) == len(candles), "Result length mismatch"
    print(f"Last Stoch: {stoch_res[-1]}")
    
    partial_stoch = StochasticEngine.calculate(candles[:50], k_length=25, k_smooth=5, d_smooth=3)
    assert stoch_res[49]["k"] == partial_stoch[-1]["k"], "Causality check failed for Stochastic %K"
    assert stoch_res[49]["d"] == partial_stoch[-1]["d"], "Causality check failed for Stochastic %D"
    print("Stochastic Causality OK")
    
    # 3. K/D Crossover check
    print("Testing K/D Crossover...")
    crossovers = 0
    for i in range(1, len(stoch_res)):
        prev = stoch_res[i-1]
        curr = stoch_res[i]
        
        if prev["k"] <= prev["d"] and curr["k"] > curr["d"]:
            crossovers += 1
            print(f"Bullish crossover at index {i}: K={curr['k']:.2f}, D={curr['d']:.2f}")
            
    print(f"Total bullish crossovers found: {crossovers}")
    print("ALL TESTS PASSED.")

if __name__ == "__main__":
    run_tests()
