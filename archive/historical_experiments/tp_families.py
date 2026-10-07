"""
QCP Take Profit Families.
Implements the Take Profit components for the strategy grammar.
All TP calculations are strictly causal and point-in-time.
"""

import pandas as pd
import numpy as np

from research.grammar_components import AbstractTakeProfit


class TPDynamicR(AbstractTakeProfit):
    def __init__(self, component_id: str = "TP_DYNAMIC_R", r_multiple: float = 4.0):
        super().__init__(component_id, f"Dynamic R-Multiple Target ({r_multiple}R)")
        self.parameters = {"r_multiple": r_multiple}
        
    def evaluate(self, df: pd.DataFrame, direction: pd.Series, stop_loss: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        r_multiple = self.parameters["r_multiple"]
        tp = pd.Series(np.nan, index=df.index)
        
        long_mask = direction == 1
        short_mask = direction == -1
        
        risk_long = df["close"][long_mask] - stop_loss[long_mask]
        tp[long_mask] = df["close"][long_mask] + (risk_long * r_multiple)
        
        risk_short = stop_loss[short_mask] - df["close"][short_mask]
        tp[short_mask] = df["close"][short_mask] - (risk_short * r_multiple)
        
        return tp


class TPLTFLiquidity(AbstractTakeProfit):
    def __init__(self, component_id: str = "TP_LTF_LIQUIDITY", lookback: int = 20):
        super().__init__(component_id, "Take Profit at Recent Swing High/Low")
        self.parameters = {"lookback": lookback}
        
    def evaluate(self, df: pd.DataFrame, direction: pd.Series, stop_loss: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        lookback = self.parameters["lookback"]
        roll_min = df["low"].rolling(lookback).min()
        roll_max = df["high"].rolling(lookback).max()
        
        tp = pd.Series(np.nan, index=df.index)
        long_mask = direction == 1
        short_mask = direction == -1
        
        tp[long_mask] = roll_max[long_mask]
        tp[short_mask] = roll_min[short_mask]
        return tp


class TPHTFStructural(AbstractTakeProfit):
    def __init__(self, component_id: str = "TP_HTF_STRUCTURAL"):
        super().__init__(component_id, "Target placed at the recent HTF Swing High/Low")
        self.parameters = {"lookback_bars": 10}

    def evaluate(self, df: pd.DataFrame, direction: pd.Series, stop_loss: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        lookback = self.parameters["lookback_bars"] * htf_scale
        roll_max = df["high"].rolling(lookback).max()
        roll_min = df["low"].rolling(lookback).min()
        
        tp = pd.Series(np.nan, index=df.index)
        long_mask = direction == 1
        short_mask = direction == -1
        
        tp[long_mask] = roll_max[long_mask]
        tp[short_mask] = roll_min[short_mask]
        return tp


class TPStructuralSwing(AbstractTakeProfit):
    """
    TP_STRUCTURAL_SWING:
    Target placed at the major opposing structural swing high (for long) or swing low (for short).
    Uses MTF scale for substantial structural expansion.
    """
    def __init__(self):
        super().__init__("TP_STRUCTURAL_SWING", "Target placed at major opposing structural swing")
        self.parameters = {"lookback_bars": 20}

    def evaluate(self, df: pd.DataFrame, direction: pd.Series, stop_loss: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        lookback = self.parameters["lookback_bars"] * max(2, mtf_scale)
        roll_max = df["high"].rolling(lookback).max()
        roll_min = df["low"].rolling(lookback).min()

        tp = pd.Series(np.nan, index=df.index)
        long_mask = direction == 1
        short_mask = direction == -1

        tp[long_mask] = roll_max[long_mask]
        tp[short_mask] = roll_min[short_mask]
        return tp


class TPLiquidityTarget(AbstractTakeProfit):
    """
    TP_LIQUIDITY_TARGET:
    Target placed at the opposing external liquidity pool (prior session / rolling 30-bar MTF extreme).
    """
    def __init__(self):
        super().__init__("TP_LIQUIDITY_TARGET", "Target placed at opposing external liquidity pool")
        self.parameters = {"lookback_bars": 30}

    def evaluate(self, df: pd.DataFrame, direction: pd.Series, stop_loss: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        lookback = self.parameters["lookback_bars"] * max(2, mtf_scale)
        roll_max = df["high"].rolling(lookback).max()
        roll_min = df["low"].rolling(lookback).min()

        tp = pd.Series(np.nan, index=df.index)
        long_mask = direction == 1
        short_mask = direction == -1

        tp[long_mask] = roll_max[long_mask]
        tp[short_mask] = roll_min[short_mask]
        return tp


def register_all_take_profits(registry):
    registry.register(TPDynamicR("TP_DYNAMIC_R", 4.0))
    registry.register(TPDynamicR("TP_FIXED_R", 4.0))
    registry.register(TPHTFStructural("TP_HTF_STRUCTURAL"))
    registry.register(TPHTFStructural("TP_HTF_STRUCTURE"))
    registry.register(TPLTFLiquidity())
    registry.register(TPStructuralSwing())
    registry.register(TPStructuralSwing())
    registry.register(TPLiquidityTarget())
    # Aliases
    tp_struct = TPStructuralSwing()
    tp_struct.id = "STRUCTURAL_TP"
    registry.register(tp_struct)
