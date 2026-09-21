"""
Quantitative Crypto Platform (QCP) — Time-Series Momentum Strategy
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from research.economic_evaluation_engine import compute_atr
from strategy_engine.factory.base_strategy import BaseStrategy
from platform_core.alpha_genome import AlphaFamily


class TimeSeriesMomentumStrategy(BaseStrategy):
    """
    Family: Time-Series Momentum (TSMOM)
    Hypothesis: Absolute past performance over N periods positively predicts 
    future performance due to behavioral underreaction and flow persistence.
    """

    def __init__(self, strategy_id: str, symbol: str, timeframe: str = "4h", parameters: Optional[Dict[str, Any]] = None):
        super().__init__(strategy_id, AlphaFamily.DIRECTIONAL, symbol, timeframe, parameters)

    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        lookback = self.params.get("lookback", 60)
        vol_scaled = self.params.get("vol_scaled", False)

        # Standard sign of return
        past_returns = df["close"].pct_change(periods=lookback).shift(1)

        sig = np.zeros(len(df))

        if not vol_scaled:
            sig[(past_returns > 0).fillna(False).to_numpy()] = 1.0
            sig[(past_returns < 0).fillna(False).to_numpy()] = -1.0
        else:
            # Volatility-scaled signal
            atr = compute_atr(df, lookback)
            # Normalize past returns by ATR
            # We treat strong vol-adjusted trends as active signals
            scaled_momentum = (df["close"] - df["close"].shift(lookback)) / atr
            scaled_momentum = scaled_momentum.shift(1)
            
            sig[(scaled_momentum > 0.5).fillna(False).to_numpy()] = 1.0
            sig[(scaled_momentum < -0.5).fillna(False).to_numpy()] = -1.0

        return sig

    def get_parameter_grid(self) -> List[Dict[str, Any]]:
        grid = []
        for lookback in [20, 60, 120, 240]:
            for vol_scaled in [False, True]:
                grid.append({
                    "lookback": lookback,
                    "vol_scaled": vol_scaled
                })
        return grid
