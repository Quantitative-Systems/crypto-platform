"""
QCP HTF Bias Families.
Implements the Bias components for the strategy grammar.
All biases are strictly causal and point-in-time.
"""

from typing import Tuple
import pandas as pd
import numpy as np

from research.grammar_components import AbstractBias
from strategy_candidate_v2.fast_indicators import supertrend_numpy, stochastic_numpy
from research.regime_engine import RegimeEngine, RegimeState

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

class CanonicalSupertrendStochasticBias(AbstractBias):
    def __init__(self):
        super().__init__("CANONICAL_SUPERTREND_STOCHASTIC", "Supertrend Direction + Stochastic Pullback")
        self.parameters = {"st_len": 6, "st_fac": 5.0, "stoch_k": 25, "stoch_ks": 5, "stoch_ds": 3}

    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        highs, lows, closes = df["high"].values, df["low"].values, df["close"].values
        st_val, st_dir = supertrend_numpy(highs, lows, closes, 
                                          atr_length=self.parameters["st_len"] * scale, 
                                          factor=self.parameters["st_fac"])
        k, d = stochastic_numpy(highs, lows, closes, 
                                k_length=self.parameters["stoch_k"] * scale, 
                                k_smooth=self.parameters["stoch_ks"], 
                                d_smooth=self.parameters["stoch_ds"])
        
        st_series = pd.Series(st_dir, index=df.index)
        k_series = pd.Series(k, index=df.index)
        
        bull_st = st_series == 1
        bull_pullback = k_series <= 40
        
        bear_st = st_series == -1
        bear_pullback = k_series >= 60
        
        return (bull_st & bull_pullback), (bear_st & bear_pullback)

class TrendMAAlignmentBias(AbstractBias):
    def __init__(self):
        super().__init__("TREND_MA_ALIGNMENT", "Fast EMA > Slow EMA")
        
    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        fast = _ema(df["close"], 20 * scale)
        slow = _ema(df["close"], 50 * scale)
        return (fast > slow), (fast < slow)

class StructHHHLBias(AbstractBias):
    def __init__(self):
        super().__init__("STRUCT_HH_HL", "Structural Higher Highs and Higher Lows")
        
    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        roll_high = df["high"].rolling(20 * scale).max()
        roll_low = df["low"].rolling(20 * scale).min()
        bull_ms = (roll_high > roll_high.shift(20 * scale)) & (roll_low > roll_low.shift(20 * scale))
        bear_ms = (roll_high < roll_high.shift(20 * scale)) & (roll_low < roll_low.shift(20 * scale))
        return bull_ms, bear_ms

class MomRSIRegimeBias(AbstractBias):
    def __init__(self):
        super().__init__("MOM_RSI_REGIME", "RSI above/below 50")
        
    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        rsi = _rsi(df["close"], 14 * scale)
        return (rsi > 50), (rsi < 50)

class NeutralBias(AbstractBias):
    def __init__(self):
        super().__init__("NEUTRAL", "Neutral Bias, allows all setups")
        self.neutral_state = True
        
    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        return pd.Series(True, index=df.index), pd.Series(True, index=df.index)


# =====================================================================
# Phase C Regime Biases
# =====================================================================

class RegimeTrendBias(AbstractBias):
    """
    REGIME_TREND:
    Requires causal TREND_UP / TREND_DOWN or expanding directional state from RegimeEngine.
    """
    def __init__(self):
        super().__init__("REGIME_TREND", "Causal Trend/Expansion Regime Bias")
        self.engine = RegimeEngine()

    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        out = self.engine.compute(df)
        reg = out.regime
        align = out.measurements["ma_alignment"]
        
        bull_bias = (reg == RegimeState.TREND_UP.value) | ((reg == RegimeState.EXPANSION.value) & (align > 0))
        bear_bias = (reg == RegimeState.TREND_DOWN.value) | ((reg == RegimeState.EXPANSION.value) & (align < 0))
        return bull_bias.fillna(False), bear_bias.fillna(False)


class RegimeRangeBias(AbstractBias):
    """
    REGIME_RANGE:
    Requires RANGE or NORMAL/LOW_VOL regime for mean reversion / sweep strategies.
    """
    def __init__(self):
        super().__init__("REGIME_RANGE", "Causal Range/Consolidation Regime Bias")
        self.engine = RegimeEngine()

    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        out = self.engine.compute(df)
        reg = out.regime
        is_range = reg.isin([RegimeState.RANGE.value, RegimeState.NORMAL_VOL.value, RegimeState.LOW_VOL.value])
        return is_range.fillna(False), is_range.fillna(False)


class RegimeAnyBias(AbstractBias):
    """
    REGIME (REGIME_ANY):
    Permits setups in any verified non-unknown market regime.
    """
    def __init__(self, component_id: str = "REGIME"):
        super().__init__(component_id, "Causal Valid Regime Layer")
        self.engine = RegimeEngine()

    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        out = self.engine.compute(df)
        valid = out.regime != RegimeState.UNKNOWN.value
        return valid.fillna(False), valid.fillna(False)


def register_all_biases(registry):
    registry.register(CanonicalSupertrendStochasticBias())
    registry.register(TrendMAAlignmentBias())
    registry.register(StructHHHLBias())
    registry.register(MomRSIRegimeBias())
    registry.register(NeutralBias())
    # Phase C Regime Biases
    registry.register(RegimeTrendBias())
    registry.register(RegimeRangeBias())
    registry.register(RegimeAnyBias("REGIME"))
    registry.register(RegimeAnyBias("REGIME_ANY"))


# =====================================================================
# Phase E — Full Bias Taxonomy Expansion
# =====================================================================

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["close"].shift(1)).abs()
    tr3 = (df["low"] - df["close"].shift(1)).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(period, min_periods=3).mean()


# ── Category A: Trend-Following Biases ───────────────────────────────────────

class IchimokuCloudBias(AbstractBias):
    """
    BIAS_ICHIMOKU: Price position relative to Ichimoku Kumo cloud.
    Bull bias: close above cloud top (Senkou A > Senkou B, or close > max(A,B)).
    Bear bias: close below cloud bottom.
    Tenkan/Kijun cross adds confirmation layer.
    All signals strictly forward-shifted by cloud_shift to ensure causality.
    """
    def __init__(self):
        super().__init__("BIAS_ICHIMOKU", "Ichimoku Kumo Cloud Position")
        self.parameters = {
            "tenkan_period": 9,
            "kijun_period": 26,
            "senkou_b_period": 52,
            "cloud_shift": 26,
        }

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        h = df["high"]
        l = df["low"]
        c = df["close"]
        tp = self.parameters["tenkan_period"] * scale
        kp = self.parameters["kijun_period"] * scale
        sp = self.parameters["senkou_b_period"] * scale
        shift = self.parameters["cloud_shift"] * scale

        tenkan = (h.rolling(tp).max() + l.rolling(tp).min()) / 2
        kijun  = (h.rolling(kp).max() + l.rolling(kp).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(shift)
        senkou_b = ((h.rolling(sp).max() + l.rolling(sp).min()) / 2).shift(shift)

        cloud_top    = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
        cloud_bottom = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)

        bull = (c > cloud_top).fillna(False)
        bear = (c < cloud_bottom).fillna(False)
        return bull, bear


class MACDRegimeBias(AbstractBias):
    """
    BIAS_MACD_REGIME: MACD line sign + histogram direction.
    Bull bias: MACD > 0 AND histogram (MACD-signal) turning positive.
    Bear bias: MACD < 0 AND histogram turning negative.
    """
    def __init__(self):
        super().__init__("BIAS_MACD_REGIME", "MACD Sign + Histogram Direction")
        self.parameters = {"fast": 12, "slow": 26, "signal": 9}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        c = df["close"]
        fast = c.ewm(span=self.parameters["fast"] * scale, adjust=False).mean()
        slow = c.ewm(span=self.parameters["slow"] * scale, adjust=False).mean()
        macd = fast - slow
        sig  = macd.ewm(span=self.parameters["signal"], adjust=False).mean()
        hist = macd - sig

        bull = ((macd > 0) & (hist > hist.shift(1))).fillna(False)
        bear = ((macd < 0) & (hist < hist.shift(1))).fillna(False)
        return bull, bear


class ADXDirectionalBias(AbstractBias):
    """
    BIAS_ADX_DIRECTIONAL: ADX strength + +DI/-DI winner.
    Bull bias: ADX > 20 AND +DI > -DI.
    Bear bias: ADX > 20 AND -DI > +DI.
    Threshold 20 is a well-established institutional minimum trend strength indicator.
    """
    def __init__(self):
        super().__init__("BIAS_ADX_DIRECTIONAL", "ADX Directional Strength")
        self.parameters = {"period": 14, "adx_min": 20}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        period = self.parameters["period"] * scale
        h, l, c = df["high"], df["low"], df["close"]
        up   = h - h.shift(1)
        down = l.shift(1) - l
        plus_dm  = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
        minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
        tr1 = h - l
        tr2 = (h - c.shift(1)).abs()
        tr3 = (l - c.shift(1)).abs()
        tr   = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_ = tr.ewm(alpha=1.0/period, adjust=False).mean().replace(0, np.nan)
        plus_di  = 100 * (plus_dm.ewm(alpha=1.0/period, adjust=False).mean() / atr_)
        minus_di = 100 * (minus_dm.ewm(alpha=1.0/period, adjust=False).mean() / atr_)
        dx  = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.ewm(alpha=1.0/period, adjust=False).mean().fillna(0)
        min_adx = self.parameters["adx_min"]
        bull = ((adx > min_adx) & (plus_di > minus_di)).fillna(False)
        bear = ((adx > min_adx) & (minus_di > plus_di)).fillna(False)
        return bull, bear


# ── Category B: Momentum Biases ───────────────────────────────────────────────

class StochasticRegimeBias(AbstractBias):
    """
    BIAS_STOCHASTIC_REGIME: Stochastic K line position.
    Bull bias: K > 50 (momentum above midpoint).
    Bear bias: K < 50.
    """
    def __init__(self):
        super().__init__("BIAS_STOCHASTIC_REGIME", "Stochastic K Mid-Line Regime")
        self.parameters = {"k_period": 14, "smooth": 3}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        kp = self.parameters["k_period"] * scale
        h  = df["high"].rolling(kp, min_periods=3).max()
        l  = df["low"].rolling(kp, min_periods=3).min()
        k  = 100 * (df["close"] - l) / (h - l).replace(0, np.nan)
        k  = k.rolling(self.parameters["smooth"]).mean().fillna(50)
        bull = (k > 50)
        bear = (k < 50)
        return bull.fillna(False), bear.fillna(False)


class SqueezeDirectionBias(AbstractBias):
    """
    BIAS_SQUEEZE_DIRECTION: Bollinger Band + Keltner Channel squeeze breakout direction.
    Bull: BB wider than KC (squeeze released) AND close > BB mid.
    Bear: BB wider than KC AND close < BB mid.
    Squeeze present when BB is inside KC.
    """
    def __init__(self):
        super().__init__("BIAS_SQUEEZE_DIRECTION", "BB/KC Squeeze Breakout Direction")
        self.parameters = {"bb_period": 20, "bb_std": 2.0, "kc_period": 20, "kc_mult": 1.5}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        bp = self.parameters["bb_period"] * scale
        kp = self.parameters["kc_period"] * scale
        c  = df["close"]
        bb_mid = c.rolling(bp, min_periods=5).mean()
        bb_std = c.rolling(bp, min_periods=5).std()
        bb_upper = bb_mid + self.parameters["bb_std"] * bb_std
        bb_lower = bb_mid - self.parameters["bb_std"] * bb_std
        atr_ = _atr(df, kp)
        kc_upper = bb_mid + self.parameters["kc_mult"] * atr_
        kc_lower = bb_mid - self.parameters["kc_mult"] * atr_
        # Squeeze released: BB wider than KC
        squeeze_off = (bb_upper > kc_upper) & (bb_lower < kc_lower)
        bull = (squeeze_off & (c > bb_mid)).fillna(False)
        bear = (squeeze_off & (c < bb_mid)).fillna(False)
        return bull, bear


class MomentumSlopeBias(AbstractBias):
    """
    BIAS_MOMENTUM_SLOPE: Rate-of-change direction over multiple periods.
    Bull: ROC(close, period) > 0 (positive slope).
    Bear: ROC(close, period) < 0.
    """
    def __init__(self):
        super().__init__("BIAS_MOMENTUM_SLOPE", "Rate of Change Slope Direction")
        self.parameters = {"roc_period": 14}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        period = self.parameters["roc_period"] * scale
        roc = df["close"].pct_change(period)
        bull = (roc > 0).fillna(False)
        bear = (roc < 0).fillna(False)
        return bull, bear


# ── Category C: Price Action / Structure Biases ──────────────────────────────

class VWAPPositionBias(AbstractBias):
    """
    BIAS_VWAP_POSITION: Rolling VWAP (volume-weighted average price) position.
    Bull bias: close > rolling VWAP.
    Bear bias: close < rolling VWAP.
    Uses a rolling 20-bar VWAP (causal, backward-looking).
    """
    def __init__(self):
        super().__init__("BIAS_VWAP_POSITION", "Rolling VWAP Position")
        self.parameters = {"period": 20}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        period = self.parameters["period"] * scale
        tp = (df["high"] + df["low"] + df["close"]) / 3
        vol = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)
        vwap = (tp * vol).rolling(period, min_periods=5).sum() / vol.rolling(period, min_periods=5).sum()
        bull = (df["close"] > vwap).fillna(False)
        bear = (df["close"] < vwap).fillna(False)
        return bull, bear


class BreakOfStructureBias(AbstractBias):
    """
    BIAS_BOS: Direction of the most recent confirmed Break of Structure.
    A BOS is confirmed when price closes beyond the most recent confirmed swing H/L.
    Bull bias: last BOS was bullish (close above prior swing high).
    Bear bias: last BOS was bearish (close below prior swing low).
    Persists until overridden by a BOS in the opposite direction.
    """
    def __init__(self, pivot_lookback: int = 5):
        super().__init__("BIAS_BOS", "Break of Structure Directional Bias")
        self.parameters = {"pivot_lookback": pivot_lookback}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        p = self.parameters["pivot_lookback"] * scale
        n = len(df)
        highs  = df["high"].to_numpy()
        lows   = df["low"].to_numpy()
        closes = df["close"].to_numpy()
        bull = np.zeros(n, dtype=bool)
        bear = np.zeros(n, dtype=bool)
        last_swing_h = np.nan
        last_swing_l = np.nan
        bos_direction = 0  # 0=unknown, 1=bull, -1=bear
        for i in range(2 * p, n):
            cand = i - p
            if cand >= p:
                if highs[cand] >= np.max(highs[max(0, cand-p):cand]) and \
                   highs[cand] >= np.max(highs[cand+1:i+1]):
                    last_swing_h = highs[cand]
                if lows[cand] <= np.min(lows[max(0, cand-p):cand]) and \
                   lows[cand] <= np.min(lows[cand+1:i+1]):
                    last_swing_l = lows[cand]
            if np.isfinite(last_swing_h) and closes[i] > last_swing_h:
                bos_direction = 1
            if np.isfinite(last_swing_l) and closes[i] < last_swing_l:
                bos_direction = -1
            if bos_direction == 1:
                bull[i] = True
            elif bos_direction == -1:
                bear[i] = True
        return pd.Series(bull, index=df.index), pd.Series(bear, index=df.index)


class ChangeOfCharacterBias(AbstractBias):
    """
    BIAS_CHOCH: Change of Character — the first opposing BOS in a trending structure.
    A CHoCH signals a regime shift. After a CHoCH the bias switches direction.
    Implementation: identical to BOS but requires a directional flip (not just continuation).
    Bull CHoCH: In a downtrend, close breaks above most recent swing high.
    Bear CHoCH: In an uptrend, close breaks below most recent swing low.
    """
    def __init__(self, pivot_lookback: int = 5):
        super().__init__("BIAS_CHOCH", "Change of Character Regime Shift Bias")
        self.parameters = {"pivot_lookback": pivot_lookback}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        p = self.parameters["pivot_lookback"] * scale
        n = len(df)
        highs  = df["high"].to_numpy()
        lows   = df["low"].to_numpy()
        closes = df["close"].to_numpy()
        bull = np.zeros(n, dtype=bool)
        bear = np.zeros(n, dtype=bool)
        last_swing_h = np.nan
        last_swing_l = np.nan
        prev_direction = 0
        cur_direction  = 0
        for i in range(2 * p, n):
            cand = i - p
            if cand >= p:
                if highs[cand] >= np.max(highs[max(0, cand-p):cand]) and \
                   highs[cand] >= np.max(highs[cand+1:i+1]):
                    last_swing_h = highs[cand]
                if lows[cand] <= np.min(lows[max(0, cand-p):cand]) and \
                   lows[cand] <= np.min(lows[cand+1:i+1]):
                    last_swing_l = lows[cand]
            if np.isfinite(last_swing_h) and closes[i] > last_swing_h:
                prev_direction = cur_direction
                cur_direction  = 1
            if np.isfinite(last_swing_l) and closes[i] < last_swing_l:
                prev_direction = cur_direction
                cur_direction  = -1
            # CHoCH only on directional flip
            if cur_direction == 1 and prev_direction == -1:
                bull[i] = True
            if cur_direction == -1 and prev_direction == 1:
                bear[i] = True
        return pd.Series(bull, index=df.index), pd.Series(bear, index=df.index)


# ── Category D: SMC Biases ────────────────────────────────────────────────────

class OrderBlockBias(AbstractBias):
    """
    BIAS_ORDER_BLOCK: Last significant order block direction defines institutional bias.
    Bullish OB: The last bearish candle before a bullish impulse (3-bar expansion up).
    Bearish OB: The last bullish candle before a bearish impulse (3-bar expansion down).
    Bias = direction of the most recently formed OB.
    """
    def __init__(self, impulse_atr_mult: float = 1.5):
        super().__init__("BIAS_ORDER_BLOCK", "Last Order Block Directional Bias")
        self.parameters = {"impulse_atr_mult": impulse_atr_mult, "atr_period": 14}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        n = len(df)
        closes = df["close"].to_numpy()
        opens  = df["open"].to_numpy()
        highs  = df["high"].to_numpy()
        lows   = df["low"].to_numpy()
        atr_   = _atr(df, self.parameters["atr_period"] * scale).to_numpy()
        mult   = self.parameters["impulse_atr_mult"]
        bull = np.zeros(n, dtype=bool)
        bear = np.zeros(n, dtype=bool)
        ob_direction = 0
        for i in range(3, n):
            body_prev = abs(closes[i-1] - opens[i-1])
            # Bullish impulse: 3-bar rising with last body > mult*atr
            if closes[i] > closes[i-1] > closes[i-2] and body_prev > mult * atr_[i-1]:
                ob_direction = 1  # bullish OB formed
            # Bearish impulse: 3-bar falling
            elif closes[i] < closes[i-1] < closes[i-2] and body_prev > mult * atr_[i-1]:
                ob_direction = -1
            if ob_direction == 1:
                bull[i] = True
            elif ob_direction == -1:
                bear[i] = True
        return pd.Series(bull, index=df.index), pd.Series(bear, index=df.index)


class FVGDirectionalBias(AbstractBias):
    """
    BIAS_FVG_DIRECTION: Direction of the most recently formed Fair Value Gap.
    Bullish FVG (gap up): low[i] > high[i-2] → bull bias.
    Bearish FVG (gap down): high[i] < low[i-2] → bear bias.
    Persists until a new FVG forms in the opposite direction.
    """
    def __init__(self, displacement_atr_mult: float = 1.0, atr_period: int = 14):
        super().__init__("BIAS_FVG_DIRECTION", "Most Recent FVG Directional Bias")
        self.parameters = {"displacement_atr_mult": displacement_atr_mult, "atr_period": atr_period}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        n = len(df)
        highs  = df["high"].to_numpy()
        lows   = df["low"].to_numpy()
        opens  = df["open"].to_numpy()
        closes = df["close"].to_numpy()
        atr_   = _atr(df, self.parameters["atr_period"] * scale).to_numpy()
        mult   = self.parameters["displacement_atr_mult"]
        bull = np.zeros(n, dtype=bool)
        bear = np.zeros(n, dtype=bool)
        fvg_direction = 0
        for i in range(2, n):
            body = abs(closes[i-1] - opens[i-1])
            if body > mult * atr_[i-1]:
                if lows[i] > highs[i-2]:
                    fvg_direction = 1
                elif highs[i] < lows[i-2]:
                    fvg_direction = -1
            if fvg_direction == 1:
                bull[i] = True
            elif fvg_direction == -1:
                bear[i] = True
        return pd.Series(bull, index=df.index), pd.Series(bear, index=df.index)


class PremiumDiscountZoneBias(AbstractBias):
    """
    BIAS_PREMIUM_DISCOUNT: HTF range position.
    Computes the rolling N-bar H/L range. Price in lower 50% = discount (buy bias).
    Price in upper 50% = premium (sell bias).
    Used for mean-reversion / range hypothesis families.
    """
    def __init__(self, lookback: int = 50):
        super().__init__("BIAS_PREMIUM_DISCOUNT", "Premium/Discount Zone Range Position")
        self.parameters = {"lookback": lookback}

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        lb = self.parameters["lookback"] * scale
        roll_h = df["high"].rolling(lb, min_periods=10).max().shift(1)
        roll_l = df["low"].rolling(lb, min_periods=10).min().shift(1)
        midpoint = (roll_h + roll_l) / 2
        bull = (df["close"] <= midpoint).fillna(False)   # discount zone = buy bias
        bear = (df["close"] >= midpoint).fillna(False)   # premium zone  = sell bias
        return bull, bear


# ── Category E: Regime Extension ─────────────────────────────────────────────

class RegimeCompressionBias(AbstractBias):
    """
    BIAS_REGIME_COMPRESSION: Active COMPRESSION regime from RegimeEngine.
    Used for breakout hypotheses that require prior compression before expansion.
    Direction is determined by MA alignment at time of compression exit.
    """
    def __init__(self):
        super().__init__("BIAS_REGIME_COMPRESSION", "Active Compression Regime Bias")
        self.engine = RegimeEngine()

    def evaluate(self, df: pd.DataFrame, scale: int) -> tuple:
        out = self.engine.compute(df)
        reg   = out.regime
        align = out.measurements["ma_alignment"]
        is_compression = (reg == RegimeState.COMPRESSION.value)
        # Both bull and bear active during compression (direction unresolved)
        bull = (is_compression & (align >= 0)).fillna(False)
        bear = (is_compression & (align < 0)).fillna(False)
        return bull, bear


def register_all_biases(registry):
    # Phase A/B existing biases
    registry.register(CanonicalSupertrendStochasticBias())
    registry.register(TrendMAAlignmentBias())
    registry.register(StructHHHLBias())
    registry.register(MomRSIRegimeBias())
    registry.register(NeutralBias())
    registry.register(RegimeTrendBias())
    registry.register(RegimeRangeBias())
    registry.register(RegimeAnyBias("REGIME"))
    registry.register(RegimeAnyBias("REGIME_ANY"))
    # Phase E new biases
    for cls in [
        IchimokuCloudBias,
        MACDRegimeBias,
        ADXDirectionalBias,
        StochasticRegimeBias,
        SqueezeDirectionBias,
        MomentumSlopeBias,
        VWAPPositionBias,
        BreakOfStructureBias,
        ChangeOfCharacterBias,
        OrderBlockBias,
        FVGDirectionalBias,
        PremiumDiscountZoneBias,
        RegimeCompressionBias,
    ]:
        registry.register(cls())
