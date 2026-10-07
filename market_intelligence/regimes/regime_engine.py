"""Market Regime Engine: Multi-Dimensional Environment Classification.

Computes independent Volatility, Liquidity, Correlation, Trend, and Risk regimes,
strictly preserving the distinction between environmental Regime and price Phase.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np

from market_intelligence.regimes.regime_contracts import (
    CorrelationRegime,
    LiquidityRegime,
    MarketRegimeSnapshot,
    RiskRegime,
    TrendRegime,
    VolatilityRegime,
)
from market_model.contracts import MarketState, TrendDirection


class MarketRegimeEngine:
    """Evaluates multi-dimensional market climate without contaminating technical structure."""

    def __init__(self, vol_lookback_bars: int = 60):
        self.vol_lookback_bars = vol_lookback_bars

    def evaluate_regime(
        self,
        current_state: MarketState,
        historical_closes: Optional[np.ndarray] = None,
        cross_market_data: Optional[Dict[str, Any]] = None,
        positioning_data: Optional[Dict[str, Any]] = None,
    ) -> MarketRegimeSnapshot:
        """Derive full environmental regime snapshot from state and external inputs."""
        ts_ms = current_state.timestamp_ms

        # 1. Volatility Regime
        vol_regime, ann_vol, vol_pct = self._classify_volatility(current_state, historical_closes)

        # 2. Liquidity Regime
        liq_regime, liq_score = self._classify_liquidity(current_state, positioning_data)

        # 3. Correlation Regime
        corr_regime, avg_corr = self._classify_correlation(cross_market_data)

        # 4. Trend Regime
        trend_regime = self._classify_trend(current_state)

        # 5. Risk Regime
        risk_regime = self._classify_risk(cross_market_data, current_state)

        # Trend-following favorability: Trending environment, Normal/Abundant liquidity, non-extreme volatility
        is_favorable = (
            trend_regime in (TrendRegime.TRENDING, TrendRegime.TRANSITIONAL)
            and vol_regime in (VolatilityRegime.LOW, VolatilityRegime.NORMAL, VolatilityRegime.HIGH)
            and liq_regime in (LiquidityRegime.NORMAL, LiquidityRegime.ABUNDANT)
            and vol_regime != VolatilityRegime.EXTREME
        )

        return MarketRegimeSnapshot(
            timestamp_ms=ts_ms,
            volatility=vol_regime,
            liquidity=liq_regime,
            correlation=corr_regime,
            trend=trend_regime,
            risk=risk_regime,
            realized_vol_annualized=ann_vol,
            vol_percentile=vol_pct,
            liquidity_score=liq_score,
            average_crypto_macro_corr=avg_corr,
            is_favorable_for_trend_following=is_favorable,
            meta={
                "symbol": current_state.symbol,
                "timeframe": current_state.timeframe,
            },
        )

    def _classify_volatility(
        self,
        state: MarketState,
        closes: Optional[np.ndarray],
    ) -> tuple[VolatilityRegime, float, float]:
        """Compute realized vol and map to volatility regime."""
        if closes is not None and len(closes) >= 15:
            # Calculate log returns
            log_returns = np.diff(np.log(closes[-self.vol_lookback_bars:]))
            if len(log_returns) > 5 and np.std(log_returns) > 0:
                ann_vol = float(np.std(log_returns) * math.sqrt(365 * 24))  # Hourly proxy
                # Percentile estimate relative to historical crypto norms (30% to 120%)
                vol_pct = float(np.clip((ann_vol - 0.30) / (1.20 - 0.30), 0.05, 0.99))
            else:
                ann_vol = state.measurements.realized_vol or 0.65
                vol_pct = 0.50
        else:
            ann_vol = state.measurements.realized_vol or 0.65
            vol_pct = 0.50

        if vol_pct < 0.25:
            regime = VolatilityRegime.LOW
        elif vol_pct <= 0.70:
            regime = VolatilityRegime.NORMAL
        elif vol_pct <= 0.90:
            regime = VolatilityRegime.HIGH
        else:
            regime = VolatilityRegime.EXTREME

        return regime, ann_vol, vol_pct

    def _classify_liquidity(
        self,
        state: MarketState,
        positioning_data: Optional[Dict[str, Any]],
    ) -> tuple[LiquidityRegime, float]:
        """Assess liquidity depth and order-book health."""
        vol_ratio = state.measurements.volume_sma_ratio or 1.0
        
        # Consider liquidation cascade or funding stress if provided
        cascade_active = False
        if positioning_data:
            cascade_active = positioning_data.get("is_liquidation_cascade", False)

        if cascade_active:
            return LiquidityRegime.IMPAIRED, 0.20

        if vol_ratio > 1.3:
            return LiquidityRegime.ABUNDANT, 1.40
        elif vol_ratio >= 0.75:
            return LiquidityRegime.NORMAL, 1.00
        elif vol_ratio >= 0.40:
            return LiquidityRegime.TIGHT, 0.60
        else:
            return LiquidityRegime.IMPAIRED, 0.30

    def _classify_correlation(
        self,
        cross_market_data: Optional[Dict[str, Any]],
    ) -> tuple[CorrelationRegime, float]:
        """Determine what factor is primarily driving price dispersion."""
        if not cross_market_data:
            return CorrelationRegime.BTC_LED, 0.10

        macro_corr = cross_market_data.get("macro_correlation", 0.0)
        btc_alt_corr = cross_market_data.get("btc_alt_correlation", 0.85)

        if abs(macro_corr) > 0.60:
            return CorrelationRegime.MACRO_LED, macro_corr
        elif btc_alt_corr > 0.70:
            return CorrelationRegime.BTC_LED, macro_corr
        elif btc_alt_corr < 0.40:
            return CorrelationRegime.IDIOSYNCRATIC, macro_corr
        else:
            return CorrelationRegime.SECTOR_LED, macro_corr

    def _classify_trend(self, state: MarketState) -> TrendRegime:
        """Classify directional trend persistence."""
        ext_trend = state.structure.external_trend
        adx = state.measurements.adx

        if ext_trend in (TrendDirection.BULLISH, TrendDirection.BEARISH) and adx >= 22.0:
            return TrendRegime.TRENDING
        elif ext_trend in (TrendDirection.RANGE, TrendDirection.NEUTRAL):
            return TrendRegime.RANGING
        else:
            return TrendRegime.TRANSITIONAL

    def _classify_risk(
        self,
        cross_market_data: Optional[Dict[str, Any]],
        state: MarketState,
    ) -> RiskRegime:
        """Classify broad market risk appetite."""
        if not cross_market_data:
            # Fallback to local price trend
            if state.structure.external_trend == TrendDirection.BULLISH:
                return RiskRegime.RISK_ON
            elif state.structure.external_trend == TrendDirection.BEARISH:
                return RiskRegime.RISK_OFF
            return RiskRegime.NEUTRAL

        dxy_trend = cross_market_data.get("dxy_trend", "NEUTRAL")
        vix_level = cross_market_data.get("vix_level", 18.0)
        spx_trend = cross_market_data.get("spx_trend", "NEUTRAL")

        if vix_level > 28.0 or (dxy_trend == "BULLISH" and spx_trend == "BEARISH"):
            return RiskRegime.RISK_OFF
        elif vix_level < 20.0 and dxy_trend == "BEARISH" and spx_trend == "BULLISH":
            return RiskRegime.RISK_ON
        else:
            return RiskRegime.NEUTRAL
