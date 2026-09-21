"""
Quantitative Systems Platform (QSP) — Market Intelligence Regime Engine.

Continuously classifies the market environment into multidimensional regimes:
- Trend Regime: Strong Bull, Weak Bull, Range Bound, Weak Bear, Strong Bear
- Volatility Regime: Compression (Squeeze), Normal, Expansion, Extreme Volatility
- Liquidity Regime: High, Normal, Deteriorating

Calculates the conditional probability and compatibility score:
    P(Strategy Edge | Current Regime)
Allowing the platform to throttle or suppress trades in hostile market conditions.
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class TrendRegime(str, Enum):
    STRONG_BULL = "STRONG_BULL"
    WEAK_BULL = "WEAK_BULL"
    RANGE_BOUND = "RANGE_BOUND"
    WEAK_BEAR = "WEAK_BEAR"
    STRONG_BEAR = "STRONG_BEAR"


class VolatilityRegime(str, Enum):
    COMPRESSION = "COMPRESSION"
    NORMAL = "NORMAL"
    EXPANSION = "EXPANSION"
    EXTREME_VOLATILITY = "EXTREME_VOLATILITY"


class RegimeFilterAction(str, Enum):
    ALLOW_FULL_SIZE = "ALLOW_FULL_SIZE"
    ALLOW_HALF_SIZE = "ALLOW_HALF_SIZE"
    SUPPRESS_SIGNAL = "SUPPRESS_SIGNAL"


@dataclass
class MarketRegimeSnapshot:
    timestamp: int
    symbol: str
    trend_regime: TrendRegime
    volatility_regime: VolatilityRegime
    adx_value: float
    atr_percentile: float
    bb_width_pct: float
    ema_alignment_score: float  # +1.0 for perfect bull stack, -1.0 for bear stack, 0 for mixed
    regime_description: str


@dataclass
class StrategyRegimeCompatibility:
    strategy_id: str
    family_id: str
    compatibility_score: float  # 0.0 to 1.0
    action: RegimeFilterAction
    rationale: str


class MarketRegimeEngine:
    """
    Computes real-time market regimes and strategy edge compatibility.
    """

    @staticmethod
    def classify_regime(
        timestamp: int,
        symbol: str,
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
    ) -> MarketRegimeSnapshot:
        """Classifies the current bar's multi-factor market regime."""
        n = len(closes)
        if n < 50:
            return MarketRegimeSnapshot(
                timestamp=timestamp,
                symbol=symbol,
                trend_regime=TrendRegime.RANGE_BOUND,
                volatility_regime=VolatilityRegime.NORMAL,
                adx_value=20.0,
                atr_percentile=50.0,
                bb_width_pct=2.0,
                ema_alignment_score=0.0,
                regime_description="Insufficient history for regime classification",
            )

        # 1. EMA Stack (20, 50, 200 approx)
        c_current = closes[-1]
        sma_20 = np.mean(closes[-20:])
        sma_50 = np.mean(closes[-50:])
        sma_200 = np.mean(closes[-min(200, n):])

        ema_score = 0.0
        if c_current > sma_20 > sma_50 > sma_200:
            ema_score = 1.0
        elif c_current < sma_20 < sma_50 < sma_200:
            ema_score = -1.0
        elif c_current > sma_50:
            ema_score = 0.5
        elif c_current < sma_50:
            ema_score = -0.5

        # 2. Simple ATR & Volatility percentile
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])),
        )
        recent_tr = tr[-14:]
        curr_atr = np.mean(recent_tr) if len(recent_tr) > 0 else 1.0
        atr_window = tr[-min(100, len(tr)):]
        if np.std(atr_window) < 1e-4:
            atr_percentile = 50.0
        else:
            atr_percentile = (np.sum(atr_window <= curr_atr) / len(atr_window)) * 100.0

        # Bollinger Band Width
        std_20 = np.std(closes[-20:])
        bb_width_pct = (4.0 * std_20 / sma_20) * 100.0 if sma_20 > 0 else 0.0

        # 3. Simple Proxy ADX (Directional strength)
        dx_window = np.abs(closes[-14:] - closes[-14]) / curr_atr if curr_atr > 0 else 0.0
        adx_value = min(100.0, float(np.mean(dx_window) * 15.0))

        # Classify Trend
        if ema_score == 1.0 and adx_value >= 25.0:
            trend = TrendRegime.STRONG_BULL
        elif ema_score == -1.0 and adx_value >= 25.0:
            trend = TrendRegime.STRONG_BEAR
        elif ema_score > 0:
            trend = TrendRegime.WEAK_BULL
        elif ema_score < 0:
            trend = TrendRegime.WEAK_BEAR
        else:
            trend = TrendRegime.RANGE_BOUND

        # Classify Volatility
        if atr_percentile >= 92.0:
            vol = VolatilityRegime.EXTREME_VOLATILITY
        elif atr_percentile >= 75.0 or bb_width_pct > 8.0:
            vol = VolatilityRegime.EXPANSION
        elif atr_percentile <= 25.0 or bb_width_pct < 2.5:
            vol = VolatilityRegime.COMPRESSION
        else:
            vol = VolatilityRegime.NORMAL

        desc = f"{trend.value} trend ({adx_value:.1f} ADX) with {vol.value} volatility ({atr_percentile:.0f}th percentile)"

        return MarketRegimeSnapshot(
            timestamp=timestamp,
            symbol=symbol,
            trend_regime=trend,
            volatility_regime=vol,
            adx_value=round(adx_value, 1),
            atr_percentile=round(atr_percentile, 1),
            bb_width_pct=round(bb_width_pct, 2),
            ema_alignment_score=ema_score,
            regime_description=desc,
        )

    @classmethod
    def evaluate_strategy_compatibility(
        cls,
        strategy_family_id: str,
        regime: MarketRegimeSnapshot,
        signal_direction: str = "LONG",
    ) -> StrategyRegimeCompatibility:
        """
        Calculates compatibility score P(Edge | Regime) and trade sizing recommendation.
        """
        score = 0.50
        notes = []

        fam = strategy_family_id.upper()

        if "FAM-07" in fam or "FAM-01" in fam or "FAM-02" in fam or "FAM-04" in fam:
            # Trend following / MTF Continuation / Momentum
            is_bull_match = (signal_direction == "LONG" and regime.trend_regime in (TrendRegime.STRONG_BULL, TrendRegime.WEAK_BULL))
            is_bear_match = (signal_direction == "SHORT" and regime.trend_regime in (TrendRegime.STRONG_BEAR, TrendRegime.WEAK_BEAR))

            if is_bull_match or is_bear_match:
                if regime.trend_regime in (TrendRegime.STRONG_BULL, TrendRegime.STRONG_BEAR):
                    score = 0.90
                    notes.append("Aligned with strong directional trend")
                else:
                    score = 0.70
                    notes.append("Aligned with moderate trend")

                if regime.volatility_regime == VolatilityRegime.EXPANSION:
                    score = min(1.0, score + 0.10)
                    notes.append("Volatility expansion reinforces trend momentum")
                elif regime.volatility_regime == VolatilityRegime.COMPRESSION:
                    score = max(0.0, score - 0.20)
                    notes.append("Volatility compression dampens continuation probability")
                elif regime.volatility_regime == VolatilityRegime.EXTREME_VOLATILITY:
                    score = max(0.0, score - 0.35)
                    notes.append("Extreme volatility increases gap & whip risk")
            else:
                score = 0.20
                notes.append(f"Counter-trend signal ({signal_direction} vs {regime.trend_regime.value})")

        elif "FAM-05" in fam:
            # Mean Reversion
            if regime.trend_regime == TrendRegime.RANGE_BOUND:
                score = 0.85
                notes.append("Range-bound regime ideal for mean reversion")
                if regime.volatility_regime == VolatilityRegime.COMPRESSION:
                    score = 0.95
                    notes.append("Volatility compression favors oscillator oscillations")
            elif regime.trend_regime in (TrendRegime.STRONG_BULL, TrendRegime.STRONG_BEAR):
                score = 0.15
                notes.append("Strong trend regime hostile to mean reversion (trend continuation threat)")

        elif "FAM-03" in fam or "FAM-06" in fam:
            # Breakout / Volatility Expansion
            if regime.volatility_regime == VolatilityRegime.COMPRESSION:
                score = 0.85
                notes.append("Pre-breakout compression setup detected")
            elif regime.volatility_regime == VolatilityRegime.EXPANSION:
                score = 0.75
                notes.append("Expansion in progress")
            else:
                score = 0.40
                notes.append("Normal/uncompressed volatility offers lower breakout momentum")

        # Determine action
        if score >= 0.70:
            action = RegimeFilterAction.ALLOW_FULL_SIZE
        elif score >= 0.45:
            action = RegimeFilterAction.ALLOW_HALF_SIZE
        else:
            action = RegimeFilterAction.SUPPRESS_SIGNAL

        return StrategyRegimeCompatibility(
            strategy_id=strategy_family_id,
            family_id=strategy_family_id,
            compatibility_score=round(score, 2),
            action=action,
            rationale="; ".join(notes),
        )
