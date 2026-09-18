"""
QCP LTF Entry Families.
Implements modular entry triggers for Strategy Grammar v2.1.
Keep setup and entry strictly separate:
e.g. FVG formation != FVG setup != entry confirmation.
"""

from typing import Tuple
import pandas as pd
import numpy as np

from research.grammar_components import AbstractEntry


class CanonicalSupertrendStochasticEntry(AbstractEntry):
    def __init__(self):
        super().__init__("CANONICAL_SUPERTREND_STOCHASTIC_ENTRY", "LTF specific trigger")
        self.parameters = {"st_len": 6, "st_fac": 5.0, "stoch_k": 25, "stoch_ks": 5, "stoch_ds": 3}
        
    def evaluate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        from strategy_candidate_v2.fast_indicators import supertrend_numpy, stochastic_numpy
        highs, lows, closes = df["high"].values, df["low"].values, df["close"].values
        st_val, st_dir = supertrend_numpy(highs, lows, closes, 
                                          atr_length=self.parameters["st_len"], 
                                          factor=self.parameters["st_fac"])
        k, d = stochastic_numpy(highs, lows, closes, 
                                k_length=self.parameters["stoch_k"], 
                                k_smooth=self.parameters["stoch_ks"], 
                                d_smooth=self.parameters["stoch_ds"])
        
        k_series = pd.Series(k, index=df.index)
        d_series = pd.Series(d, index=df.index)
        st_series = pd.Series(st_dir, index=df.index)
        
        bull_st = st_series == 1
        bull_cross = (k_series > d_series) & (k_series.shift(1) <= d_series.shift(1))
        bull_extreme = (k_series <= 25)
        bull_entry = bull_st & bull_cross & bull_extreme
        
        bear_st = st_series == -1
        bear_cross = (k_series < d_series) & (k_series.shift(1) >= d_series.shift(1))
        bear_extreme = (k_series >= 75)
        bear_entry = bear_st & bear_cross & bear_extreme
        
        return bull_entry, bear_entry


class EngulfingEntry(AbstractEntry):
    def __init__(self):
        super().__init__("ENGULFING", "Bullish/Bearish Engulfing Candle")
        
    def evaluate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        bull_eng = (df["close"].shift(1) < df["open"].shift(1)) & \
                   (df["close"] > df["open"]) & \
                   (df["close"] > df["open"].shift(1)) & \
                   (df["open"] < df["close"].shift(1))
                   
        bear_eng = (df["close"].shift(1) > df["open"].shift(1)) & \
                   (df["close"] < df["open"]) & \
                   (df["close"] < df["open"].shift(1)) & \
                   (df["open"] > df["close"].shift(1))
                   
        return bull_eng, bear_eng


class MACDCrossoverEntry(AbstractEntry):
    def __init__(self):
        super().__init__("MACD_CROSSOVER", "MACD line crosses Signal line")
        
    def evaluate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        
        bull_cross = (macd > signal) & (macd.shift(1) <= signal.shift(1))
        bear_cross = (macd < signal) & (macd.shift(1) >= signal.shift(1))
        
        return bull_cross, bear_cross


# =====================================================================
# Phase C Structural Entry Families
# =====================================================================

class EntryBreakoutClose(AbstractEntry):
    """
    ENTRY_BREAKOUT_CLOSE:
    LTF confirmation triggered when price closes beyond the high/low of the previous bar.
    """
    def __init__(self):
        super().__init__("ENTRY_BREAKOUT_CLOSE", "LTF close breaking beyond prior candle extreme")

    def evaluate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        bull_entry = (df["close"] > df["high"].shift(1)) & (df["close"] > df["open"])
        bear_entry = (df["close"] < df["low"].shift(1)) & (df["close"] < df["open"])
        return bull_entry.fillna(False), bear_entry.fillna(False)


class EntryChochConfirmation(AbstractEntry):
    """
    ENTRY_CHOCH_CONFIRMATION:
    LTF change-of-character confirmation: price breaks and closes beyond
    the most recent confirmed LTF swing high (bullish) or swing low (bearish).
    """
    def __init__(self, pivot_lookback: int = 3):
        super().__init__("ENTRY_CHOCH_CONFIRMATION", "LTF close confirming structural transition")
        self.parameters = {"pivot_lookback": pivot_lookback}

    def evaluate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        p = self.parameters["pivot_lookback"]
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        closes = df["close"].to_numpy()
        n = len(df)

        bull_entry = np.zeros(n, dtype=bool)
        bear_entry = np.zeros(n, dtype=bool)

        last_swing_h = np.nan
        last_swing_l = np.nan

        for i in range(2 * p, n):
            cand = i - p
            if (highs[cand] >= np.max(highs[cand - p: cand])) and (highs[cand] >= np.max(highs[cand + 1: i + 1])):
                last_swing_h = highs[cand]

            if (lows[cand] <= np.min(lows[cand - p: cand])) and (lows[cand] <= np.min(lows[cand + 1: i + 1])):
                last_swing_l = lows[cand]

            if np.isfinite(last_swing_h) and closes[i] > last_swing_h and closes[i-1] <= last_swing_h:
                bull_entry[i] = True

            if np.isfinite(last_swing_l) and closes[i] < last_swing_l and closes[i-1] >= last_swing_l:
                bear_entry[i] = True

        return pd.Series(bull_entry, index=df.index), pd.Series(bear_entry, index=df.index)


class EntryRejectionClose(AbstractEntry):
    """
    ENTRY_REJECTION_CLOSE:
    Rejection pin bar closing in the trade direction with prominent counter-wick.
    Bullish: Long lower wick (>= 1.5x body) and closes in upper 35% of candle range.
    Bearish: Long upper wick (>= 1.5x body) and closes in lower 35% of candle range.
    """
    def __init__(self):
        super().__init__("ENTRY_REJECTION_CLOSE", "Structural rejection candle with counter-wick")

    def evaluate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        high = df["high"]
        low = df["low"]
        open_ = df["open"]
        close = df["close"]

        candle_range = (high - low).replace(0, np.nan)
        body = (close - open_).abs()
        lower_wick = np.minimum(open_, close) - low
        upper_wick = high - np.maximum(open_, close)

        bull_rej = (lower_wick >= 1.5 * body) & ((close - low) / candle_range >= 0.65) & (close >= open_)
        bear_rej = (upper_wick >= 1.5 * body) & ((high - close) / candle_range >= 0.65) & (close <= open_)

        return bull_rej.fillna(False), bear_rej.fillna(False)


class EntrySweepReclaim(AbstractEntry):
    """
    ENTRY_SWEEP_RECLAIM:
    Intraday sweep of the prior candle low/high followed by immediate reclaim and close.
    Bullish: Low probes below prior bar low, but close finishes ABOVE prior bar close.
    Bearish: High probes above prior bar high, but close finishes BELOW prior bar close.
    """
    def __init__(self):
        super().__init__("ENTRY_SWEEP_RECLAIM", "Immediate reclaim of swept liquidity level on LTF")

    def evaluate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        bull_reclaim = (df["low"] < df["low"].shift(1)) & (df["close"] > df["close"].shift(1)) & (df["close"] > df["open"])
        bear_reclaim = (df["high"] > df["high"].shift(1)) & (df["close"] < df["close"].shift(1)) & (df["close"] < df["open"])
        return bull_reclaim.fillna(False), bear_reclaim.fillna(False)


class EntryFVGRejection(AbstractEntry):
    """
    ENTRY_FVG_REJECTION:
    Candle probes lower (testing an FVG zone) and rejects with a bullish close in the upper half of the bar.
    """
    def __init__(self):
        super().__init__("ENTRY_FVG_REJECTION", "Rejection from Fair Value Gap zone")

    def evaluate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        candle_range = (df["high"] - df["low"]).replace(0, np.nan)
        bull_rej = (df["close"] > df["open"]) & ((df["close"] - df["low"]) / candle_range >= 0.60)
        bear_rej = (df["close"] < df["open"]) & ((df["high"] - df["close"]) / candle_range >= 0.60)
        return bull_rej.fillna(False), bear_rej.fillna(False)


class EntryDisplacementConfirmation(AbstractEntry):
    """
    ENTRY_DISPLACEMENT_CONFIRMATION:
    Energetic displacement candle confirming institutional order flow.
    Body > 1.2x ATR, closing near the extreme (wick <= 25% of range).
    """
    def __init__(self, atr_period: int = 14, atr_mult: float = 1.2):
        super().__init__("ENTRY_DISPLACEMENT_CONFIRMATION", "Energetic displacement candle in trade direction")
        self.parameters = {"atr_period": atr_period, "atr_mult": atr_mult}

    def evaluate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        open_ = df["open"]

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.parameters["atr_period"], min_periods=5).mean()

        candle_range = (high - low).replace(0, np.nan)
        body = (close - open_).abs()

        # Bullish displacement
        bull_disp = (close > open_) & (body >= self.parameters["atr_mult"] * atr) & ((high - close) / candle_range <= 0.25)
        # Bearish displacement
        bear_disp = (close < open_) & (body >= self.parameters["atr_mult"] * atr) & ((close - low) / candle_range <= 0.25)

        return bull_disp.fillna(False), bear_disp.fillna(False)


def register_all_entries(registry):
    registry.register(CanonicalSupertrendStochasticEntry())
    registry.register(EngulfingEntry())
    registry.register(MACDCrossoverEntry())
    # Phase C Entries
    for cls, short_id in [
        (EntryBreakoutClose, "BREAKOUT_CLOSE"),
        (EntryChochConfirmation, "CHOCH_CONFIRMATION"),
        (EntryRejectionClose, "REJECTION_CLOSE"),
        (EntrySweepReclaim, "SWEEP_RECLAIM"),
        (EntryFVGRejection, "FVG_REJECTION"),
        (EntryDisplacementConfirmation, "DISPLACEMENT_CONFIRMATION"),
    ]:
        obj = cls()
        registry.register(obj)
        alias = cls()
        alias.id = short_id
        registry.register(alias)
