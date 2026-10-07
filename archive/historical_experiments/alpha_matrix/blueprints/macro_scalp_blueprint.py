from platform_core.alpha_genome import AlphaGenome, AlphaFamily
from research.alpha_matrix.timeframe_governor import TimeframeGovernor, TradingStyle
import pandas as pd
import numpy as np

class MacroScalpBlueprint:
    """
    Blueprint for Macro-Scalping strategies (5m).
    
    Captures localized mean reversion, volume spikes, and order flow imbalance
    over short horizons. Requires high edge to beat taker fees, or smart execution
    with limit orders.
    """
    
    @staticmethod
    def construct_orderflow_genome(symbol: str) -> AlphaGenome:
        """
        Creates an AlphaGenome for a Macro Scalping strategy.
        """
        genome = AlphaGenome(
            alpha_id=f"FAM-MACROSCALP-{symbol.replace('/', '')}",
            family=AlphaFamily.MICROSTRUCTURE,
            version="v1.0",
            asset_universe=[symbol],
            venues=["BINANCE"],
            instruments=["SPOT"],
            timeframe="5m",
            expected_holding_period_hours=1.0,
            economic_rationale="Fades volume absorption spikes using market orders if expected move > taker fees.",
            features=["VOLUME_SPIKE", "PRICE_REJECTION"],
            entry_mechanism="TAKER_MARKET",
            exit_mechanism="TAKER_MARKET"
        )
        
        # Enforce physical constraints
        TimeframeGovernor.validate_genome(genome, TradingStyle.MACRO_SCALP)
        
        return genome

    @staticmethod
    def generate_volume_fade_signal(df: pd.DataFrame, vol_mult: float = 15.0) -> np.ndarray:
        """
        Generates a 5m scalp signal fading massive volume spikes.
        """
        vol = df["volume"]
        close = df["close"]
        open_p = df["open"]
        
        # Simple volume moving average
        vol_ma = vol.rolling(window=20).mean()
        
        signal = np.zeros(len(df), dtype=int)
        
        # Massive volume spike on a red candle -> exhaust -> buy
        buy_cond = (vol > vol_ma * vol_mult) & (close < open_p)
        signal[buy_cond] = 1
        
        # Massive volume spike on a green candle -> exhaust -> sell
        sell_cond = (vol > vol_ma * vol_mult) & (close > open_p)
        signal[sell_cond] = -1
        
        return signal
