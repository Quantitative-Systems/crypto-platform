from platform_core.alpha_genome import AlphaGenome, AlphaFamily
from research.alpha_matrix.timeframe_governor import TimeframeGovernor, TradingStyle
import pandas as pd
import numpy as np
from typing import Callable, Dict, Any

class ScalpBlueprint:
    """
    Blueprint for High-Frequency / Scalping strategies.
    
    WARNING: Directional scalping with taker fees on Binance is mathematically unprofitable.
    This blueprint focuses ONLY on Maker-Maker Statistical Arbitrage (Pairs Trading) or 
    Passive Liquidity Provision models.
    """
    
    @staticmethod
    def construct_statarb_genome(symbol_pair: str) -> AlphaGenome:
        """
        Creates an AlphaGenome for a Statistical Arbitrage pair (e.g. BTC-ETH).
        Requires delta neutrality and limit order execution.
        """
        genome = AlphaGenome(
            alpha_id=f"FAM-SCALP-STATARB-{symbol_pair.replace('/', '')}",
            family=AlphaFamily.STAT_ARB,
            version="v1.0",
            asset_universe=[symbol_pair],  # e.g. "BTC/USDT-ETH/USDT"
            venues=["BINANCE"],
            instruments=["SPOT", "PERPETUAL"],
            timeframe="1m",
            expected_holding_period_hours=0.5,
            economic_rationale="Captures short-term pricing inefficiencies between highly correlated assets using limit orders to earn maker rebates or avoid taker fees.",
            features=["Z_SCORE_SPREAD", "COINTEGRATION_RANK"],
            entry_mechanism="MAKER_LIMIT",
            exit_mechanism="MAKER_LIMIT"
        )
        
        # Enforce physical constraints
        TimeframeGovernor.validate_genome(genome, TradingStyle.MICRO_SCALP)
        
        return genome

    @staticmethod
    def generate_zscore_signal(df_leg1: pd.DataFrame, df_leg2: pd.DataFrame, window: int = 60, entry_z: float = 3.5) -> np.ndarray:
        """
        Generates a pairs trading signal based on the spread z-score.
        1 = Long Leg1, Short Leg2
        -1 = Short Leg1, Long Leg2
        0 = Flat
        """
        # Ensure lengths match
        min_len = min(len(df_leg1), len(df_leg2))
        c1 = df_leg1["close"].to_numpy()[-min_len:]
        c2 = df_leg2["close"].to_numpy()[-min_len:]
        
        # Calculate spread (log prices are better but this is a simplified template)
        spread = c1 - c2
        
        # Moving average and standard deviation
        spread_s = pd.Series(spread)
        ma = spread_s.rolling(window).mean()
        std = spread_s.rolling(window).std()
        
        z_score = (spread_s - ma) / std
        
        signal = np.zeros(min_len, dtype=int)
        
        # Naive vectorized entry logic for demonstration
        # 1 means spread is unusually low -> buy the spread (buy leg1, sell leg2)
        signal[z_score < -entry_z] = 1
        
        # -1 means spread is unusually high -> sell the spread (sell leg1, buy leg2)
        signal[z_score > entry_z] = -1
        
        # Exit when reverting to mean
        signal[np.abs(z_score) < 0.5] = 0
        
        # Forward fill the signal to hold positions (naive)
        s_df = pd.Series(signal).replace(0, np.nan).ffill().fillna(0)
        signal = s_df.to_numpy()
        # We need to correctly handle the 0 condition (flat), this is just a stub implementation
        
        return signal
