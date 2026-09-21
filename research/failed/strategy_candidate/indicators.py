import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from market_intelligence.primitives import Candle

class SupertrendEngine:
    @staticmethod
    def calculate(candles: List[Candle], atr_length: int = 6, factor: float = 5.0) -> List[Dict[str, Any]]:
        """
        Causal Supertrend calculation.
        """
        if len(candles) < atr_length:
            return [{"supertrend": 0.0, "direction": 0, "upperband": 0.0, "lowerband": 0.0} for _ in candles]
        
        highs = np.array([c.high for c in candles])
        lows = np.array([c.low for c in candles])
        closes = np.array([c.close for c in candles])
        
        # Calculate True Range
        tr = np.zeros(len(candles))
        tr[0] = highs[0] - lows[0]
        for i in range(1, len(candles)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr[i] = max(hl, hc, lc)
        
        # Calculate ATR (RMA - Wilder's Smoothing)
        atr = np.zeros(len(candles))
        atr[atr_length - 1] = np.mean(tr[:atr_length])
        for i in range(atr_length, len(candles)):
            atr[i] = (atr[i-1] * (atr_length - 1) + tr[i]) / atr_length
            
        hl2 = (highs + lows) / 2
        basic_ub = hl2 + (factor * atr)
        basic_lb = hl2 - (factor * atr)
        
        final_ub = np.zeros(len(candles))
        final_lb = np.zeros(len(candles))
        supertrend = np.zeros(len(candles))
        direction = np.zeros(len(candles), dtype=int) # 1 for bullish, -1 for bearish
        
        final_ub[:] = basic_ub[:]
        final_lb[:] = basic_lb[:]
        
        direction[0] = 1
        supertrend[0] = final_lb[0]
        
        for i in range(1, len(candles)):
            if basic_ub[i] < final_ub[i-1] or closes[i-1] > final_ub[i-1]:
                final_ub[i] = basic_ub[i]
            else:
                final_ub[i] = final_ub[i-1]
                
            if basic_lb[i] > final_lb[i-1] or closes[i-1] < final_lb[i-1]:
                final_lb[i] = basic_lb[i]
            else:
                final_lb[i] = final_lb[i-1]
                
            if supertrend[i-1] == final_ub[i-1] and closes[i] <= final_ub[i]:
                direction[i] = -1
                supertrend[i] = final_ub[i]
            elif supertrend[i-1] == final_ub[i-1] and closes[i] > final_ub[i]:
                direction[i] = 1
                supertrend[i] = final_lb[i]
            elif supertrend[i-1] == final_lb[i-1] and closes[i] >= final_lb[i]:
                direction[i] = 1
                supertrend[i] = final_lb[i]
            elif supertrend[i-1] == final_lb[i-1] and closes[i] < final_lb[i]:
                direction[i] = -1
                supertrend[i] = final_ub[i]
            else:
                direction[i] = direction[i-1]
                supertrend[i] = final_ub[i] if direction[i] == -1 else final_lb[i]
                
        results = []
        for i in range(len(candles)):
            results.append({
                "supertrend": supertrend[i],
                "direction": direction[i],
                "upperband": final_ub[i],
                "lowerband": final_lb[i]
            })
            
        return results

class StochasticEngine:
    @staticmethod
    def calculate(candles: List[Candle], k_length: int = 25, k_smooth: int = 5, d_smooth: int = 3) -> List[Dict[str, Any]]:
        """
        Causal Stochastic calculation.
        %K = SMA(Fast %K, k_smooth)
        Fast %K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
        %D = SMA(%K, d_smooth)
        """
        if len(candles) < k_length:
            return [{"k": 50.0, "d": 50.0} for _ in candles]
            
        highs = np.array([c.high for c in candles])
        lows = np.array([c.low for c in candles])
        closes = np.array([c.close for c in candles])
        
        fast_k = np.zeros(len(candles))
        fast_k.fill(50.0)
        
        for i in range(k_length - 1, len(candles)):
            window_low = np.min(lows[i - k_length + 1 : i + 1])
            window_high = np.max(highs[i - k_length + 1 : i + 1])
            
            if window_high == window_low:
                fast_k[i] = 50.0
            else:
                fast_k[i] = ((closes[i] - window_low) / (window_high - window_low)) * 100.0
                
        # Smooth %K
        k = np.zeros(len(candles))
        k.fill(50.0)
        for i in range(k_length - 1 + k_smooth - 1, len(candles)):
            k[i] = np.mean(fast_k[i - k_smooth + 1 : i + 1])
            
        # Smooth %D
        d = np.zeros(len(candles))
        d.fill(50.0)
        for i in range(k_length - 1 + k_smooth - 1 + d_smooth - 1, len(candles)):
            d[i] = np.mean(k[i - d_smooth + 1 : i + 1])
            
        results = []
        for i in range(len(candles)):
            results.append({
                "k": k[i],
                "d": d[i]
            })
            
        return results
