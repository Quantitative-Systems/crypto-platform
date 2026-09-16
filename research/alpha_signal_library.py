"""
QCP Alpha Signal Library.
Causal signal constructors for the measurable alpha specifications.

Contract for every signal function here:
    signal_fn(df) -> np.ndarray of {-1, 0, +1}, aligned to df.index
    where signal[i] may use ONLY data available at the close of bar i.
    Filling happens at bar i+1's open inside the evaluation engine.

Alphas whose economic mechanism requires data QCP does not possess (live order
book depth, funding history) are registered with `builder=None` and an explicit
`availability_reason`. They are NOT simulated, approximated or back-filled.
They are reported as DATA_UNAVAILABLE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from research.economic_evaluation_engine import compute_atr


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def trend_continuation_signal(
    fast_span: int = 20,
    slow_span: int = 50,
    pullback_atr_tolerance: float = 1.0,
    atr_period: int = 14,
) -> Callable[[pd.DataFrame], np.ndarray]:
    """
    Directional trend continuation with a pullback entry.

    Economic rationale: persistent crypto trends are driven by order-flow
    herding and slow allocator rebalancing. Entering on a shallow retracement
    inside an established trend harvests continuation without buying the
    extension extreme.

    Long  : fast EMA > slow EMA, slow EMA rising, close pulls back to within
            tolerance*ATR of the fast EMA while remaining above it.
    Short : mirror image.
    """

    def _fn(df: pd.DataFrame) -> np.ndarray:
        close = df["close"]
        atr = compute_atr(df, atr_period)
        fast, slow = _ema(close, fast_span), _ema(close, slow_span)
        tolerance = atr * pullback_atr_tolerance
        pulled_back_up = (close <= fast + tolerance) & (close >= fast)
        pulled_back_down = (close >= fast - tolerance) & (close <= fast)

        long_cond = (fast > slow) & (slow.diff() > 0) & pulled_back_up
        short_cond = (fast < slow) & (slow.diff() < 0) & pulled_back_down

        signal = np.zeros(len(df))
        signal[long_cond.fillna(False).to_numpy()] = 1.0
        signal[short_cond.fillna(False).to_numpy()] = -1.0
        return signal

    return _fn


def volatility_squeeze_breakout_signal(
    squeeze_lookback: int = 100,
    squeeze_percentile: float = 0.30,
    breakout_lookback: int = 20,
    atr_period: int = 14,
) -> Callable[[pd.DataFrame], np.ndarray]:
    """
    Volatility-contraction breakout.

    Economic rationale: volatility clusters and mean-reverts. Compression
    raises the conditional probability of an expansion move; trading the range
    break captures that expansion while the ATR stop bounds risk.
    """

    def _fn(df: pd.DataFrame) -> np.ndarray:
        close = df["close"]
        atr = compute_atr(df, atr_period)
        atr_pct = atr.rolling(squeeze_lookback, min_periods=max(10, squeeze_lookback // 2)).rank(pct=True)
        in_squeeze = atr_pct <= squeeze_percentile

        prior_high = df["high"].rolling(breakout_lookback).max().shift(1)
        prior_low = df["low"].rolling(breakout_lookback).min().shift(1)

        long_cond = in_squeeze & (close > prior_high)
        short_cond = in_squeeze & (close < prior_low)

        signal = np.zeros(len(df))
        signal[long_cond.fillna(False).to_numpy()] = 1.0
        signal[short_cond.fillna(False).to_numpy()] = -1.0
        return signal

    return _fn




def make_relative_value_signal(
    reference_df: pd.DataFrame,
    entry_z: float = 1.5,
    lookback: int = 200,
) -> Callable[[pd.DataFrame], np.ndarray]:
    """
    Cross-asset relative-value reversion versus a reference asset.

    Economic rationale: two high-correlation crypto majors share a common
    factor; transient divergences of their log-price ratio are driven by
    idiosyncratic flow and are compensated to revert.

    The reference series is aligned strictly on matching timestamps, so the
    causality contract holds: bar i's decision uses bar i's close for both legs.
    """
    ref = reference_df[["timestamp", "close"]].rename(columns={"close": "ref_close"})

    def _fn(df: pd.DataFrame) -> np.ndarray:
        merged = df[["timestamp", "close"]].merge(ref, on="timestamp", how="left")
        ratio = np.log(merged["close"] / merged["ref_close"])
        minp = max(10, lookback // 2)
        mean = ratio.rolling(lookback, min_periods=minp).mean()
        std = ratio.rolling(lookback, min_periods=minp).std()
        z = (ratio - mean) / std.replace(0.0, np.nan)

        signal = np.zeros(len(merged))
        vals = z.to_numpy()
        # Divergence above threshold -> short the rich leg; below -> long the cheap leg.
        signal[vals >= entry_z] = -1.0
        signal[vals <= -entry_z] = 1.0
        return signal

    return _fn


@dataclass
class SignalSpec:
    alpha_id: str
    required_data: List[str]
    builder: Optional[Callable[[], Callable[[pd.DataFrame], np.ndarray]]] = None
    availability_reason: str = "AVAILABLE"
    economic_mechanism: str = ""

    @property
    def is_measurable(self) -> bool:
        return self.builder is not None


def build_signal_registry(reference_df: Optional[pd.DataFrame] = None) -> Dict[str, SignalSpec]:
    """Constructs the registry of measurable and explicitly unmeasurable alphas."""
    registry: Dict[str, SignalSpec] = {
        "FAM-07-MTFCONT_SOLUSDT_Set2": SignalSpec(
            alpha_id="FAM-07-MTFCONT_SOLUSDT_Set2",
            required_data=["OHLCV_4h"],
            builder=lambda: trend_continuation_signal(),
            economic_mechanism="Trend persistence + pullback continuation.",
        ),
        "FAM-06-VOLSQUEEZE_SOLUSDT_V1": SignalSpec(
            alpha_id="FAM-06-VOLSQUEEZE_SOLUSDT_V1",
            required_data=["OHLCV_4h"],
            builder=lambda: volatility_squeeze_breakout_signal(),
            economic_mechanism="Volatility clustering and range expansion.",
        ),
        "FAM-12-OFI_MOMENTUM_BTC_V1": SignalSpec(
            alpha_id="FAM-12-OFI_MOMENTUM_BTC_V1",
            required_data=["L2_ORDER_BOOK_DEPTH_TICK", "AGGRESSOR_FLOW"],
            builder=None,
            availability_reason=(
                "DATA_UNAVAILABLE: requires historical L2 book-depth and aggressor-flow "
                "ticks. QCP holds no such archive; the alpha cannot be measured and is "
                "not simulated."
            ),
            economic_mechanism="Order-flow imbalance pressure.",
        ),
        "FAM-10-DYNAMIC_CARRY_SOL_V2": SignalSpec(
            alpha_id="FAM-10-DYNAMIC_CARRY_SOL_V2",
            required_data=["FUNDING_RATE_HISTORY", "SPOT_PERP_BASIS"],
            builder=None,
            availability_reason=(
                "DATA_UNAVAILABLE: requires historical funding-rate and spot/perp basis "
                "series. Not present in the warehouse; measured carry claims are therefore "
                "impossible today."
            ),
            economic_mechanism="Perpetual funding carry.",
        ),
    }

    if reference_df is not None:
        registry["FAM-09-RV_COINT_ETH_BTC_V2"] = SignalSpec(
            alpha_id="FAM-09-RV_COINT_ETH_BTC_V2",
            required_data=["OHLCV_4h_ETH", "OHLCV_4h_BTC"],
            builder=lambda: make_relative_value_signal(reference_df),
            economic_mechanism="Common-factor residual reversion between majors.",
        )
    else:
        registry["FAM-09-RV_COINT_ETH_BTC_V2"] = SignalSpec(
            alpha_id="FAM-09-RV_COINT_ETH_BTC_V2",
            required_data=["OHLCV_4h_ETH", "OHLCV_4h_BTC"],
            builder=None,
            availability_reason="DATA_UNAVAILABLE: reference leg not supplied.",
            economic_mechanism="Common-factor residual reversion between majors.",
        )

    return registry
    return _fn