from platform_core.alpha_genome import AlphaGenome, AlphaFamily
from research.alpha_matrix.timeframe_governor import TimeframeGovernor, TradingStyle
import pandas as pd
import numpy as np

class PositionalBlueprint:
    """
    Blueprint for Positional strategies (1D - 1W).
    
    Captures long-term structural edges such as Funding Arbitrage, Carry Trade, and
    Macro trend following. Holding periods range from days to months.
    """
    
    @staticmethod
    def construct_funding_arb_genome(symbol: str) -> AlphaGenome:
        """
        Creates an AlphaGenome for a Positional Funding Arbitrage strategy.
        This builds directly on the successful EABG-004 logic.
        """
        genome = AlphaGenome(
            alpha_id=f"FAM-POS-CARRY-{symbol.replace('/', '')}",
            family=AlphaFamily.ARBITRAGE, # Close enough for Carry
            version="v2.0", # v2 indicates integration into the Matrix
            asset_universe=[symbol],
            venues=["BINANCE"],
            instruments=["SPOT", "PERPETUAL"],
            timeframe="1d",
            expected_holding_period_hours=336.0, # 14 days
            economic_rationale="Captures persistent positive funding rates in crypto derivatives by shorting perpetuals and holding spot delta-neutral.",
            features=["FUNDING_RATE_SMA", "BASIS_SPREAD"],
            entry_mechanism="FUNDING_ARBITRAGE",
            exit_mechanism="FUNDING_REVERSAL"
        )
        
        # Enforce physical constraints
        TimeframeGovernor.validate_genome(genome, TradingStyle.POSITIONAL)
        
        return genome
        
    @staticmethod
    def generate_funding_signal(df: pd.DataFrame, funding_df: pd.DataFrame, threshold: float = 0.0001, window: int = 14) -> np.ndarray:
        """
        Generates a positional carry signal based on persistent positive funding.
        Assumes funding data is aligned to daily bars.
        """
        # Create a time-aligned series
        funding_rate = funding_df.set_index("timestamp")["funding_rate"].astype(float)
        
        # Align funding dates to df dates using forward fill
        aligned_funding = pd.Series(index=df["timestamp"], dtype=float)
        
        # Convert df timestamps to ms if necessary
        df_ts = (df["timestamp"] - pd.Timestamp("1970-01-01", tz="utc")) // pd.Timedelta("1ms")
        
        for i, ts in enumerate(df_ts):
            # Get the most recent funding rate before or at this bar
            past_rates = funding_rate[funding_rate.index <= ts]
            if not past_rates.empty:
                aligned_funding.iloc[i] = past_rates.iloc[-1]
            else:
                aligned_funding.iloc[i] = 0.0
                
        # Calculate moving average of funding rate to avoid noise
        sma_funding = aligned_funding.rolling(window=window).mean()
        
        signal = np.zeros(len(df), dtype=int)
        
        # Enter the carry trade (Short Perp, Long Spot) when average funding > threshold
        signal[sma_funding > threshold] = 1 # Return 1 for Hold position (Funding Arb engine expects 1 or 0)
        
        return signal
