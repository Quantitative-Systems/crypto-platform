"""
QCP Regime Engine (v1.0.0-causal).
Provides modular, causal, and versioned market regime classification.

The regime engine uses strictly backward-looking (point-in-time) measurements
and does NOT optimize thresholds for backtest performance.

Initial Regime States:
- TREND_UP: Bullish trend structure, positive MA alignment, high range efficiency.
- TREND_DOWN: Bearish trend structure, negative MA alignment, high range efficiency.
- RANGE: Indecisive directional movement, low range efficiency.
- LOW_VOL: Realized volatility / ATR in the lowest quintile.
- NORMAL_VOL: Baseline historical volatility environment.
- HIGH_VOL: Realized volatility / ATR in the highest quintile.
- COMPRESSION: Narrow Bollinger bandwidth and low ATR percentile preceding expansion.
- EXPANSION: Widening volatility bands and high directional impulse.
- UNKNOWN: Insufficient history (warm-up period).
"""

from dataclasses import dataclass
import enum
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd


REGIME_ENGINE_VERSION = "1.0.0-causal"


class RegimeState(str, enum.Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    LOW_VOL = "LOW_VOL"
    NORMAL_VOL = "NORMAL_VOL"
    HIGH_VOL = "HIGH_VOL"
    COMPRESSION = "COMPRESSION"
    EXPANSION = "EXPANSION"
    UNKNOWN = "UNKNOWN"


@dataclass
class RegimeOutput:
    """Container holding regime series and all underlying causal measurements."""
    regime: pd.Series
    measurements: pd.DataFrame
    version: str = REGIME_ENGINE_VERSION


class RegimeEngine:
    """
    Causal Regime Classification Engine.
    
    Thresholds and justifications:
    - Warm-up period: 50 bars. Prior to 50 bars, output is UNKNOWN.
    - MA Fast/Slow: 20 and 50 exponential moving averages. Standard institutional trend reference.
    - Efficiency Ratio: Kaufman Efficiency Ratio (net direction / total path) over 20 bars.
      * ER > 0.40 indicates directional efficiency (trend/expansion).
      * ER < 0.25 indicates path inefficiency (chop/range/compression).
    - ATR Percentile: Rolling 100-bar percentile rank of 14-period ATR.
      * > 0.80: High volatility regime.
      * < 0.20: Low volatility regime.
    - Bollinger Bandwidth Percentile: Rolling 100-bar percentile rank of (Upper - Lower) / Middle.
      * < 0.20: COMPRESSION.
      * > 0.85: EXPANSION.
    """

    def __init__(
        self,
        fast_ma_period: int = 20,
        slow_ma_period: int = 50,
        atr_period: int = 14,
        vol_lookback: int = 20,
        percentile_window: int = 100,
        warmup_bars: int = 50,
    ):
        self.fast_ma_period = fast_ma_period
        self.slow_ma_period = slow_ma_period
        self.atr_period = atr_period
        self.vol_lookback = vol_lookback
        self.percentile_window = percentile_window
        self.warmup_bars = warmup_bars

    @staticmethod
    def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(alpha=1.0 / period, adjust=False).mean()

    @staticmethod
    def _compute_dmi(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        up = high - high.shift(1)
        down = low.shift(1) - low

        plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
        minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1.0 / period, adjust=False).mean().replace(0, np.nan)

        plus_di = 100.0 * (plus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr)
        minus_di = 100.0 * (minus_dm.ewm(alpha=1.0 / period, adjust=False).mean() / atr)

        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.ewm(alpha=1.0 / period, adjust=False).mean()
        return plus_di.fillna(0.0), minus_di.fillna(0.0), adx.fillna(0.0)

    def compute(self, df: pd.DataFrame) -> RegimeOutput:
        """
        Executes causal feature computation and produces regime classification.
        All inputs must be chronological OHLCV DataFrame.
        """
        closes = df["close"]
        highs = df["high"]
        lows = df["low"]

        # 1. Moving Averages & Slopes
        fast_ma = closes.ewm(span=self.fast_ma_period, adjust=False).mean()
        slow_ma = closes.ewm(span=self.slow_ma_period, adjust=False).mean()
        ma_alignment = fast_ma - slow_ma
        ma_slope = fast_ma - fast_ma.shift(5)

        # 2. Volatility Metrics
        log_ret = np.log(closes / closes.shift(1).replace(0, np.nan)).fillna(0.0)
        realized_vol = log_ret.rolling(self.vol_lookback, min_periods=5).std() * np.sqrt(365 * 24)
        
        atr = self._compute_atr(df, self.atr_period)
        atr_pct = atr.rolling(self.percentile_window, min_periods=20).rank(pct=True).fillna(0.5)

        # 3. Bollinger Bandwidth (Compression / Expansion)
        bb_mid = closes.rolling(20, min_periods=5).mean()
        bb_std = closes.rolling(20, min_periods=5).std()
        bb_width = (2.0 * bb_std) / bb_mid.replace(0, np.nan)
        bb_width_pct = bb_width.rolling(self.percentile_window, min_periods=20).rank(pct=True).fillna(0.5)

        # 4. Range Efficiency (Kaufman Efficiency Ratio)
        net_change = (closes - closes.shift(20)).abs()
        gross_path = (closes - closes.shift(1)).abs().rolling(20, min_periods=5).sum()
        range_efficiency = (net_change / gross_path.replace(0, np.nan)).fillna(0.0)

        # 5. Directional Movement
        plus_di, minus_di, adx = self._compute_dmi(df, self.atr_period)
        directional_diff = plus_di - minus_di

        # Build Measurements DataFrame
        measurements = pd.DataFrame({
            "fast_ma": fast_ma,
            "slow_ma": slow_ma,
            "ma_alignment": ma_alignment,
            "ma_slope": ma_slope,
            "realized_vol": realized_vol,
            "atr": atr,
            "atr_percentile": atr_pct,
            "bb_width_pct": bb_width_pct,
            "range_efficiency": range_efficiency,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "adx": adx,
            "directional_diff": directional_diff,
        }, index=df.index)

        # ── Causal Classification — Vectorised ───────────────────────────────
        # All series are already pandas Series aligned on df.index.
        # np.select evaluates conditions in priority order (first match wins),
        # preserving the identical priority hierarchy as the original loop.

        eff   = range_efficiency.to_numpy()
        atr_p = atr_pct.to_numpy()
        bb_p  = bb_width_pct.to_numpy()
        align = ma_alignment.to_numpy()
        slope = ma_slope.to_numpy()
        d_diff = directional_diff.to_numpy()
        d_adx  = adx.to_numpy()

        conditions = [
            # Priority 1a: Compression
            (bb_p < 0.20) & (atr_p < 0.25),
            # Priority 1b: Expansion
            (bb_p > 0.85) & (eff > 0.35),
            # Priority 2a: Trend Up
            (align > 0) & (slope > 0) & (d_diff > 5.0) & (eff >= 0.35),
            # Priority 2b: Trend Down
            (align < 0) & (slope < 0) & (d_diff < -5.0) & (eff >= 0.35),
            # Priority 3a: High Vol
            (atr_p >= 0.80),
            # Priority 3b: Low Vol
            (atr_p <= 0.20),
            # Priority 4: Range / Consolidation
            (eff < 0.30) | (d_adx < 20.0),
        ]
        choices = [
            RegimeState.COMPRESSION.value,
            RegimeState.EXPANSION.value,
            RegimeState.TREND_UP.value,
            RegimeState.TREND_DOWN.value,
            RegimeState.HIGH_VOL.value,
            RegimeState.LOW_VOL.value,
            RegimeState.RANGE.value,
        ]
        states = np.select(conditions, choices, default=RegimeState.NORMAL_VOL.value)

        # Mask warm-up bars to UNKNOWN (matches causal contract)
        states[:self.warmup_bars] = RegimeState.UNKNOWN.value

        regime_series = pd.Series(states, index=df.index, name="regime")
        return RegimeOutput(regime=regime_series, measurements=measurements)



def classify_market_regime(df: pd.DataFrame) -> RegimeOutput:
    engine = RegimeEngine()
    return engine.compute(df)
