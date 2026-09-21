"""
QCP Strategy Grammar Components.
Defines the strict interfaces and registry for modular market mechanisms.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

class AbstractComponent(ABC):
    """Base class for all QCP grammar components."""
    def __init__(self, component_id: str, description: str):
        self.id = component_id
        self.description = description
        self.required_data: List[str] = []
        self.timeframe_compatibility: List[str] = []
        self.parameters: Dict[str, Any] = {}
        self.causal_requirements: List[str] = []
        self.failure_conditions: List[str] = []

class AbstractBias(AbstractComponent):
    def __init__(self, component_id: str, description: str):
        super().__init__(component_id, description)
        self.neutral_state: bool = False
        self.regime_compatibility: List[str] = []

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        """Returns (bullish_bias, bearish_bias) boolean masks."""
        pass

class AbstractSetup(AbstractComponent):
    def __init__(self, component_id: str, description: str):
        super().__init__(component_id, description)
        self.regime_compatibility: List[str] = []

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, scale: int) -> Tuple[pd.Series, pd.Series]:
        """Returns (bullish_setup, bearish_setup) boolean masks."""
        pass

class AbstractEntry(AbstractComponent):
    def __init__(self, component_id: str, description: str):
        super().__init__(component_id, description)
        self.regime_compatibility: List[str] = []

    @abstractmethod
    def evaluate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """Returns (bullish_entry, bearish_entry) boolean masks."""
        pass

class AbstractStopLoss(AbstractComponent):
    @abstractmethod
    def evaluate(self, df: pd.DataFrame, direction: pd.Series, scale: int = 1) -> pd.Series:
        """
        Returns absolute price level for the stop loss.
        direction is a Series of 1 (long) and -1 (short).
        """
        pass

class AbstractTakeProfit(AbstractComponent):
    @abstractmethod
    def evaluate(self, df: pd.DataFrame, direction: pd.Series, stop_loss: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        """
        Returns absolute price level for the take profit.
        """
        pass

class AbstractTrailing(AbstractComponent):
    @abstractmethod
    def evaluate(self, df: pd.DataFrame, direction: pd.Series, current_stop: pd.Series, htf_scale: int = 1, mtf_scale: int = 1) -> pd.Series:
        """
        Calculates trailing stops during position hold.
        """
        pass

class ComponentRegistry:
    """Central registry for all strategy grammar components."""
    _biases: Dict[str, AbstractBias] = {}
    _setups: Dict[str, AbstractSetup] = {}
    _entries: Dict[str, AbstractEntry] = {}
    _stop_losses: Dict[str, AbstractStopLoss] = {}
    _take_profits: Dict[str, AbstractTakeProfit] = {}
    _trailings: Dict[str, AbstractTrailing] = {}

    @classmethod
    def register(cls, component: Any) -> None:
        if isinstance(component, AbstractBias):
            cls._biases[component.id] = component
        elif isinstance(component, AbstractSetup):
            cls._setups[component.id] = component
        elif isinstance(component, AbstractEntry):
            cls._entries[component.id] = component
        elif isinstance(component, AbstractStopLoss):
            cls._stop_losses[component.id] = component
        elif isinstance(component, AbstractTakeProfit):
            cls._take_profits[component.id] = component
        elif isinstance(component, AbstractTrailing):
            cls._trailings[component.id] = component
        else:
            raise ValueError(f"Unknown component type: {type(component)}")

    @classmethod
    def get_bias(cls, id: str) -> AbstractBias: return cls._biases[id]
    @classmethod
    def get_setup(cls, id: str) -> AbstractSetup: return cls._setups[id]
    @classmethod
    def get_entry(cls, id: str) -> AbstractEntry: return cls._entries[id]
    @classmethod
    def get_stop_loss(cls, id: str) -> AbstractStopLoss: return cls._stop_losses[id]
    @classmethod
    def get_take_profit(cls, id: str) -> AbstractTakeProfit: return cls._take_profits[id]
    @classmethod
    def get_trailing(cls, id: str) -> AbstractTrailing: return cls._trailings[id]
