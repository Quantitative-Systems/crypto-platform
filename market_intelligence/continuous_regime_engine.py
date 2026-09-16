"""
QCP Continuous Regime Engine.
Multi-dimensional market state classification quantifying:
- Trend state (Bull momentum, Bear expansion, Sideways chop)
- Volatility state (Low-vol squeeze, Normal, Vol explosion)
- Liquidity state (Expanding depth, Normal, Contraction void)
- Funding state (Neutral, Extreme positive, Extreme negative)
- Correlation state (Dispersed, Coupled systemic shock)
"""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class TrendState(str, enum.Enum):
    BULL_MOMENTUM = "BULL_MOMENTUM"
    BEAR_EXPANSION = "BEAR_EXPANSION"
    SIDEWAYS_CHOP = "SIDEWAYS_CHOP"


class VolatilityState(str, enum.Enum):
    LOW_VOL_SQUEEZE = "LOW_VOL_SQUEEZE"
    NORMAL_VOL = "NORMAL_VOL"
    VOL_EXPLOSION = "VOL_EXPLOSION"


class LiquidityState(str, enum.Enum):
    EXPANDING_DEPTH = "EXPANDING_DEPTH"
    NORMAL_DEPTH = "NORMAL_DEPTH"
    LIQUIDITY_CONTRACTION = "LIQUIDITY_CONTRACTION"


class FundingState(str, enum.Enum):
    NEUTRAL_CARRY = "NEUTRAL_CARRY"
    EXTREME_POSITIVE_FUNDING = "EXTREME_POSITIVE_FUNDING"
    EXTREME_NEGATIVE_FUNDING = "EXTREME_NEGATIVE_FUNDING"


class CorrelationState(str, enum.Enum):
    DISPERSED_MARKET = "DISPERSED_MARKET"
    COUPLED_SYSTEMIC_SHOCK = "COUPLED_SYSTEMIC_SHOCK"


@dataclass
class RegimeState:
    timestamp_utc: str
    symbol: str
    trend: TrendState
    volatility: VolatilityState
    liquidity: LiquidityState
    funding: FundingState
    correlation: CorrelationState
    trend_strength_score: float     # [-1.0, 1.0]
    volatility_percentile: float    # [0.0, 100.0]
    liquidity_depth_ratio: float    # relative to 30d median
    annualized_funding_pct: float
    systemic_coupling_score: float  # [0.0, 1.0]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["trend"] = self.trend.value
        d["volatility"] = self.volatility.value
        d["liquidity"] = self.liquidity.value
        d["funding"] = self.funding.value
        d["correlation"] = self.correlation.value
        return d


class ContinuousRegimeEngine:
    """
    Evaluates multi-timeframe market telemetry to classify continuous regimes,
    informing the research factory and capital allocator of structural macro conditions.
    """

    def __init__(self, ema_fast: int = 20, ema_slow: int = 50, atr_period: int = 14):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.atr_period = atr_period

    def classify_series(
        self,
        df: pd.DataFrame,
        symbol: str = "SOL/USDT",
        funding_rate_bps: float = 1.0,
        cross_corr_score: float = 0.45
    ) -> RegimeState:
        """Classifies the most recent bar into a 5-dimensional regime vector."""
        if len(df) < max(self.ema_slow, self.atr_period) + 10:
            return self._default_regime(symbol)

        c = df["close"].values
        h = df["high"].values
        l = df["low"].values

        # 1. Trend Calculation
        ema_f = pd.Series(c).ewm(span=self.ema_fast, adjust=False).mean().values
        ema_s = pd.Series(c).ewm(span=self.ema_slow, adjust=False).mean().values
        trend_diff = (ema_f[-1] - ema_s[-1]) / max(1e-6, ema_s[-1])

        if trend_diff > 0.015 and c[-1] > ema_f[-1]:
            trend = TrendState.BULL_MOMENTUM
            trend_score = min(1.0, trend_diff * 20.0)
        elif trend_diff < -0.015 and c[-1] < ema_f[-1]:
            trend = TrendState.BEAR_EXPANSION
            trend_score = max(-1.0, trend_diff * 20.0)
        else:
            trend = TrendState.SIDEWAYS_CHOP
            trend_score = float(trend_diff * 20.0)

        # 2. Volatility Calculation (ATR percentile)
        tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
        atr = pd.Series(tr).rolling(self.atr_period).mean().dropna().values
        if len(atr) > 20:
            current_atr = atr[-1]
            vol_pct = float(np.mean(atr <= current_atr) * 100.0)
        else:
            vol_pct = 50.0

        if vol_pct < 25.0:
            vol = VolatilityState.LOW_VOL_SQUEEZE
        elif vol_pct > 80.0:
            vol = VolatilityState.VOL_EXPLOSION
        else:
            vol = VolatilityState.NORMAL_VOL

        # 3. Liquidity Calculation (Volume vs rolling median)
        if "volume" in df.columns:
            v = df["volume"].values
            rolling_med = np.median(v[-60:]) if len(v) >= 60 else np.median(v)
            liq_ratio = float(v[-1] / max(1e-6, rolling_med))
        else:
            liq_ratio = 1.0

        if liq_ratio < 0.6:
            liq = LiquidityState.LIQUIDITY_CONTRACTION
        elif liq_ratio > 1.8:
            liq = LiquidityState.EXPANDING_DEPTH
        else:
            liq = LiquidityState.NORMAL_DEPTH

        # 4. Funding State
        annualized_funding = (funding_rate_bps / 10000.0) * (365 * 3) * 100.0
        if annualized_funding > 25.0:
            funding = FundingState.EXTREME_POSITIVE_FUNDING
        elif annualized_funding < -15.0:
            funding = FundingState.EXTREME_NEGATIVE_FUNDING
        else:
            funding = FundingState.NEUTRAL_CARRY

        # 5. Correlation State
        if cross_corr_score > 0.75:
            corr = CorrelationState.COUPLED_SYSTEMIC_SHOCK
        else:
            corr = CorrelationState.DISPERSED_MARKET

        ts_val = df["timestamp"].iloc[-1] if "timestamp" in df.columns else datetime.now(timezone.utc).isoformat()
        ts_str = str(ts_val)

        return RegimeState(
            timestamp_utc=ts_str,
            symbol=symbol,
            trend=trend,
            volatility=vol,
            liquidity=liq,
            funding=funding,
            correlation=corr,
            trend_strength_score=round(trend_score, 4),
            volatility_percentile=round(vol_pct, 2),
            liquidity_depth_ratio=round(liq_ratio, 3),
            annualized_funding_pct=round(annualized_funding, 2),
            systemic_coupling_score=round(cross_corr_score, 3)
        )

    def _default_regime(self, symbol: str) -> RegimeState:
        return RegimeState(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            trend=TrendState.SIDEWAYS_CHOP,
            volatility=VolatilityState.NORMAL_VOL,
            liquidity=LiquidityState.NORMAL_DEPTH,
            funding=FundingState.NEUTRAL_CARRY,
            correlation=CorrelationState.DISPERSED_MARKET,
            trend_strength_score=0.0,
            volatility_percentile=50.0,
            liquidity_depth_ratio=1.0,
            annualized_funding_pct=10.95,
            systemic_coupling_score=0.35
        )
