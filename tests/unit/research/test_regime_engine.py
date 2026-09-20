"""
Unit and Causality Tests for RegimeEngine.
Ensures point-in-time calculation and verifies no future lookahead.
"""

import unittest
import numpy as np
import pandas as pd

from research.regime_engine import RegimeEngine, RegimeState, classify_market_regime


def generate_mock_ohlcv(size: int = 250, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    returns = np.random.normal(0.0005, 0.02, size)
    close = 100.0 * np.exp(np.cumsum(returns))
    high = close * (1.0 + np.abs(np.random.normal(0, 0.01, size)))
    low = close * (1.0 - np.abs(np.random.normal(0, 0.01, size)))
    open_ = np.roll(close, 1)
    open_[0] = 100.0
    volume = np.random.uniform(100, 1000, size)
    
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


class TestRegimeEngine(unittest.TestCase):

    def setUp(self):
        self.df = generate_mock_ohlcv(300)
        self.engine = RegimeEngine(warmup_bars=50)

    def test_output_structure(self):
        output = self.engine.compute(self.df)
        self.assertEqual(len(output.regime), len(self.df))
        self.assertEqual(len(output.measurements), len(self.df))
        
        # Warm-up bars must be UNKNOWN
        for i in range(50):
            self.assertEqual(output.regime.iloc[i], RegimeState.UNKNOWN.value)
            
        # Ensure all states emitted after warmup are valid RegimeStates
        valid_states = {s.value for s in RegimeState}
        for state in output.regime.iloc[50:].unique():
            self.assertIn(state, valid_states)

    def test_measurements_populated(self):
        output = self.engine.compute(self.df)
        m = output.measurements
        required_cols = [
            "fast_ma", "slow_ma", "ma_alignment", "ma_slope",
            "realized_vol", "atr", "atr_percentile", "bb_width_pct",
            "range_efficiency", "plus_di", "minus_di", "adx", "directional_diff"
        ]
        for col in required_cols:
            self.assertIn(col, m.columns)
            self.assertFalse(m[col].iloc[50:].isna().all(), f"Column {col} is all NaN")

    def test_causality_under_future_perturbation(self):
        """
        Anti-lookahead invariant:
        Perturbing data at and after index 150 MUST NOT change any regime
        or measurement values at or before index 149.
        """
        df_orig = self.df.copy()
        df_pert = self.df.copy()
        
        # Inject massive shock at index 150 onwards
        df_pert.loc[150:, "close"] *= 3.0
        df_pert.loc[150:, "high"] *= 3.5
        df_pert.loc[150:, "low"] *= 2.5
        df_pert.loc[150:, "volume"] *= 10.0

        out_orig = self.engine.compute(df_orig)
        out_pert = self.engine.compute(df_pert)

        # Regimes up to 149 must match exactly
        pd.testing.assert_series_equal(
            out_orig.regime.iloc[:150],
            out_pert.regime.iloc[:150],
            check_names=False
        )

        # Measurements up to 149 must match exactly
        for col in out_orig.measurements.columns:
            pd.testing.assert_series_equal(
                out_orig.measurements[col].iloc[:150],
                out_pert.measurements[col].iloc[:150],
                check_names=False,
                rtol=1e-5,
                atol=1e-8
            )


if __name__ == "__main__":
    unittest.main()
