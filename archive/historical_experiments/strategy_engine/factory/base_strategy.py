"""
Quantitative Crypto Platform (QCP) — Pluggable Base Strategy Interface.

Abstract contract for all strategy families in QCP. Every strategy evaluates
market data causally and emits trading signals {-1.0, 0.0, 1.0} or OrderIntents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


class SignalDirection(float, Enum):
    SHORT = -1.0
    NEUTRAL = 0.0
    LONG = 1.0


@dataclass
class StrategyParameters:
    parameters: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.parameters.get(key, default)


class BaseStrategy(ABC):
    """
    Universal strategy plugin interface.
    """

    def __init__(self, strategy_id: str, family: str, symbol: str, timeframe: str = "4h", parameters: Optional[Dict[str, Any]] = None):
        self.strategy_id = strategy_id
        self.family = family
        self.symbol = symbol
        self.timeframe = timeframe
        self.params = StrategyParameters(parameters or {})

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> np.ndarray:
        """
        Causal evaluation: signal[i] MUST use ONLY data available at or before close of bar i.
        Returns array of float values: +1.0 (Long), -1.0 (Short), 0.0 (Neutral).
        """
        pass

    def get_parameter_grid(self) -> List[Dict[str, Any]]:
        """Returns parameter search grid for research discovery."""
        return [self.params.parameters]
