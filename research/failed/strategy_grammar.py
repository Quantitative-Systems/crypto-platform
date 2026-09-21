import enum
from typing import Callable, Tuple, Dict, Any
import numpy as np
import pandas as pd

from research.market_regime import RegimeState
from research.grammar_components import ComponentRegistry


# ==========================================
# Timeframe Execution Sets
# ==========================================
class TimeframeSet(enum.Enum):
    SET_1_MACRO = "SET_1_MACRO"         # Base: 1d. MTF: 1w (scale 7), HTF: 1mo (scale 30)
    SET_2_CORE = "SET_2_CORE"           # Base: 4h. MTF: 1d (scale 6), HTF: 1w (scale 42)
    SET_3_SWING = "SET_3_SWING"         # Base: 1h. MTF: 4h (scale 4), HTF: 1d (scale 24)
    SET_4_INTRADAY = "SET_4_INTRADAY"   # Base: 15m. MTF: 1h (scale 4), HTF: 4h (scale 16)
    SET_5_ACTIVE = "SET_5_ACTIVE"       # Base: 5m. MTF: 15m (scale 3), HTF: 1h (scale 12)
    SET_6_SCALP = "SET_6_SCALP"         # Base: 1m. MTF: 5m (scale 5), HTF: 15m (scale 15)

def get_scales_for_set(tf_set: TimeframeSet) -> Tuple[int, int]:
    """Returns (htf_scale, mtf_scale) relative to the base timeframe."""
    scales = {
        TimeframeSet.SET_1_MACRO: (30, 7),
        TimeframeSet.SET_2_CORE: (42, 6),
        TimeframeSet.SET_3_SWING: (24, 4),
        TimeframeSet.SET_4_INTRADAY: (16, 4),
        TimeframeSet.SET_5_ACTIVE: (12, 3),
        TimeframeSet.SET_6_SCALP: (15, 5),
    }
    return scales[tf_set]


# ==========================================
# Grammar Combinator
# ==========================================
class HypothesisBuilder:
    """
    Constructs a hypothesis-driven signal using predefined modular components from the ComponentRegistry.
    Outputs a DataFrame containing: signal, planned_sl, planned_tp.
    """
    
    @staticmethod
    def build_signal(
        hypothesis_id: str,
        bias_id: str,
        setup_id: str,
        entry_id: str,
        sl_id: str,
        tp_id: str,
        trailing_id: str,
        tf_set: TimeframeSet
    ) -> Callable[[pd.DataFrame, pd.Series], pd.DataFrame]:
        
        htf_scale, mtf_scale = get_scales_for_set(tf_set)
        
        def _fn(df: pd.DataFrame, regime_series: pd.Series = None) -> pd.DataFrame:
            bias_comp = ComponentRegistry.get_bias(bias_id)
            setup_comp = ComponentRegistry.get_setup(setup_id)
            entry_comp = ComponentRegistry.get_entry(entry_id)
            sl_comp = ComponentRegistry.get_stop_loss(sl_id)
            tp_comp = ComponentRegistry.get_take_profit(tp_id)
            
            bull_bias, bear_bias = bias_comp.evaluate(df, htf_scale)
            bull_setup, bear_setup = setup_comp.evaluate(df, mtf_scale)
            bull_entry, bear_entry = entry_comp.evaluate(df)
            
            if regime_series is not None:
                # Mask out bias if current regime is not compatible (if configured)
                if bias_comp.regime_compatibility:
                    compatible_bias = regime_series.isin(bias_comp.regime_compatibility)
                    bull_bias = bull_bias & compatible_bias
                    bear_bias = bear_bias & compatible_bias
                
                if setup_comp.regime_compatibility:
                    compatible_setup = regime_series.isin(setup_comp.regime_compatibility)
                    bull_setup = bull_setup & compatible_setup
                    bear_setup = bear_setup & compatible_setup
                
                if entry_comp.regime_compatibility:
                    compatible_entry = regime_series.isin(entry_comp.regime_compatibility)
                    bull_entry = bull_entry & compatible_entry
                    bear_entry = bear_entry & compatible_entry
            
            long_cond = bull_bias & bull_setup & bull_entry
            short_cond = bear_bias & bear_setup & bear_entry
            
            signal = pd.Series(0.0, index=df.index)
            signal[long_cond.fillna(False)] = 1.0
            signal[short_cond.fillna(False)] = -1.0
            
            planned_sl = sl_comp.evaluate(df, signal)
            planned_tp = tp_comp.evaluate(df, signal, planned_sl, htf_scale=htf_scale, mtf_scale=mtf_scale)
            
            out_df = pd.DataFrame({
                "signal": signal,
                "planned_sl": planned_sl,
                "planned_tp": planned_tp,
                "trailing_id": trailing_id
            }, index=df.index)

            # Store upstream funnel statistics in DataFrame attributes
            out_df.attrs["funnel"] = {
                "observations": int(len(df)),
                "regime_valid": int((bull_bias | bear_bias).sum()),
                "setup_valid": int((bull_setup | bear_setup).sum()),
                "entry_valid": int((bull_entry | bear_entry).sum()),
                "combined_candidates": int((signal != 0.0).sum()),
            }
            
            return out_df

        return _fn
