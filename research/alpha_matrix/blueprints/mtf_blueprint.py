import numpy as np
import pandas as pd
from typing import Optional
from platform_core.alpha_genome import AlphaGenome, EconomicPerformance, AlphaFamily
from research.economic_evaluation_engine import CertifiedSeriesLoader


class MTFBlueprint:
    """
    Multi-Timeframe (MTF) Blueprint
    - HTF (e.g. 4h): Bias/Trend direction.
    - MTF (e.g. 15m): Setup/Structure.
    - LTF (e.g. 1m or 5m): Precise entry execution.
    """

    @staticmethod
    def construct_mtf_genome(symbol: str, ltf: str = "5m", mtf: str = "15m", htf: str = "4h") -> AlphaGenome:
        return AlphaGenome(
            alpha_id=f"ALPHA_MTF_{ltf}_{mtf}_{htf}_TREND",
            family=AlphaFamily.DIRECTIONAL,
            version="v1.0",
            asset_universe=[symbol],
            venues=["BINANCE"],
            instruments=["PERPETUAL"],
            timeframe=ltf,
            expected_holding_period_hours=24.0,
            economic_rationale="Multi-Timeframe aligned trend continuation with tight LTF entry and trailing stop.",
            features=["htf_ema_cross", "mtf_rsi_pullback", "ltf_momentum_breakout"],
            entry_mechanism="Momentum expansion aligned with MTF oversold and HTF trend.",
            exit_mechanism="Triple Barrier with 1:4 Reward/Risk and trailing stop.",
            performance=EconomicPerformance()
        )

    @staticmethod
    def _compute_htf_bias(df_htf: pd.DataFrame) -> pd.Series:
        """Returns 1 for LONG bias, -1 for SHORT bias, 0 for NEUTRAL."""
        close = df_htf["close"]
        ret = close.pct_change()
        vol = ret.rolling(20).std()
        mom = ret.rolling(5).mean()
        
        bias = pd.Series(0, index=df_htf.index)
        bias[(mom > 0.001) & (vol > vol.rolling(50).mean())] = 1
        bias[(mom < -0.001) & (vol > vol.rolling(50).mean())] = -1
        return bias

    @staticmethod
    def _compute_mtf_setup(df_mtf: pd.DataFrame) -> pd.Series:
        """Returns 1 for LONG setup, -1 for SHORT, 0 otherwise."""
        close = df_mtf["close"]
        ret = close.pct_change()
        vol = ret.rolling(20).std()
        mom = ret.rolling(5).mean()
        
        setup = pd.Series(0, index=df_mtf.index)
        setup[(mom > 0.001) & (vol > vol.rolling(50).mean())] = 1
        setup[(mom < -0.001) & (vol > vol.rolling(50).mean())] = -1
        return setup

    @staticmethod
    def _compute_ltf_entry(df_ltf: pd.DataFrame) -> pd.Series:
        """Returns 1 for LONG entry, -1 for SHORT."""
        # Institutional Causal Oracle Filter (momentum + volatility breakout)
        close = df_ltf["close"]
        ret = close.pct_change()
        vol = ret.rolling(20).std()
        mom = ret.rolling(5).mean()
        
        entry = pd.Series(0, index=df_ltf.index)
        
        # Long when momentum is positive and volatility is expanding (breakout)
        long_cond = (mom > 0.0005) & (vol > vol.rolling(50).mean())
        # Short when momentum is negative
        short_cond = (mom < -0.0005) & (vol > vol.rolling(50).mean())
        
        entry[long_cond] = 1
        entry[short_cond] = -1
        return entry

    @staticmethod
    def generate_mtf_signal(df_ltf: pd.DataFrame, symbol: str, mtf: str = "15m", htf: str = "4h") -> np.ndarray:
        loader = CertifiedSeriesLoader()
        try:
            df_mtf, _ = loader.load(symbol, mtf)
            df_htf, _ = loader.load(symbol, htf)
        except FileNotFoundError:
            # If higher timeframe data doesn't exist, we can't trade
            return np.zeros(len(df_ltf))

        # 1. Compute components
        htf_bias = MTFBlueprint._compute_htf_bias(df_htf)
        mtf_setup = MTFBlueprint._compute_mtf_setup(df_mtf)
        ltf_entry = MTFBlueprint._compute_ltf_entry(df_ltf)

        # 2. Align timestamps (forward fill HTF and MTF to LTF)
        # We must be careful not to introduce lookahead bias.
        # df_htf["timestamp"] is the OPEN time of the HTF bar.
        # It's only safe to use the HTF bar's data AFTER it closes.
        # Binance kline open_time + timeframe_ms = close_time.
        # However, our loader standardizes df["timestamp"] as the open time.
        # We need the close time of the HTF bar to map to the LTF bar.
        
        # A simpler causal alignment:
        # We set the index of the signals to df["timestamp"]
        htf_bias.index = df_htf["timestamp"]
        mtf_setup.index = df_mtf["timestamp"]
        ltf_entry_df = pd.DataFrame({"ltf_entry": ltf_entry.values}, index=df_ltf["timestamp"])

        # Shift HTF and MTF by 1 so the signal at T was computed at T-1's close,
        # meaning it is known from T onwards.
        htf_bias_shifted = htf_bias.shift(1)
        mtf_setup_shifted = mtf_setup.shift(1)

        # Reindex to LTF timestamps using forward fill.
        # This means at LTF time t, we look up the latest known shifted HTF/MTF signal.
        htf_aligned = htf_bias_shifted.reindex(ltf_entry_df.index, method="ffill").fillna(0)
        mtf_aligned = mtf_setup_shifted.reindex(ltf_entry_df.index, method="ffill").fillna(0)

        # 3. Combine rules
        # Long: HTF is 1, MTF is 1, LTF is 1
        # Short: HTF is -1, MTF is -1, LTF is -1
        signal = np.zeros(len(df_ltf))
        
        is_long = (htf_aligned == 1) & (mtf_aligned == 1) & (ltf_entry_df["ltf_entry"] == 1)
        is_short = (htf_aligned == -1) & (mtf_aligned == -1) & (ltf_entry_df["ltf_entry"] == -1)
        
        signal[is_long.values] = 1
        signal[is_short.values] = -1
        
        return signal
