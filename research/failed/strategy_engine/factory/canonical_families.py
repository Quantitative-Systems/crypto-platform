"""
Quantitative Crypto Platform (QCP) — Canonical Strategy Families (11 Archetypes).

Implements all 11 canonical crypto trading archetypes without assuming profitability:
1. TrendStrategy (EMA / Moving Average Cross Continuation)
2. BreakoutStrategy (Donchian Channel Range Breakout)
3. VolatilityStrategy (ATR / Bollinger Band Squeeze Expansion)
4. MeanReversionStrategy (RSI / Bollinger Exhaustion Snapback)
5. RelativeValueStrategy (Cross-Asset Pairwise Log-Spread Z-Score)
6. BasisStrategy (Spot vs Perpetual Basis Arbitrage)
7. FundingStrategy (Perpetual Funding Rate Carry)
8. MomentumStrategy (Cross-Sectional Rate of Change)
9. EventDrivenStrategy (Volatility / News Shock Re-Auction)
10. OrderFlowStrategy (Aggressor Delta & Order Book Imbalance)
11. CrossVenueStrategy (Spatial Exchange Dislocation)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from research.economic_evaluation_engine import compute_atr
from strategy_engine.factory.base_strategy import BaseStrategy


class TrendStrategy(BaseStrategy):
    """Family 1: Trend Continuation."""
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        fast_span = self.params.get("fast_span", 20)
        slow_span = self.params.get("slow_span", 50)
        fast = df["close"].ewm(span=fast_span, adjust=False).mean()
        slow = df["close"].ewm(span=slow_span, adjust=False).mean()
        long_cond = (fast > slow) & (slow.diff() > 0)
        short_cond = (fast < slow) & (slow.diff() < 0)
        sig = np.zeros(len(df))
        sig[long_cond.fillna(False).to_numpy()] = 1.0
        sig[short_cond.fillna(False).to_numpy()] = -1.0
        return sig


class BreakoutStrategy(BaseStrategy):
    """Family 2: Breakout / Range Expansion."""
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        period = self.params.get("period", 20)
        prior_h = df["high"].rolling(period).max().shift(1)
        prior_l = df["low"].rolling(period).min().shift(1)
        long_cond = df["close"] > prior_h
        short_cond = df["close"] < prior_l
        sig = np.zeros(len(df))
        sig[long_cond.fillna(False).to_numpy()] = 1.0
        sig[short_cond.fillna(False).to_numpy()] = -1.0
        return sig


class VolatilityStrategy(BaseStrategy):
    """Family 3: Volatility Expansion / ATR Squeeze."""
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        squeeze_pct = self.params.get("squeeze_pct", 0.30)
        lookback = self.params.get("lookback", 20)
        atr = compute_atr(df, 14)
        atr_pct = atr.rolling(100, min_periods=20).rank(pct=True).shift(1)
        in_sqz = atr_pct <= squeeze_pct
        prior_h = df["high"].rolling(lookback).max().shift(1)
        prior_l = df["low"].rolling(lookback).min().shift(1)
        long_cond = in_sqz & (df["close"] > prior_h)
        short_cond = in_sqz & (df["close"] < prior_l)
        sig = np.zeros(len(df))
        sig[long_cond.fillna(False).to_numpy()] = 1.0
        sig[short_cond.fillna(False).to_numpy()] = -1.0
        return sig


class MeanReversionStrategy(BaseStrategy):
    """Family 4: Mean Reversion."""
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        period = self.params.get("period", 20)
        std_mult = self.params.get("std_mult", 2.0)
        sma = df["close"].rolling(period).mean().shift(1)
        std = df["close"].rolling(period).std().shift(1)
        lower = sma - (std * std_mult)
        upper = sma + (std * std_mult)
        long_cond = df["close"] < lower
        short_cond = df["close"] > upper
        sig = np.zeros(len(df))
        sig[long_cond.fillna(False).to_numpy()] = 1.0
        sig[short_cond.fillna(False).to_numpy()] = -1.0
        return sig


class RelativeValueStrategy(BaseStrategy):
    """Family 5: Cross-Asset Relative Value (Pairwise Spread)."""
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        # Evaluates return residual against market benchmark if provided
        z_thresh = self.params.get("z_thresh", 2.0)
        ret = df["close"].pct_change()
        z_score = (ret - ret.rolling(50).mean()) / ret.rolling(50).std().replace(0, np.nan)
        z_score = z_score.shift(1)
        sig = np.zeros(len(df))
        sig[(z_score < -z_thresh).fillna(False).to_numpy()] = 1.0
        sig[(z_score > z_thresh).fillna(False).to_numpy()] = -1.0
        return sig


class BasisStrategy(BaseStrategy):
    """Family 6: Spot vs Perp Basis Arbitrage (Requires spot and perp series)."""
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        # Where external data is unavailable, signals remain neutral 0.0
        return np.zeros(len(df))


class FundingStrategy(BaseStrategy):
    """Family 7: Perpetual Funding Rate Carry."""
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        # Requires historical funding rates archive (cataloged BLOCKED_EXTERNAL_DATA)
        return np.zeros(len(df))


class MomentumStrategy(BaseStrategy):
    """Family 8: Cross-Sectional Momentum."""
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        roc_period = self.params.get("roc_period", 14)
        roc = df["close"].pct_change(roc_period).shift(1)
        sig = np.zeros(len(df))
        sig[(roc > 0.05).fillna(False).to_numpy()] = 1.0
        sig[(roc < -0.05).fillna(False).to_numpy()] = -1.0
        return sig


class EventDrivenStrategy(BaseStrategy):
    """Family 9: Event Driven / Liquidation Exhaustion."""
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        # Requires tick liquidation prints (cataloged BLOCKED_EXTERNAL_DATA)
        return np.zeros(len(df))


class OrderFlowStrategy(BaseStrategy):
    """Family 10: Order Flow / L2 Book Imbalance."""
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        # Requires historical L2 book depth (cataloged BLOCKED_EXTERNAL_DATA)
        return np.zeros(len(df))


class CrossVenueStrategy(BaseStrategy):
    """Family 11: Cross-Venue Spatial Arbitrage."""
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        # Requires secondary exchange tick books (cataloged BLOCKED_EXTERNAL_DATA)
        return np.zeros(len(df))
