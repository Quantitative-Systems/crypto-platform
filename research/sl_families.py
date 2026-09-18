"""
QCP Stop Loss Families.
Implements the Stop Loss components for the strategy grammar.
All SL calculations are strictly causal and point-in-time.
"""

import pandas as pd
import numpy as np

from research.grammar_components import AbstractStopLoss


class SLATR(AbstractStopLoss):
    def __init__(self, component_id: str = "SL_ATR"):
        super().__init__(component_id, "Average True Range based Stop Loss")
        self.parameters = {"length": 14, "multiplier": 2.0}
        
    def evaluate(self, df: pd.DataFrame, direction: pd.Series, scale: int = 1) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(self.parameters["length"]).mean()
        
        sl = pd.Series(np.nan, index=df.index)
        long_mask = direction == 1
        short_mask = direction == -1
        
        sl[long_mask] = df["close"][long_mask] - (atr[long_mask] * self.parameters["multiplier"])
        sl[short_mask] = df["close"][short_mask] + (atr[short_mask] * self.parameters["multiplier"])
        return sl


class SLLTFSwing(AbstractStopLoss):
    def __init__(self, component_id: str = "SL_LTF_SWING"):
        super().__init__(component_id, "Recent Swing Low/High Stop Loss")
        self.parameters = {"lookback": 10}
        
    def evaluate(self, df: pd.DataFrame, direction: pd.Series, scale: int = 1) -> pd.Series:
        lookback = self.parameters["lookback"]
        roll_min = df["low"].rolling(lookback).min()
        roll_max = df["high"].rolling(lookback).max()
        
        sl = pd.Series(np.nan, index=df.index)
        long_mask = direction == 1
        short_mask = direction == -1
        
        sl[long_mask] = roll_min[long_mask]
        sl[short_mask] = roll_max[short_mask]
        return sl


class SLSetupInvalidation(AbstractStopLoss):
    """
    SL_SETUP_INVALIDATION:
    Stop placed at the exact invalidation extreme of the setup candle (e.g. low of the sweep / retest base).
    Uses a 3-bar local extreme with a 0.2 ATR buffer for spread safety.
    """
    def __init__(self):
        super().__init__("SL_SETUP_INVALIDATION", "Stop placed at setup invalidation extreme")
        self.parameters = {"lookback": 3, "buffer_atr": 0.2}

    def evaluate(self, df: pd.DataFrame, direction: pd.Series, scale: int = 1) -> pd.Series:
        lookback = self.parameters["lookback"]
        roll_min = df["low"].rolling(lookback).min()
        roll_max = df["high"].rolling(lookback).max()

        tr = np.maximum(df["high"] - df["low"], np.abs(df["high"] - df["close"].shift(1)))
        atr = pd.Series(tr, index=df.index).rolling(14).mean().fillna(0.0)

        sl = pd.Series(np.nan, index=df.index)
        long_mask = direction == 1
        short_mask = direction == -1

        sl[long_mask] = roll_min[long_mask] - (self.parameters["buffer_atr"] * atr[long_mask])
        sl[short_mask] = roll_max[short_mask] + (self.parameters["buffer_atr"] * atr[short_mask])
        return sl


class SLFVGInvalidation(AbstractStopLoss):
    """
    SL_FVG_INVALIDATION:
    Stop placed beyond the origin candle of the Fair Value Gap (lowest low of prior 5 bars for long,
    highest high for short).
    """
    def __init__(self):
        super().__init__("SL_FVG_INVALIDATION", "Stop placed beyond FVG origin candle")
        self.parameters = {"lookback": 5}

    def evaluate(self, df: pd.DataFrame, direction: pd.Series, scale: int = 1) -> pd.Series:
        lookback = self.parameters["lookback"] * max(1, scale)
        roll_min = df["low"].rolling(lookback).min()
        roll_max = df["high"].rolling(lookback).max()

        sl = pd.Series(np.nan, index=df.index)
        long_mask = direction == 1
        short_mask = direction == -1

        sl[long_mask] = roll_min[long_mask]
        sl[short_mask] = roll_max[short_mask]
        return sl


class SLBOSInvalidation(AbstractStopLoss):
    """
    SL_BOS_INVALIDATION:
    Stop placed at the origin of the structural break (15-period rolling extreme).
    """
    def __init__(self):
        super().__init__("SL_BOS_INVALIDATION", "Stop placed at origin of structural break")
        self.parameters = {"lookback": 15}

    def evaluate(self, df: pd.DataFrame, direction: pd.Series, scale: int = 1) -> pd.Series:
        lookback = self.parameters["lookback"] * max(1, scale)
        roll_min = df["low"].rolling(lookback).min()
        roll_max = df["high"].rolling(lookback).max()

        sl = pd.Series(np.nan, index=df.index)
        long_mask = direction == 1
        short_mask = direction == -1

        sl[long_mask] = roll_min[long_mask]
        sl[short_mask] = roll_max[short_mask]
        return sl


def register_all_stop_losses(registry):
    registry.register(SLATR("SL_ATR"))
    registry.register(SLATR("SL_ATR_REFERENCE"))
    registry.register(SLLTFSwing("SL_LTF_SWING"))
    registry.register(SLLTFSwing("STRUCTURAL_SL"))
    registry.register(SLSetupInvalidation())
    registry.register(SLFVGInvalidation())
    fvg_sl = SLFVGInvalidation()
    fvg_sl.id = "FVG_INVALIDATION_SL"
    registry.register(fvg_sl)
    registry.register(SLBOSInvalidation())
