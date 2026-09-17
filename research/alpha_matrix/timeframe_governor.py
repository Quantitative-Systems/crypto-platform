from enum import Enum
from dataclasses import dataclass
from typing import List

class TradingStyle(Enum):
    MICRO_SCALP = "MICRO_SCALP"
    MACRO_SCALP = "MACRO_SCALP"
    INTRADAY = "INTRADAY"
    SWING = "SWING"
    POSITIONAL = "POSITIONAL"
    MACRO_INVESTING = "MACRO_INVESTING"


@dataclass
class StyleConstraints:
    style: TradingStyle
    allowed_timeframes: List[str]
    max_holding_hours: float
    min_holding_hours: float
    allowed_entry_mechanisms: List[str]
    allowed_exit_mechanisms: List[str]
    requires_maker_fees: bool
    requires_delta_neutral: bool


class TimeframeGovernor:
    """
    Enforces structural constraints on different trading styles to prevent
    the creation of mathematically doomed strategies (like directional scalping with taker fees).
    """
    
    # ---------------------------------------------------------
    # The Matrix Definitions
    # ---------------------------------------------------------
    MICRO_SCALP = StyleConstraints(
        style=TradingStyle.MICRO_SCALP,
        allowed_timeframes=["1m"],
        max_holding_hours=0.5,
        min_holding_hours=0.0,
        allowed_entry_mechanisms=["MAKER_LIMIT", "STAT_ARB", "MARKET_MAKING"],
        allowed_exit_mechanisms=["MAKER_LIMIT", "STAT_ARB", "MARKET_MAKING"],
        requires_maker_fees=True,
        requires_delta_neutral=True  # Short-term directional risk is pure noise
    )
    
    MACRO_SCALP = StyleConstraints(
        style=TradingStyle.MACRO_SCALP,
        allowed_timeframes=["5m"],
        max_holding_hours=2.0,
        min_holding_hours=0.05,
        allowed_entry_mechanisms=["TAKER_MARKET", "MAKER_LIMIT", "ORDER_FLOW"],
        allowed_exit_mechanisms=["TAKER_MARKET", "MAKER_LIMIT", "TIME_STOP"],
        requires_maker_fees=False, # Taker fees allowable if edge > 0.05%
        requires_delta_neutral=False
    )
    
    INTRADAY = StyleConstraints(
        style=TradingStyle.INTRADAY,
        allowed_timeframes=["15m", "1h"],
        max_holding_hours=24.0,
        min_holding_hours=0.5,
        allowed_entry_mechanisms=["TAKER_MARKET", "MAKER_LIMIT", "VWAP"],
        allowed_exit_mechanisms=["TAKER_MARKET", "MAKER_LIMIT", "VWAP", "TIME_STOP"],
        requires_maker_fees=False, 
        requires_delta_neutral=False
    )
    
    SWING = StyleConstraints(
        style=TradingStyle.SWING,
        allowed_timeframes=["4h"],
        max_holding_hours=336.0, # 14 days
        min_holding_hours=4.0,
        allowed_entry_mechanisms=["BREAKOUT", "PULLBACK", "TAKER_MARKET"],
        allowed_exit_mechanisms=["TRAILING_STOP", "FIXED_TARGET", "TIME_STOP"],
        requires_maker_fees=False,
        requires_delta_neutral=False
    )
    
    POSITIONAL = StyleConstraints(
        style=TradingStyle.POSITIONAL,
        allowed_timeframes=["1d"],
        max_holding_hours=8760.0, # 1 year
        min_holding_hours=72.0,
        allowed_entry_mechanisms=["FUNDING_ARBITRAGE", "MACRO_TREND"],
        allowed_exit_mechanisms=["REGIME_SHIFT", "FUNDING_REVERSAL"],
        requires_maker_fees=False,
        requires_delta_neutral=False
    )
    
    MACRO_INVESTING = StyleConstraints(
        style=TradingStyle.MACRO_INVESTING,
        allowed_timeframes=["1w", "1M"],
        max_holding_hours=87600.0, # 10 years
        min_holding_hours=336.0,
        allowed_entry_mechanisms=["FUNDAMENTAL_VALUE", "REGIME_SHIFT"],
        allowed_exit_mechanisms=["FUNDAMENTAL_VALUE", "REGIME_SHIFT"],
        requires_maker_fees=False,
        requires_delta_neutral=False
    )
    
    _matrix = {
        TradingStyle.MICRO_SCALP: MICRO_SCALP,
        TradingStyle.MACRO_SCALP: MACRO_SCALP,
        TradingStyle.INTRADAY: INTRADAY,
        TradingStyle.SWING: SWING,
        TradingStyle.POSITIONAL: POSITIONAL,
        TradingStyle.MACRO_INVESTING: MACRO_INVESTING
    }

    @classmethod
    def get_constraints(cls, style: TradingStyle) -> StyleConstraints:
        return cls._matrix[style]

    @classmethod
    def validate_genome(cls, genome: "AlphaGenome", style: TradingStyle) -> bool:
        """
        Validates that an AlphaGenome adheres to the rigid physical laws of the requested trading style.
        """
        constraints = cls.get_constraints(style)
        
        if genome.timeframe not in constraints.allowed_timeframes:
            raise ValueError(f"{style.name} requires timeframe in {constraints.allowed_timeframes}. Got {genome.timeframe}.")
            
        if genome.expected_holding_period_hours > constraints.max_holding_hours:
            raise ValueError(f"{style.name} holding period exceeds max {constraints.max_holding_hours}h.")
            
        if constraints.requires_maker_fees and genome.entry_mechanism not in constraints.allowed_entry_mechanisms:
            raise ValueError(f"{style.name} requires strictly {constraints.allowed_entry_mechanisms} entry to survive friction.")
            
        return True
