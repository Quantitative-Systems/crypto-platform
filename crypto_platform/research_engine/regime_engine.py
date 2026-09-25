"""Crypto Trading Platform — Multi-Timeframe Regime & Intelligence Engine.

Classifies market regimes (Trending, Ranging, Volatility Expansion, Crisis)
and calculates dynamic risk/allocation adjustments for the strategy engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Dict, List, Optional
import numpy as np


class MarketRegime(Enum):
    TRENDING_BULL = "TRENDING_BULL"
    TRENDING_BEAR = "TRENDING_BEAR"
    RANGING_COMPRESSED = "RANGING_COMPRESSED"
    VOLATILITY_EXPANSION = "VOLATILITY_EXPANSION"
    LIQUIDITY_CRISIS = "LIQUIDITY_CRISIS"


@dataclass
class RegimeState:
    symbol: str
    regime: MarketRegime
    atr_percentile: float
    trend_strength: float
    funding_rate_bps: float
    risk_multiplier: float
    recommended_allocation: Dict[str, float]
    timestamp_ms: int


class RegimeEngine:
    """Quantitative regime classification engine driving dynamic strategy weights."""

    def __init__(self, atr_lookback: int = 24, trend_lookback: int = 50):
        self.atr_lookback = atr_lookback
        self.trend_lookback = trend_lookback

    def classify_series(
        self,
        symbol: str,
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        current_funding_bps: float = 1.0,
        timestamp_ms: int = 0,
    ) -> RegimeState:
        """Classifies the market regime for a single asset series and outputs risk multipliers."""
        if len(closes) < self.trend_lookback:
            return RegimeState(
                symbol=symbol,
                regime=MarketRegime.RANGING_COMPRESSED,
                atr_percentile=50.0,
                trend_strength=0.0,
                funding_rate_bps=current_funding_bps,
                risk_multiplier=1.0,
                recommended_allocation={"trend": 0.5, "mean_reversion": 0.5, "carry": 0.5},
                timestamp_ms=timestamp_ms,
            )

        # 1. Average True Range (ATR) & Volatility Percentile
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])),
        )
        recent_atr = np.mean(tr[-self.atr_lookback :])
        hist_atr = np.mean(tr)
        atr_ratio = recent_atr / max(hist_atr, 1e-8)
        atr_percentile = min(100.0, max(0.0, atr_ratio * 50.0))

        # 2. Trend Strength & Direction (EMA Slope & Donchian Channel Position)
        fast_sma = np.mean(closes[-12:])
        slow_sma = np.mean(closes[-self.trend_lookback :])
        price_to_slow = (closes[-1] - slow_sma) / slow_sma
        trend_strength = abs(price_to_slow) * 100.0

        # 3. Regime Determination
        if atr_percentile > 90.0:
            regime = MarketRegime.LIQUIDITY_CRISIS
            risk_mult = 0.4  # Hard de-risking
            alloc = {"trend": 0.2, "mean_reversion": 0.1, "carry": 0.7}
        elif atr_percentile > 75.0:
            regime = MarketRegime.VOLATILITY_EXPANSION
            risk_mult = 0.7
            alloc = {"trend": 0.6, "mean_reversion": 0.2, "carry": 0.2}
        elif trend_strength > 2.5 and price_to_slow > 0:
            regime = MarketRegime.TRENDING_BULL
            risk_mult = 1.0
            alloc = {"trend": 0.8, "mean_reversion": 0.1, "carry": 0.4}
        elif trend_strength > 2.5 and price_to_slow < 0:
            regime = MarketRegime.TRENDING_BEAR
            risk_mult = 0.9
            alloc = {"trend": 0.8, "mean_reversion": 0.1, "carry": 0.5}
        else:
            regime = MarketRegime.RANGING_COMPRESSED
            risk_mult = 1.0
            alloc = {"trend": 0.2, "mean_reversion": 0.8, "carry": 0.8}

        return RegimeState(
            symbol=symbol,
            regime=regime,
            atr_percentile=round(float(atr_percentile), 2),
            trend_strength=round(float(trend_strength), 2),
            funding_rate_bps=round(float(current_funding_bps), 4),
            risk_multiplier=round(float(risk_mult), 2),
            recommended_allocation=alloc,
            timestamp_ms=timestamp_ms,
        )

    def compute_portfolio_regime_matrix(
        self,
        symbols_data: Dict[str, Dict[str, np.ndarray]],
        funding_rates: Dict[str, float],
    ) -> Dict[str, Any]:
        """Aggregates multi-asset regimes into an institutional portfolio risk matrix."""
        states = {}
        regime_counts: Dict[str, int] = {}

        for sym, data in symbols_data.items():
            st = self.classify_series(
                symbol=sym,
                closes=data["closes"],
                highs=data["highs"],
                lows=data["lows"],
                current_funding_bps=funding_rates.get(sym, 1.0),
            )
            states[sym] = {
                "regime": st.regime.value,
                "atr_percentile": st.atr_percentile,
                "trend_strength": st.trend_strength,
                "funding_rate_bps": st.funding_rate_bps,
                "risk_multiplier": st.risk_multiplier,
                "recommended_allocation": st.recommended_allocation,
            }
            regime_counts[st.regime.value] = regime_counts.get(st.regime.value, 0) + 1

        # Global macro posture
        crisis_count = regime_counts.get(MarketRegime.LIQUIDITY_CRISIS.value, 0)
        dominant_regime = max(regime_counts.items(), key=lambda x: x[1])[0] if regime_counts else "UNKNOWN"

        portfolio_risk_scale = 0.5 if crisis_count > 0 else 1.0

        return {
            "dominant_regime": dominant_regime,
            "portfolio_risk_scale": portfolio_risk_scale,
            "symbols": states,
            "regime_distribution": regime_counts,
        }
