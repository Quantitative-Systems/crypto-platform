"""
QCP Trailing Stop Families.
Implements the Trailing Stop components for the strategy grammar.
All trailing logic is strictly causal and updates point-in-time.
"""

import pandas as pd
import numpy as np

from research.grammar_components import AbstractTrailing


class TrailNone(AbstractTrailing):
    def __init__(self):
        super().__init__("TRAIL_NONE", "Do not trail stop loss")
        
    def evaluate(self, df: pd.DataFrame, direction: pd.Series, current_stop: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        return current_stop.copy()


class TrailChandelier(AbstractTrailing):
    def __init__(self, component_id: str = "TRAIL_CHANDELIER"):
        super().__init__(component_id, "Chandelier Exit based trailing stop")
        self.parameters = {"length": 22, "multiplier": 3.0}
        
    def evaluate(self, df: pd.DataFrame, direction: pd.Series, current_stop: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        length = self.parameters["length"]
        mult = self.parameters["multiplier"]
        
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(length).mean()
        
        roll_high = df["high"].rolling(length).max()
        roll_low = df["low"].rolling(length).min()
        
        trail = current_stop.copy()
        long_mask = direction == 1
        short_mask = direction == -1
        
        new_long_stop = roll_high[long_mask] - (atr[long_mask] * mult)
        new_short_stop = roll_low[short_mask] + (atr[short_mask] * mult)
        
        trail[long_mask] = np.maximum(trail[long_mask], new_long_stop)
        trail[short_mask] = np.minimum(trail[short_mask], new_short_stop)
        return trail


class TrailMTFStructural(AbstractTrailing):
    def __init__(self, component_id: str = "TRAIL_MTF_STRUCTURAL"):
        super().__init__(component_id, "Trails stop behind MTF swing structure")
        self.parameters = {"lookback_bars": 10}
        
    def evaluate(self, df: pd.DataFrame, direction: pd.Series, current_stop: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        lookback = self.parameters["lookback_bars"] * mtf_scale
        roll_min = df["low"].rolling(lookback).min()
        roll_max = df["high"].rolling(lookback).max()
        
        trail = current_stop.copy()
        long_mask = direction == 1
        short_mask = direction == -1
        
        new_long_stop = roll_min[long_mask]
        new_short_stop = roll_max[short_mask]
        
        trail[long_mask] = np.maximum(trail[long_mask], new_long_stop)
        trail[short_mask] = np.minimum(trail[short_mask], new_short_stop)
        return trail


class TrailBOS(AbstractTrailing):
    """
    TRAIL_BOS:
    Trails stop loss aggressively behind each newly confirmed Break of Structure (BOS).
    Uses a 5-bar swing confirmation window on the MTF scale.
    """
    def __init__(self):
        super().__init__("TRAIL_BOS", "Trails stop behind newly confirmed Break of Structure pivots")
        self.parameters = {"pivot_bars": 5}

    def evaluate(self, df: pd.DataFrame, direction: pd.Series, current_stop: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        lookback = max(3, self.parameters["pivot_bars"] * mtf_scale // 2)
        roll_min = df["low"].rolling(lookback).min()
        roll_max = df["high"].rolling(lookback).max()

        trail = current_stop.copy()
        long_mask = direction == 1
        short_mask = direction == -1

        new_long_stop = roll_min[long_mask]
        new_short_stop = roll_max[short_mask]

        trail[long_mask] = np.maximum(trail[long_mask], new_long_stop)
        trail[short_mask] = np.minimum(trail[short_mask], new_short_stop)
        return trail


class TrailLTFStructure(AbstractTrailing):
    """
    TRAIL_LTF_STRUCTURE:
    Trails stop loss behind recent LTF swing low/high.
    """
    def __init__(self):
        super().__init__("TRAIL_LTF_STRUCTURE", "Trails stop behind recent LTF swing levels")
        self.parameters = {"lookback_bars": 5}

    def evaluate(self, df: pd.DataFrame, direction: pd.Series, current_stop: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        lookback = self.parameters["lookback_bars"]
        roll_min = df["low"].rolling(lookback).min()
        roll_max = df["high"].rolling(lookback).max()

        trail = current_stop.copy()
        long_mask = direction == 1
        short_mask = direction == -1

        new_long_stop = roll_min[long_mask]
        new_short_stop = roll_max[short_mask]

        trail[long_mask] = np.maximum(trail[long_mask], new_long_stop)
        trail[short_mask] = np.minimum(trail[short_mask], new_short_stop)
        return trail


def register_all_trailings(registry):
    registry.register(TrailNone())
    registry.register(TrailChandelier("TRAIL_CHANDELIER"))
    registry.register(TrailChandelier("TRAIL_ATR"))
    registry.register(TrailMTFStructural())
    registry.register(TrailBOS())
    registry.register(TrailLTFStructure())
