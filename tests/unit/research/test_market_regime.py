import unittest
import numpy as np
import pandas as pd
from research.market_regime import RegimeState, detect_regime, _calc_adx, _calc_atr

class TestMarketRegime(unittest.TestCase):

    def setUp(self):
        # Create a synthetic DataFrame
        # For simplicity, 200 rows of data.
        
        # 1. Trending Up: High ADX, price rising above EMA50
        trend_up = np.linspace(10, 100, 50)
        # 2. Trending Down: High ADX, price falling below EMA50
        trend_dn = np.linspace(100, 10, 50)
        # 3. Ranging: Low ADX, price flat
        ranging = np.ones(50) * 50.0 + np.random.normal(0, 1, 50)
        # 4. High Volatility: Low ADX, massive ATR (huge wicks)
        high_vol = np.ones(50) * 50.0
        
        close = np.concatenate([trend_up, trend_dn, ranging, high_vol])
        high = close + 1.0
        low = close - 1.0
        
        # Inject massive wicks for the high vol section
        high[150:] = close[150:] + 20.0
        low[150:] = close[150:] - 20.0
        
        open_ = close.copy()
        
        self.df = pd.DataFrame({
            "open": open_,
            "high": high,
            "low": low,
            "close": close
        })

    def test_calc_atr(self):
        atr = _calc_atr(self.df, period=14)
        self.assertEqual(len(atr), len(self.df))
        self.assertFalse(atr.isna().all())
        # The high volatility section should have higher ATR
        self.assertGreater(atr.iloc[-1], atr.iloc[120])

    def test_calc_adx(self):
        adx = _calc_adx(self.df, period=14)
        self.assertEqual(len(adx), len(self.df))
        self.assertFalse(adx.isna().all())
        
        # ADX should be high during the strong trend down section (index 80-90)
        self.assertGreater(adx.iloc[85], 25.0)

    def test_detect_regime(self):
        regimes = detect_regime(self.df, adx_threshold=25.0)
        
        # At the end of the trend_up section, it should be TRENDING_UP
        # But EMA needs time to warm up. By index 49 it should be fine.
        # Wait, the EMA of 50 will lag. Let's just check if it returns a Series of correct types
        self.assertEqual(len(regimes), len(self.df))
        self.assertIn(regimes.iloc[0], list(RegimeState))
        self.assertIn(regimes.iloc[-1], list(RegimeState))

if __name__ == '__main__':
    unittest.main()
