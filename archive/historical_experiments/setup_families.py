"""
QCP MTF Structural Setup Families.
Implements modular structural setups for Strategy Grammar v2.1.
All setups are strictly causal, point-in-time, and expose verifiable boundaries.
"""

from typing import Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np

from research.grammar_components import AbstractSetup


class CanonicalSupertrendStochasticSetup(AbstractSetup):
    def __init__(self):
        super().__init__("CANONICAL_SUPERTREND_STOCHASTIC_SETUP", "Pullback confirmation on MTF")
        self.parameters = {"st_len": 6, "st_fac": 5.0, "stoch_k": 25, "stoch_ks": 5, "stoch_ds": 3}
        
    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        from strategy_candidate_v2.fast_indicators import supertrend_numpy, stochastic_numpy
        highs, lows, closes = df["high"].values, df["low"].values, df["close"].values
        st_val, st_dir = supertrend_numpy(highs, lows, closes, 
                                          atr_length=self.parameters["st_len"] * scale, 
                                          factor=self.parameters["st_fac"])
        k, d = stochastic_numpy(highs, lows, closes, 
                                k_length=self.parameters["stoch_k"] * scale, 
                                k_smooth=self.parameters["stoch_ks"], 
                                d_smooth=self.parameters["stoch_ds"])
                                
        k_series = pd.Series(k, index=df.index)
        st_series = pd.Series(st_dir, index=df.index)
        
        bull_st = st_series == 1
        bull_extreme = k_series <= 25
        
        bear_st = st_series == -1
        bear_extreme = k_series >= 75
        
        return (bull_st & bull_extreme), (bear_st & bear_extreme)


class PullbackSetup(AbstractSetup):
    def __init__(self):
        super().__init__("PULLBACK", "Price pulls back to 20 EMA")
        
    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        ema20 = df["close"].ewm(span=20 * scale, adjust=False).mean()
        bull_pb = (df["low"] <= ema20) & (df["close"] > ema20)
        bear_pb = (df["high"] >= ema20) & (df["close"] < ema20)
        return bull_pb, bear_pb


class BreakoutSetup(AbstractSetup):
    def __init__(self):
        super().__init__("BREAKOUT", "Price breaking out of 20-period range")
        
    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        roll_high = df["high"].rolling(20 * scale).max().shift(1)
        roll_low = df["low"].rolling(20 * scale).min().shift(1)
        bull_bo = df["close"] > roll_high
        bear_bo = df["close"] < roll_low
        return bull_bo, bear_bo


# =====================================================================
# Phase C Structural Setups
# =====================================================================

class SetupFVGTap(AbstractSetup):
    """
    SETUP_FVG_TAP:
    Causally identifies 3-candle Fair Value Gaps (FVG) created by displacement,
    and identifies subsequent taps into the unmitigated gap zone.
    
    Causality Invariants:
    - Bullish FVG confirmed at close of candle t: low[t] > high[t-2] with displacement at t-1.
      Boundaries: gap_bottom = high[t-2], gap_top = low[t].
    - Bearish FVG confirmed at close of candle t: high[t] < low[t-2] with displacement at t-1.
      Boundaries: gap_top = low[t-2], gap_bottom = high[t].
    - Tap: At bar k > t, price reaches into the gap zone without closing past invalidation.
    - Max age: Gaps expire after max_age_bars to avoid stale zones.
    """
    def __init__(self, max_age_bars: int = 30):
        super().__init__("SETUP_FVG_TAP", "Causal Fair Value Gap tap on MTF")
        self.parameters = {"max_age_bars": max_age_bars, "displacement_atr_mult": 1.0}

    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        n = len(df)
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        opens = df["open"].to_numpy()
        closes = df["close"].to_numpy()

        # Compute ATR for displacement qualification
        tr1 = highs - lows
        tr2 = np.abs(highs - np.roll(closes, 1))
        tr3 = np.abs(lows - np.roll(closes, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        # Simple rolling ATR
        atr = pd.Series(tr).rolling(14 * scale, min_periods=5).mean().to_numpy()

        max_age = self.parameters["max_age_bars"] * scale
        mult = self.parameters["displacement_atr_mult"]

        bull_tap = np.zeros(n, dtype=bool)
        bear_tap = np.zeros(n, dtype=bool)

        # Track active FVGs: list of (formed_idx, gap_bottom, gap_top)
        active_bull_fvgs = []
        active_bear_fvgs = []

        for i in range(2, n):
            # 1. Check if an FVG is tapped by current bar i
            # Current bar tests active bullish FVGs
            curr_low = lows[i]
            curr_close = closes[i]
            surviving_bull = []
            for formed_idx, b_bot, b_top in active_bull_fvgs:
                if (i - formed_idx) > max_age:
                    continue
                # Tap condition: low reaches into gap (curr_low <= b_top) and closes above or within (curr_close >= b_bot)
                if curr_low <= b_top and curr_close >= b_bot:
                    bull_tap[i] = True
                # Invalidation: if price closes below bottom, gap is dead
                if curr_close >= b_bot:
                    surviving_bull.append((formed_idx, b_bot, b_top))
            active_bull_fvgs = surviving_bull

            # Current bar tests active bearish FVGs
            curr_high = highs[i]
            surviving_bear = []
            for formed_idx, b_bot, b_top in active_bear_fvgs:
                if (i - formed_idx) > max_age:
                    continue
                # Tap condition: high reaches into gap (curr_high >= b_bot) and closes below or within (curr_close <= b_top)
                if curr_high >= b_bot and curr_close <= b_top:
                    bear_tap[i] = True
                # Invalidation: if price closes above top, gap is dead
                if curr_close <= b_top:
                    surviving_bear.append((formed_idx, b_bot, b_top))
            active_bear_fvgs = surviving_bear

            # 2. Check if a new FVG forms at bar i (available for future bars)
            # Bullish FVG: candle i-1 is bullish displacement, low[i] > high[i-2]
            body_prev = closes[i-1] - opens[i-1]
            if body_prev > mult * atr[i-1] and lows[i] > highs[i-2]:
                active_bull_fvgs.append((i, highs[i-2], lows[i]))

            # Bearish FVG: candle i-1 is bearish displacement, high[i] < low[i-2]
            body_prev_bear = opens[i-1] - closes[i-1]
            if body_prev_bear > mult * atr[i-1] and highs[i] < lows[i-2]:
                active_bear_fvgs.append((i, highs[i], lows[i-2]))

        return pd.Series(bull_tap, index=df.index), pd.Series(bear_tap, index=df.index)


class SetupLiquiditySweep(AbstractSetup):
    """
    SETUP_LIQUIDITY_SWEEP:
    Price sweeps a previously identifiable causal liquidity reference:
    - Swing high/low (confirmed with backward-looking pivot delay)
    - Session/rolling high/low (past 20 * scale bars)
    
    Causality Invariants:
    - Reference level is strictly established on or before bar i-1.
    - Bullish sweep (sell-side liquidity sweep): Low probes below reference low, but closes above reference low.
    - Bearish sweep (buy-side liquidity sweep): High probes above reference high, but closes below reference high.
    """
    def __init__(self, lookback: int = 20):
        super().__init__("SETUP_LIQUIDITY_SWEEP", "Causal liquidity sweep on MTF")
        self.parameters = {"lookback": lookback}

    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        lookback = self.parameters["lookback"] * scale
        highs = df["high"]
        lows = df["low"]
        closes = df["close"]

        # Strictly backward-looking reference: shifted by 1 to exclude current bar
        ref_high = highs.rolling(lookback, min_periods=10).max().shift(1)
        ref_low = lows.rolling(lookback, min_periods=10).min().shift(1)

        # Bullish sweep: Low pierces below prior support low, close holds at or above
        bull_sweep = (lows < ref_low) & (closes >= ref_low)
        # Bearish sweep: High pierces above prior resistance high, close holds at or below
        bear_sweep = (highs > ref_high) & (closes <= ref_high)

        return bull_sweep.fillna(False), bear_sweep.fillna(False)


class SetupBreakoutRetest(AbstractSetup):
    """
    SETUP_BREAKOUT_RETEST:
    Causal structural breakout followed by a retest of the broken level.
    
    Causality Invariants:
    - Level defined by rolling N-period high/low prior to breakout.
    - Breakout occurred within recent window [1..10 bars ago].
    - Retest: current price tests the broken level from the favorable side.
    """
    def __init__(self, lookback: int = 20, max_retest_bars: int = 10):
        super().__init__("SETUP_BREAKOUT_RETEST", "Breakout of MTF structure followed by retest")
        self.parameters = {"lookback": lookback, "max_retest_bars": max_retest_bars}

    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        lookback = self.parameters["lookback"] * scale
        max_retest = self.parameters["max_retest_bars"] * scale
        highs = df["high"]
        lows = df["low"]
        closes = df["close"]

        ref_high = highs.rolling(lookback, min_periods=10).max().shift(1)
        ref_low = lows.rolling(lookback, min_periods=10).min().shift(1)

        # Breakout occurrences
        bull_break = (closes > ref_high) & (closes.shift(1) <= ref_high.shift(1))
        bear_break = (closes < ref_low) & (closes.shift(1) >= ref_low.shift(1))

        n = len(df)
        bull_retest = np.zeros(n, dtype=bool)
        bear_retest = np.zeros(n, dtype=bool)

        highs_arr = highs.to_numpy()
        lows_arr = lows.to_numpy()
        closes_arr = closes.to_numpy()
        ref_high_arr = ref_high.to_numpy()
        ref_low_arr = ref_low.to_numpy()
        bull_break_arr = bull_break.to_numpy()
        bear_break_arr = bear_break.to_numpy()

        last_bull_break_bar = -999
        broken_high_level = np.nan

        last_bear_break_bar = -999
        broken_low_level = np.nan

        for i in range(1, n):
            if bull_break_arr[i]:
                last_bull_break_bar = i
                broken_high_level = ref_high_arr[i]

            if bear_break_arr[i]:
                last_bear_break_bar = i
                broken_low_level = ref_low_arr[i]

            # Bullish retest: within max_retest bars after breakout, price dips to test broken level from above
            if (i > last_bull_break_bar) and (i - last_bull_break_bar <= max_retest):
                if lows_arr[i] <= broken_high_level and closes_arr[i] >= broken_high_level:
                    bull_retest[i] = True

            # Bearish retest: within max_retest bars after breakout, price rises to test broken level from below
            if (i > last_bear_break_bar) and (i - last_bear_break_bar <= max_retest):
                if highs_arr[i] >= broken_low_level and closes_arr[i] <= broken_low_level:
                    bear_retest[i] = True

        return pd.Series(bull_retest, index=df.index), pd.Series(bear_retest, index=df.index)


class SetupChochBosRetest(AbstractSetup):
    """
    SETUP_CHOCH_BOS_RETEST:
    Causal structural transition (Change of Character / Break of Structure)
    followed by a retest of the broken structural swing.
    """
    def __init__(self, pivot_lookback: int = 5, max_retest_bars: int = 15):
        super().__init__("SETUP_CHOCH_BOS_RETEST", "Structural ChoCH/BOS followed by retest")
        self.parameters = {"pivot_lookback": pivot_lookback, "max_retest_bars": max_retest_bars}

    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        p = self.parameters["pivot_lookback"] * scale
        max_retest = self.parameters["max_retest_bars"] * scale
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        closes = df["close"].to_numpy()
        n = len(df)

        bull_setup = np.zeros(n, dtype=bool)
        bear_setup = np.zeros(n, dtype=bool)

        # Causal swing pivots: a swing high at bar k is only confirmed at bar k+p
        last_swing_high = np.nan
        last_swing_low = np.nan
        last_bull_bos_bar = -999
        bos_high_level = np.nan
        last_bear_bos_bar = -999
        bos_low_level = np.nan

        for i in range(2 * p, n):
            # Check if bar i-p was a swing high
            cand_h = i - p
            if cand_h >= p:
                if (highs[cand_h] >= np.max(highs[cand_h - p: cand_h])) and \
                   (highs[cand_h] >= np.max(highs[cand_h + 1: i + 1])):
                    last_swing_high = highs[cand_h]

            # Check if bar i-p was a swing low
            cand_l = i - p
            if cand_l >= p:
                if (lows[cand_l] <= np.min(lows[cand_l - p: cand_l])) and \
                   (lows[cand_l] <= np.min(lows[cand_l + 1: i + 1])):
                    last_swing_low = lows[cand_l]

            # Detect ChoCH/BOS at bar i
            if np.isfinite(last_swing_high) and closes[i] > last_swing_high and closes[i-1] <= last_swing_high:
                last_bull_bos_bar = i
                bos_high_level = last_swing_high

            if np.isfinite(last_swing_low) and closes[i] < last_swing_low and closes[i-1] >= last_swing_low:
                last_bear_bos_bar = i
                bos_low_level = last_swing_low

            # Retest
            if (i > last_bull_bos_bar) and (i - last_bull_bos_bar <= max_retest):
                if lows[i] <= bos_high_level and closes[i] >= bos_high_level:
                    bull_setup[i] = True

            if (i > last_bear_bos_bar) and (i - last_bear_bos_bar <= max_retest):
                if highs[i] >= bos_low_level and closes[i] <= bos_low_level:
                    bear_setup[i] = True

        return pd.Series(bull_setup, index=df.index), pd.Series(bear_setup, index=df.index)


def register_all_setups(registry):
    registry.register(CanonicalSupertrendStochasticSetup())
    registry.register(PullbackSetup())
    registry.register(BreakoutSetup())
    # Phase C Setups
    fvg = SetupFVGTap()
    registry.register(fvg)
    fvg_alias = SetupFVGTap()
    fvg_alias.id = "FVG_TAP"
    registry.register(fvg_alias)

    sweep = SetupLiquiditySweep()
    registry.register(sweep)
    sweep_alias = SetupLiquiditySweep()
    sweep_alias.id = "LIQUIDITY_SWEEP"
    registry.register(sweep_alias)

    bo = SetupBreakoutRetest()
    registry.register(bo)
    bo_alias = SetupBreakoutRetest()
    bo_alias.id = "BREAKOUT_RETEST"
    registry.register(bo_alias)

    choch = SetupChochBosRetest()
    registry.register(choch)
    choch_alias = SetupChochBosRetest()
    choch_alias.id = "CHOCH_BOS_RETEST"
    registry.register(choch_alias)


# =====================================================================
# Phase E — Full Setup Taxonomy Expansion (13 new setups)
# =====================================================================

def _atr_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["close"].shift(1)).abs()
    tr3 = (df["low"] - df["close"].shift(1)).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(period, min_periods=3).mean()


class SetupOrderBlockRetest(AbstractSetup):
    """
    SETUP_ORDER_BLOCK_RETEST:
    Detects a significant institutional order block (last opposing candle before impulse)
    then waits for price to retest that zone from the favorable side.
    Bullish OB: last bearish candle before bullish impulse. Retest = price returns to OB range.
    """
    def __init__(self, impulse_bars: int = 3, max_age_bars: int = 40):
        super().__init__("SETUP_ORDER_BLOCK_RETEST", "Retest of last institutional order block zone")
        self.parameters = {"impulse_bars": impulse_bars, "max_age_bars": max_age_bars, "atr_period": 14}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        n = len(df)
        highs  = df["high"].to_numpy()
        lows   = df["low"].to_numpy()
        opens  = df["open"].to_numpy()
        closes = df["close"].to_numpy()
        atr_   = _atr_series(df, self.parameters["atr_period"] * scale).to_numpy()
        max_age = self.parameters["max_age_bars"] * scale
        ib = self.parameters["impulse_bars"]

        bull_setup = np.zeros(n, dtype=bool)
        bear_setup = np.zeros(n, dtype=bool)
        active_bull_obs = []  # (formed_idx, ob_low, ob_high)
        active_bear_obs = []

        for i in range(ib + 1, n):
            # Detect bullish OB at i-ib: ib consecutive bull closes from i-ib+1..i
            if all(closes[j] > opens[j] for j in range(i - ib + 1, i + 1)):
                # OB candle = i-ib (must be bearish)
                ob_idx = i - ib
                if closes[ob_idx] < opens[ob_idx]:
                    active_bull_obs.append((i, lows[ob_idx], highs[ob_idx]))

            # Detect bearish OB
            if all(closes[j] < opens[j] for j in range(i - ib + 1, i + 1)):
                ob_idx = i - ib
                if closes[ob_idx] > opens[ob_idx]:
                    active_bear_obs.append((i, lows[ob_idx], highs[ob_idx]))

            # Test retests
            surviving_bull = []
            for formed_idx, ob_low, ob_high in active_bull_obs:
                if (i - formed_idx) > max_age:
                    continue
                if lows[i] <= ob_high and closes[i] >= ob_low:
                    bull_setup[i] = True
                if closes[i] >= ob_low:
                    surviving_bull.append((formed_idx, ob_low, ob_high))
            active_bull_obs = surviving_bull

            surviving_bear = []
            for formed_idx, ob_low, ob_high in active_bear_obs:
                if (i - formed_idx) > max_age:
                    continue
                if highs[i] >= ob_low and closes[i] <= ob_high:
                    bear_setup[i] = True
                if closes[i] <= ob_high:
                    surviving_bear.append((formed_idx, ob_low, ob_high))
            active_bear_obs = surviving_bear

        return pd.Series(bull_setup, index=df.index), pd.Series(bear_setup, index=df.index)


class SetupFibonacciRetracement(AbstractSetup):
    """
    SETUP_FIBONACCI_RETRACEMENT:
    Price retraces to 38.2%, 50%, or 61.8% of the last identifiable swing move.
    Swing defined by rolling N-period high/low with strict backward-looking causality.
    """
    def __init__(self, swing_period: int = 20, fib_tolerance: float = 0.03):
        super().__init__("SETUP_FIBONACCI_RETRACEMENT", "Price at key Fibonacci retracement level")
        self.parameters = {"swing_period": swing_period, "fib_tolerance": fib_tolerance}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        sp = self.parameters["swing_period"] * scale
        tol = self.parameters["fib_tolerance"]
        fib_levels = [0.382, 0.500, 0.618]
        h = df["high"].rolling(sp, min_periods=5).max().shift(1)
        l = df["low"].rolling(sp, min_periods=5).min().shift(1)
        rng = (h - l).replace(0, np.nan)
        close = df["close"]
        bull_setup = pd.Series(False, index=df.index)
        bear_setup = pd.Series(False, index=df.index)
        for fib in fib_levels:
            bull_level = h - fib * rng
            bear_level = l + fib * rng
            bull_touch = ((close - bull_level).abs() / rng) < tol
            bear_touch = ((close - bear_level).abs() / rng) < tol
            bull_setup |= bull_touch.fillna(False)
            bear_setup |= bear_touch.fillna(False)
        return bull_setup, bear_setup


class SetupMAPullback(AbstractSetup):
    """
    SETUP_MA_PULLBACK:
    Price pulls back to within ATR tolerance of the fast EMA on the MTF.
    Bullish: price was above EMA, dips to touch, closes back above.
    Bearish: price was below EMA, rises to touch, closes back below.
    """
    def __init__(self, ema_period: int = 21, atr_mult: float = 0.5):
        super().__init__("SETUP_MA_PULLBACK", "Pullback to fast EMA zone")
        self.parameters = {"ema_period": ema_period, "atr_mult": atr_mult, "atr_period": 14}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        ep = self.parameters["ema_period"] * scale
        ema = df["close"].ewm(span=ep, adjust=False).mean()
        atr_ = _atr_series(df, self.parameters["atr_period"] * scale)
        band = self.parameters["atr_mult"] * atr_
        # Bullish: low dips to [ema-band, ema+band] AND close > ema
        bull = ((df["low"] <= ema + band) & (df["low"] >= ema - band) & (df["close"] > ema))
        # Bearish: high rises to band around ema AND close < ema
        bear = ((df["high"] >= ema - band) & (df["high"] <= ema + band) & (df["close"] < ema))
        return bull.fillna(False), bear.fillna(False)


class SetupVWAPMeanReversion(AbstractSetup):
    """
    SETUP_VWAP_MEAN_REVERSION:
    Price has deviated more than 1σ from rolling VWAP and is now returning.
    Bullish: price was below VWAP by > 1σ (oversold) and is now recovering above VWAP.
    Bearish: price was above VWAP by > 1σ (overbought) and is now falling below VWAP.
    """
    def __init__(self, vwap_period: int = 20, sigma_min: float = 1.0):
        super().__init__("SETUP_VWAP_MEAN_REVERSION", "Return from VWAP σ-band deviation")
        self.parameters = {"vwap_period": vwap_period, "sigma_min": sigma_min}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        p = self.parameters["vwap_period"] * scale
        tp = (df["high"] + df["low"] + df["close"]) / 3
        vol = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)
        vwap  = (tp * vol).rolling(p, min_periods=5).sum() / vol.rolling(p, min_periods=5).sum()
        sigma = (df["close"] - vwap).rolling(p, min_periods=5).std().fillna(0)
        dev = (df["close"] - vwap) / sigma.replace(0, np.nan)
        # Bullish: was oversold (dev.shift < -sigma_min) and now recovering (close > vwap)
        bull = ((dev.shift(1) < -self.parameters["sigma_min"]) & (df["close"] > vwap)).fillna(False)
        bear = ((dev.shift(1) > self.parameters["sigma_min"]) & (df["close"] < vwap)).fillna(False)
        return bull, bear


class SetupFlagPennant(AbstractSetup):
    """
    SETUP_FLAG_PENNANT:
    Identifies a 'flag' structure: strong impulse move followed by counter-trend consolidation.
    Bull flag: N-bar range contraction after bullish impulse.
    Bear flag: N-bar range contraction after bearish impulse.
    """
    def __init__(self, impulse_bars: int = 5, flag_bars: int = 10):
        super().__init__("SETUP_FLAG_PENNANT", "Flag/Pennant consolidation after impulse")
        self.parameters = {"impulse_bars": impulse_bars, "flag_bars": flag_bars, "atr_period": 14}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        ib = self.parameters["impulse_bars"] * scale
        fb = self.parameters["flag_bars"] * scale
        c = df["close"]
        atr_ = _atr_series(df, self.parameters["atr_period"] * scale)
        # Impulse: ib-bar return > 2 ATR
        ret = c - c.shift(ib)
        # Flag: recent fb-bar range < 0.6 × ib-bar return magnitude
        flag_range = df["high"].rolling(fb, min_periods=3).max() - df["low"].rolling(fb, min_periods=3).min()
        bull_impulse = ret.shift(fb) > 2 * atr_.shift(fb)
        bull_flag    = flag_range < (ret.shift(fb) * 0.6)
        bear_impulse = ret.shift(fb) < -2 * atr_.shift(fb)
        bear_flag    = flag_range < (ret.shift(fb).abs() * 0.6)
        return (bull_impulse & bull_flag).fillna(False), (bear_impulse & bear_flag).fillna(False)


class SetupInsideBar(AbstractSetup):
    """
    SETUP_INSIDE_BAR:
    Current bar range fully inside prior bar range (volatility compression signal).
    Bullish context: inside bar forming in an uptrend (above EMA).
    Bearish context: inside bar forming in a downtrend (below EMA).
    """
    def __init__(self, ema_period: int = 50):
        super().__init__("SETUP_INSIDE_BAR", "Inside bar volatility compression")
        self.parameters = {"ema_period": ema_period}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        ep = self.parameters["ema_period"] * scale
        ema = df["close"].ewm(span=ep, adjust=False).mean()
        inside = (df["high"] < df["high"].shift(1)) & (df["low"] > df["low"].shift(1))
        bull = (inside & (df["close"] > ema)).fillna(False)
        bear = (inside & (df["close"] < ema)).fillna(False)
        return bull, bear


class SetupSqueeze(AbstractSetup):
    """
    SETUP_SQUEEZE:
    Bollinger Bands inside Keltner Channel = momentum squeeze (low volatility).
    This setup fires when the SQUEEZE IS ACTIVE (not when it releases) — it marks
    the compression period before the expected expansion.
    """
    def __init__(self, bb_period: int = 20, bb_std: float = 2.0, kc_mult: float = 1.5):
        super().__init__("SETUP_SQUEEZE", "Active Bollinger/Keltner compression squeeze")
        self.parameters = {"bb_period": bb_period, "bb_std": bb_std, "kc_mult": kc_mult, "atr_period": 20}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        bp = self.parameters["bb_period"] * scale
        c  = df["close"]
        bb_mid   = c.rolling(bp, min_periods=5).mean()
        bb_upper = bb_mid + self.parameters["bb_std"] * c.rolling(bp, min_periods=5).std()
        bb_lower = bb_mid - self.parameters["bb_std"] * c.rolling(bp, min_periods=5).std()
        atr_ = _atr_series(df, self.parameters["atr_period"] * scale)
        kc_upper = bb_mid + self.parameters["kc_mult"] * atr_
        kc_lower = bb_mid - self.parameters["kc_mult"] * atr_
        squeeze_on = (bb_upper < kc_upper) & (bb_lower > kc_lower)
        ema50 = c.ewm(span=50 * scale, adjust=False).mean()
        bull = (squeeze_on & (c > ema50)).fillna(False)
        bear = (squeeze_on & (c < ema50)).fillna(False)
        return bull, bear


class SetupStochasticCross(AbstractSetup):
    """
    SETUP_STOCHASTIC_CROSS:
    Stochastic K crosses D in the extreme zone on the MTF.
    Bullish: K crosses above D while K < 30 (oversold zone).
    Bearish: K crosses below D while K > 70 (overbought zone).
    """
    def __init__(self, k_period: int = 14, smooth: int = 3, os_level: float = 30, ob_level: float = 70):
        super().__init__("SETUP_STOCHASTIC_CROSS", "Stochastic K/D crossover in extreme zone")
        self.parameters = {"k_period": k_period, "smooth": smooth, "os_level": os_level, "ob_level": ob_level}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        kp = self.parameters["k_period"] * scale
        h  = df["high"].rolling(kp, min_periods=3).max()
        l  = df["low"].rolling(kp, min_periods=3).min()
        k  = (100 * (df["close"] - l) / (h - l).replace(0, np.nan)).rolling(self.parameters["smooth"]).mean().fillna(50)
        d  = k.rolling(self.parameters["smooth"]).mean()
        bull_cross = (k > d) & (k.shift(1) <= d.shift(1)) & (k < self.parameters["ob_level"])
        bear_cross = (k < d) & (k.shift(1) >= d.shift(1)) & (k > self.parameters["os_level"])
        return bull_cross.fillna(False), bear_cross.fillna(False)


class SetupRSIDivergence(AbstractSetup):
    """
    SETUP_RSI_DIVERGENCE:
    Classic RSI divergence: price makes a new high/low but RSI does not.
    Bullish divergence: price makes lower low, RSI makes higher low.
    Bearish divergence: price makes higher high, RSI makes lower high.
    Uses N-bar lookback for prior pivot comparison.
    """
    def __init__(self, lookback: int = 20, rsi_period: int = 14):
        super().__init__("SETUP_RSI_DIVERGENCE", "Classic RSI divergence setup")
        self.parameters = {"lookback": lookback, "rsi_period": rsi_period}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        lb = self.parameters["lookback"] * scale
        rp = self.parameters["rsi_period"] * scale
        c = df["close"]
        delta = c.diff()
        gain = delta.where(delta > 0, 0).rolling(rp, min_periods=3).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(rp, min_periods=3).mean()
        rsi = 100 - (100 / (1 + gain / loss.replace(0, np.nan))).fillna(50)
        # Bullish divergence: price lower low, RSI higher low
        price_ll = c < c.rolling(lb, min_periods=5).min().shift(1)
        rsi_hl   = rsi > rsi.rolling(lb, min_periods=5).min().shift(1)
        bull = (price_ll & rsi_hl).fillna(False)
        # Bearish divergence: price higher high, RSI lower high
        price_hh = c > c.rolling(lb, min_periods=5).max().shift(1)
        rsi_lh   = rsi < rsi.rolling(lb, min_periods=5).max().shift(1)
        bear = (price_hh & rsi_lh).fillna(False)
        return bull, bear


class SetupMACDHistogramReversal(AbstractSetup):
    """
    SETUP_MACD_HISTOGRAM_REVERSAL:
    MACD histogram reversing direction (turning from red to green or vice versa).
    Bullish: histogram was negative and is now increasing (turning up from below zero).
    Bearish: histogram was positive and is now decreasing (turning down from above zero).
    """
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("SETUP_MACD_HISTOGRAM_REVERSAL", "MACD histogram direction reversal")
        self.parameters = {"fast": fast, "slow": slow, "signal": signal}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        c = df["close"]
        macd = (c.ewm(span=self.parameters["fast"] * scale, adjust=False).mean() -
                c.ewm(span=self.parameters["slow"] * scale, adjust=False).mean())
        sig  = macd.ewm(span=self.parameters["signal"], adjust=False).mean()
        hist = macd - sig
        # Bullish: histogram was negative and is now turning up (first bar of reversal)
        bull = ((hist < 0) & (hist > hist.shift(1)) & (hist.shift(1) < hist.shift(2))).fillna(False)
        bear = ((hist > 0) & (hist < hist.shift(1)) & (hist.shift(1) > hist.shift(2))).fillna(False)
        return bull, bear


class SetupLiquidityGrabReversal(AbstractSetup):
    """
    SETUP_LIQUIDITY_GRAB_REVERSAL:
    Single candle sweeps a prior swing H/L then immediately closes back inside.
    More aggressive version of the existing SetupLiquiditySweep.
    Bullish: wick breaks below N-bar low but candle closes back above.
    Bearish: wick breaks above N-bar high but candle closes back below.
    """
    def __init__(self, lookback: int = 15):
        super().__init__("SETUP_LIQUIDITY_GRAB_REVERSAL", "Intra-candle liquidity grab + immediate reversal")
        self.parameters = {"lookback": lookback}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        lb = self.parameters["lookback"] * scale
        ref_h = df["high"].rolling(lb, min_periods=5).max().shift(1)
        ref_l = df["low"].rolling(lb, min_periods=5).min().shift(1)
        # Bullish grab: low pierces below ref_l, but close is ABOVE ref_l AND candle is bullish
        bull = (df["low"] < ref_l) & (df["close"] > ref_l) & (df["close"] > df["open"])
        # Bearish grab: high pierces above ref_h, but close is BELOW ref_h AND candle is bearish
        bear = (df["high"] > ref_h) & (df["close"] < ref_h) & (df["close"] < df["open"])
        return bull.fillna(False), bear.fillna(False)


class SetupSRFlip(AbstractSetup):
    """
    SETUP_SR_FLIP:
    Prior resistance becomes support (bullish) or prior support becomes resistance (bearish).
    Detects a breakout followed by a retest that holds — the S/R flip confirmation.
    Uses rolling N-bar H/L as the reference structural level.
    """
    def __init__(self, lookback: int = 20, max_retest_bars: int = 12, atr_tolerance: float = 0.3):
        super().__init__("SETUP_SR_FLIP", "Support/resistance level flip and retest")
        self.parameters = {"lookback": lookback, "max_retest_bars": max_retest_bars,
                           "atr_tolerance": atr_tolerance, "atr_period": 14}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        lb  = self.parameters["lookback"] * scale
        mrt = self.parameters["max_retest_bars"] * scale
        tol = self.parameters["atr_tolerance"]
        atr_  = _atr_series(df, self.parameters["atr_period"] * scale)
        h_ref = df["high"].rolling(lb, min_periods=5).max().shift(1)
        l_ref = df["low"].rolling(lb, min_periods=5).min().shift(1)
        close = df["close"]
        # Breakout events
        bull_bo = (close > h_ref) & (close.shift(1) <= h_ref.shift(1))
        bear_bo = (close < l_ref) & (close.shift(1) >= l_ref.shift(1))
        n = len(df)
        bull_arr  = np.zeros(n, dtype=bool)
        bear_arr  = np.zeros(n, dtype=bool)
        c_arr     = close.to_numpy()
        l_arr     = df["low"].to_numpy()
        h_arr     = df["high"].to_numpy()
        atr_arr   = atr_.to_numpy()
        href_arr  = h_ref.to_numpy()
        lref_arr  = l_ref.to_numpy()
        bbo_arr   = bull_bo.to_numpy()
        bbr_arr   = bear_bo.to_numpy()
        last_bull_bo = -999; bull_lvl = np.nan
        last_bear_bo = -999; bear_lvl = np.nan
        for i in range(1, n):
            if bbo_arr[i]:
                last_bull_bo = i; bull_lvl = href_arr[i]
            if bbr_arr[i]:
                last_bear_bo = i; bear_lvl = lref_arr[i]
            # Bullish S/R flip: price returns to former resistance (now support)
            if (i > last_bull_bo) and (i - last_bull_bo <= mrt) and np.isfinite(bull_lvl):
                if l_arr[i] <= bull_lvl + tol * atr_arr[i] and c_arr[i] >= bull_lvl:
                    bull_arr[i] = True
            # Bearish S/R flip: price returns to former support (now resistance)
            if (i > last_bear_bo) and (i - last_bear_bo <= mrt) and np.isfinite(bear_lvl):
                if h_arr[i] >= bear_lvl - tol * atr_arr[i] and c_arr[i] <= bear_lvl:
                    bear_arr[i] = True
        return pd.Series(bull_arr, index=df.index), pd.Series(bear_arr, index=df.index)


class SetupVolumeClimax(AbstractSetup):
    """
    SETUP_VOLUME_CLIMAX:
    Extreme volume candle (> 2.5x 20-bar avg) on a directional close,
    signaling potential exhaustion and reversal setup.
    Bullish climax (sell exhaustion): high volume bearish candle — potential bounce.
    Bearish climax (buy exhaustion): high volume bullish candle — potential reversal.
    Note: This is an EXHAUSTION setup — direction is CONTRA to the climax candle.
    """
    def __init__(self, vol_mult: float = 2.5, vol_period: int = 20):
        super().__init__("SETUP_VOLUME_CLIMAX", "Extreme volume exhaustion candle")
        self.parameters = {"vol_mult": vol_mult, "vol_period": vol_period}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        if "volume" not in df.columns:
            return pd.Series(False, index=df.index), pd.Series(False, index=df.index)
        vp  = self.parameters["vol_period"] * scale
        vol = df["volume"]
        avg_vol = vol.rolling(vp, min_periods=5).mean().shift(1)
        high_vol = vol > self.parameters["vol_mult"] * avg_vol
        candle_range = (df["high"] - df["low"]).replace(0, np.nan)
        close_pct = (df["close"] - df["low"]) / candle_range
        # Bearish climax candle (close in lower 30%) → potential bullish reversal setup
        bull = (high_vol & (close_pct < 0.3)).fillna(False)
        # Bullish climax candle (close in upper 70%) → potential bearish reversal setup
        bear = (high_vol & (close_pct > 0.7)).fillna(False)
        return bull, bear


def register_all_setups(registry):
    # Phase A/B/C existing setups
    registry.register(CanonicalSupertrendStochasticSetup())
    registry.register(PullbackSetup())
    registry.register(BreakoutSetup())
    fvg = SetupFVGTap()
    registry.register(fvg)
    fvg_alias = SetupFVGTap(); fvg_alias.id = "FVG_TAP"
    registry.register(fvg_alias)
    sweep = SetupLiquiditySweep()
    registry.register(sweep)
    sweep_alias = SetupLiquiditySweep(); sweep_alias.id = "LIQUIDITY_SWEEP"
    registry.register(sweep_alias)
    bo = SetupBreakoutRetest()
    registry.register(bo)
    bo_alias = SetupBreakoutRetest(); bo_alias.id = "BREAKOUT_RETEST"
    registry.register(bo_alias)
    choch = SetupChochBosRetest()
    registry.register(choch)
    choch_alias = SetupChochBosRetest(); choch_alias.id = "CHOCH_BOS_RETEST"
    registry.register(choch_alias)
    # Phase E new setups
    for cls in [
        SetupOrderBlockRetest,
        SetupFibonacciRetracement,
        SetupMAPullback,
        SetupVWAPMeanReversion,
        SetupFlagPennant,
        SetupInsideBar,
        SetupSqueeze,
        SetupStochasticCross,
        SetupRSIDivergence,
        SetupMACDHistogramReversal,
        SetupLiquidityGrabReversal,
        SetupSRFlip,
        SetupVolumeClimax,
    ]:
        registry.register(cls())
