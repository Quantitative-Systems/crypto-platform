"""Crypto Trading Platform — Strategy Engine Subsystem & Plugin Framework."""
from .base import BaseStrategy
from .funding_carry import FundingCarryStrategy
from .investing import SystematicInvestingStrategy
from .mean_reversion import BollingerMeanReversionStrategy
from .momentum import MomentumStrategy
from .statistical_arbitrage import PairsTradingStrategy
from .trend import TrendBreakoutStrategy
from .volatility import VolatilityExpansionStrategy

__all__ = [
    "BaseStrategy",
    "TrendBreakoutStrategy",
    "BollingerMeanReversionStrategy",
    "MomentumStrategy",
    "PairsTradingStrategy",
    "FundingCarryStrategy",
    "VolatilityExpansionStrategy",
    "SystematicInvestingStrategy",
]
