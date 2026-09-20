"""
Unit and Causality Tests for Structural Components (Setups, Entries, Exits).
Ensures zero lookahead and verified component registration.
"""

import unittest
import numpy as np
import pandas as pd

from research.grammar_components import ComponentRegistry
import research.bias_families as bf
import research.setup_families as sf
import research.entry_families as ef
import research.sl_families as slf
import research.tp_families as tpf
import research.trailing_families as trf

from tests.test_regime_engine import generate_mock_ohlcv


class TestStructuralComponents(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        bf.register_all_biases(ComponentRegistry)
        sf.register_all_setups(ComponentRegistry)
        ef.register_all_entries(ComponentRegistry)
        slf.register_all_stop_losses(ComponentRegistry)
        tpf.register_all_take_profits(ComponentRegistry)
        trf.register_all_trailings(ComponentRegistry)

    def setUp(self):
        self.df = generate_mock_ohlcv(250)

    def test_component_registry_membership(self):
        # Verify all Phase C components are registered
        expected_setups = ["SETUP_FVG_TAP", "SETUP_LIQUIDITY_SWEEP", "SETUP_BREAKOUT_RETEST", "SETUP_CHOCH_BOS_RETEST"]
        for s in expected_setups:
            comp = ComponentRegistry.get_setup(s)
            self.assertIsNotNone(comp, f"Setup {s} not found in ComponentRegistry")

        expected_entries = [
            "ENTRY_BREAKOUT_CLOSE", "ENTRY_CHOCH_CONFIRMATION", "ENTRY_REJECTION_CLOSE",
            "ENTRY_SWEEP_RECLAIM", "ENTRY_FVG_REJECTION", "ENTRY_DISPLACEMENT_CONFIRMATION"
        ]
        for e in expected_entries:
            comp = ComponentRegistry.get_entry(e)
            self.assertIsNotNone(comp, f"Entry {e} not found in ComponentRegistry")

        expected_sl = ["SL_LTF_SWING", "SL_SETUP_INVALIDATION", "SL_FVG_INVALIDATION", "SL_BOS_INVALIDATION", "SL_ATR_REFERENCE"]
        for sl in expected_sl:
            comp = ComponentRegistry.get_stop_loss(sl)
            self.assertIsNotNone(comp, f"SL {sl} not found in ComponentRegistry")

        expected_tp = ["TP_STRUCTURAL_SWING", "TP_LIQUIDITY_TARGET", "TP_HTF_STRUCTURE", "TP_FIXED_R"]
        for tp in expected_tp:
            comp = ComponentRegistry.get_take_profit(tp)
            self.assertIsNotNone(comp, f"TP {tp} not found in ComponentRegistry")

        expected_trails = ["TRAIL_NONE", "TRAIL_BOS", "TRAIL_LTF_STRUCTURE", "TRAIL_ATR", "TRAIL_MTF_STRUCTURAL"]
        for tr in expected_trails:
            comp = ComponentRegistry.get_trailing(tr)
            self.assertIsNotNone(comp, f"Trailing {tr} not found in ComponentRegistry")

    def test_setup_causality_under_perturbation(self):
        """Verify that modifying future bars does not change past setup evaluations."""
        df_orig = self.df.copy()
        df_pert = self.df.copy()
        df_pert.loc[150:, "close"] *= 2.5
        df_pert.loc[150:, "high"] *= 2.5
        df_pert.loc[150:, "low"] *= 2.0

        for setup_id in ["SETUP_FVG_TAP", "SETUP_LIQUIDITY_SWEEP", "SETUP_BREAKOUT_RETEST", "SETUP_CHOCH_BOS_RETEST"]:
            comp = ComponentRegistry.get_setup(setup_id)
            bull1, bear1 = comp.evaluate(df_orig, scale=1)
            bull2, bear2 = comp.evaluate(df_pert, scale=1)

            pd.testing.assert_series_equal(bull1.iloc[:150], bull2.iloc[:150], check_names=False)
            pd.testing.assert_series_equal(bear1.iloc[:150], bear2.iloc[:150], check_names=False)

    def test_entry_causality_under_perturbation(self):
        """Verify that modifying future bars does not change past entry evaluations."""
        df_orig = self.df.copy()
        df_pert = self.df.copy()
        df_pert.loc[150:, "close"] *= 2.5
        df_pert.loc[150:, "high"] *= 2.5
        df_pert.loc[150:, "low"] *= 2.0

        entries_to_test = [
            "ENTRY_BREAKOUT_CLOSE", "ENTRY_CHOCH_CONFIRMATION", "ENTRY_REJECTION_CLOSE",
            "ENTRY_SWEEP_RECLAIM", "ENTRY_FVG_REJECTION", "ENTRY_DISPLACEMENT_CONFIRMATION"
        ]
        for entry_id in entries_to_test:
            comp = ComponentRegistry.get_entry(entry_id)
            bull1, bear1 = comp.evaluate(df_orig)
            bull2, bear2 = comp.evaluate(df_pert)

            pd.testing.assert_series_equal(bull1.iloc[:150], bull2.iloc[:150], check_names=False)
            pd.testing.assert_series_equal(bear1.iloc[:150], bear2.iloc[:150], check_names=False)

    def test_sl_tp_causality(self):
        """Verify SL and TP evaluation produces valid causal levels."""
        df = self.df.copy()
        direction = pd.Series(1.0, index=df.index)
        
        sl_comp = ComponentRegistry.get_stop_loss("SL_SETUP_INVALIDATION")
        sl_vals = sl_comp.evaluate(df, direction)
        self.assertEqual(len(sl_vals), len(df))
        # Long stop must be strictly below current close
        valid_idx = sl_vals.dropna().index
        self.assertTrue((sl_vals.loc[valid_idx] < df["close"].loc[valid_idx]).all())

        tp_comp = ComponentRegistry.get_take_profit("TP_STRUCTURAL_SWING")
        tp_vals = tp_comp.evaluate(df, direction, sl_vals)
        self.assertEqual(len(tp_vals), len(df))
        # Long TP must be at or above close
        valid_tp_idx = tp_vals.dropna().index
        self.assertTrue((tp_vals.loc[valid_tp_idx] >= df["close"].loc[valid_tp_idx]).all())


if __name__ == "__main__":
    unittest.main()
