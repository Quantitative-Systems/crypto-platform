from platform_core.alpha_genome import AlphaGenome, AlphaFamily
from research.alpha_matrix.timeframe_governor import TimeframeGovernor, TradingStyle
import pandas as pd
import numpy as np

class SwingBlueprint:
    """
    Blueprint for Swing strategies (4H - 1D).
    
    Captures structural momentum, KeyZone breakouts, and multi-day macro trends.
    Holding periods range from 4 hours to 14 days.
    """
    
    @staticmethod
    def construct_momentum_genome(symbol: str) -> AlphaGenome:
        """
        Creates an AlphaGenome for a Swing Momentum strategy.
        """
        genome = AlphaGenome(
            alpha_id=f"FAM-SWING-MOM-{symbol.replace('/', '')}",
            family=AlphaFamily.MOMENTUM,
            version="v1.0",
            asset_universe=[symbol],
            venues=["BINANCE"],
            instruments=["SPOT"],
            timeframe="4h",
            expected_holding_period_hours=72.0,
            economic_rationale="Captures multi-day persistent trends driven by broad market liquidity flows.",
            features=["MACD_CROSSOVER", "ATR_BREAKOUT"],
            entry_mechanism="BREAKOUT",
            exit_mechanism="TRAILING_STOP"
        )
        
        # Enforce physical constraints
        TimeframeGovernor.validate_genome(genome, TradingStyle.SWING)
        
        return genome
        
    @staticmethod
    def generate_macd_signal(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal_period: int = 9) -> np.ndarray:
        """
        Generates a swing momentum signal based on MACD crossovers with a massive trend filter.
        """
        close = df["close"]
        
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal_period, adjust=False).mean()
        
        ema_200 = close.ewm(span=200, adjust=False).mean()
        
        hist = macd - macd_signal
        hist_std = hist.rolling(100, min_periods=10).std().fillna(0)
        
        signal = np.zeros(len(df), dtype=int)
        
        # Go long when MACD histogram is strongly positive and in a macro uptrend
        signal[(hist > 0) & (hist > hist_std * 1.5) & (close > ema_200)] = 1
        # Go short when MACD histogram is strongly negative and in a macro downtrend
        signal[(hist < 0) & (hist < -hist_std * 1.5) & (close < ema_200)] = -1
        
        return signal
