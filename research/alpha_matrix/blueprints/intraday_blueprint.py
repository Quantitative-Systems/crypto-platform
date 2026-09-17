from platform_core.alpha_genome import AlphaGenome, AlphaFamily
from research.alpha_matrix.timeframe_governor import TimeframeGovernor, TradingStyle
import pandas as pd
import numpy as np

class IntradayBlueprint:
    """
    Blueprint for Intraday strategies (15m - 1H).
    
    Captures localized mean-reversion, VWAP imbalances, and order flow momentum.
    Holding periods range from 30 minutes to 24 hours.
    Taker fees are permissible only if the expected edge exceeds 0.15% per trade.
    """
    
    @staticmethod
    def construct_mean_reversion_genome(symbol: str) -> AlphaGenome:
        """
        Creates an AlphaGenome for an Intraday Mean Reversion strategy.
        """
        genome = AlphaGenome(
            alpha_id=f"FAM-INTRA-MR-{symbol.replace('/', '')}",
            family=AlphaFamily.MEAN_REVERSION,
            version="v1.0",
            asset_universe=[symbol],
            venues=["BINANCE"],
            instruments=["SPOT"],
            timeframe="15m",
            expected_holding_period_hours=4.0,
            economic_rationale="Capitalizes on short-term liquidity voids and over-extensions by fading sharp localized moves.",
            features=["RSI_EXTREME", "BOLLINGER_BAND_WIDTH"],
            entry_mechanism="TAKER_MARKET",
            exit_mechanism="TAKER_MARKET"
        )
        
        # Enforce physical constraints
        TimeframeGovernor.validate_genome(genome, TradingStyle.INTRADAY)
        
        return genome
        
    @staticmethod
    def generate_rsi_fade_signal(df: pd.DataFrame, rsi_period: int = 14, overbought: float = 85.0, oversold: float = 15.0) -> np.ndarray:
        """
        Generates a naive intraday fade signal based on extreme RSI with a massive trend filter.
        """
        # Note: True RSI calculation requires full Wilder's smoothing. This is a placeholder.
        close = df["close"]
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        ema_200 = close.ewm(span=200, adjust=False).mean()
        
        signal = np.zeros(len(df), dtype=int)
        
        # Only buy if deeply oversold AND in a macro uptrend
        signal[(rsi < oversold) & (close > ema_200)] = 1   # Long
        
        # Only sell if deeply overbought AND in a macro downtrend
        signal[(rsi > overbought) & (close < ema_200)] = -1 # Short
        
        return signal
