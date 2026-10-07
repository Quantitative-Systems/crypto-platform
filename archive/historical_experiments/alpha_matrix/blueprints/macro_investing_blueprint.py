from platform_core.alpha_genome import AlphaGenome, AlphaFamily
from research.alpha_matrix.timeframe_governor import TimeframeGovernor, TradingStyle
import pandas as pd
import numpy as np

class MacroInvestingBlueprint:
    """
    Blueprint for Macro Investing strategies (1W - 1M).
    
    Captures extreme long-term fundamental trends, volatility risk premium, 
    and systemic regime shifts. Holding periods are strictly measured in months.
    """
    
    @staticmethod
    def construct_macro_trend_genome(symbol: str) -> AlphaGenome:
        """
        Creates an AlphaGenome for a Macro Trend following strategy.
        """
        genome = AlphaGenome(
            alpha_id=f"FAM-MACROINV-TREND-{symbol.replace('/', '')}",
            family=AlphaFamily.DIRECTIONAL,
            version="v1.0",
            asset_universe=[symbol],
            venues=["BINANCE"],
            instruments=["SPOT"],
            timeframe="1w",
            expected_holding_period_hours=2160.0, # 90 days
            economic_rationale="Captures multi-month capital influx and adoption cycles using slow moving averages.",
            features=["200_DAY_SMA", "MACRO_REGIME"],
            entry_mechanism="FUNDAMENTAL_VALUE",
            exit_mechanism="REGIME_SHIFT"
        )
        
        # Enforce physical constraints
        TimeframeGovernor.validate_genome(genome, TradingStyle.MACRO_INVESTING)
        
        return genome

    @staticmethod
    def generate_macro_signal(df: pd.DataFrame, slow_ma: int = 20, fast_ma: int = 5) -> np.ndarray:
        """
        Generates a macro trend signal using Weekly or Monthly bars.
        """
        close = df["close"]
        
        sma_slow = close.rolling(window=slow_ma).mean()
        sma_fast = close.rolling(window=fast_ma).mean()
        
        signal = np.zeros(len(df), dtype=int)
        
        # Golden Cross on Weekly/Monthly
        buy_cond = (sma_fast > sma_slow) & (sma_fast.shift(1) <= sma_slow.shift(1))
        signal[buy_cond] = 1
        
        # Death Cross
        sell_cond = (sma_fast < sma_slow) & (sma_fast.shift(1) >= sma_slow.shift(1))
        signal[sell_cond] = -1
        
        # Simple trend following: stay in as long as fast > slow
        # (This is a simplified signal, real one requires proper position state)
        
        return signal
