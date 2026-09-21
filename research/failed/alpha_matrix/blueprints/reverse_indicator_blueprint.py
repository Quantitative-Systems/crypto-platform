import pandas as pd
import pandas_ta as ta
import numpy as np

from platform_core.alpha_genome import AlphaGenome, EconomicPerformance, AlphaFamily

class ReverseIndicatorBlueprint:
    @staticmethod
    def construct_genome(asset: str, ltf: str, mtf: str, htf: str) -> AlphaGenome:
        """
        Creates a strategy genome that runs the reverse structure,
        flagging which style we are testing so we know which indicators to use.
        """
        return AlphaGenome(
            alpha_id=f"REVERSE_MTF_{ltf}_{mtf}_{htf}_{asset.replace('/', '')}",
            family=AlphaFamily.DIRECTIONAL,
            version="v2.0",
            asset_universe=[asset],
            venues=["BINANCE"],
            instruments=["PERPETUAL"],
            timeframe=ltf,
            expected_holding_period_hours=24.0,
            economic_rationale="Inverse Timeframe Alignment (Robust Strategy)",
            features=["htf_bias", "mtf_setup", "ltf_entry"],
            entry_mechanism="Highly-Filtered Inverse Multi-Timeframe",
            exit_mechanism="Triple Barrier with >1:4 Reward/Risk and trailing stop.",
            performance=EconomicPerformance()
        )

    @staticmethod
    def get_style_from_timeframes(htf: str) -> str:
        if htf == '1M': return 'SCALPING'
        elif htf == '1w': return 'INTRADAY'
        elif htf == '1d': return 'SWING'
        elif htf == '4h': return 'POSITIONAL'
        elif htf == '1h': return 'INVESTING'
        elif htf == '15m': return 'MACRO'
        return 'UNKNOWN'

    @staticmethod
    def generate_signal(df_ltf: pd.DataFrame, asset: str, mtf: str, htf: str) -> pd.Series:
        from research.economic_evaluation_engine import CertifiedSeriesLoader
        loader = CertifiedSeriesLoader()
        try:
            df_mtf, _ = loader.load(asset, mtf)
            df_htf, _ = loader.load(asset, htf)
        except FileNotFoundError:
            return pd.Series(0, index=df_ltf.index)

        style = ReverseIndicatorBlueprint.get_style_from_timeframes(htf)

        df_htf = df_htf.copy()
        df_mtf = df_mtf.copy()
        df_ltf = df_ltf.copy()

        # Helper functions
        def get_series(df, col_name, default_val=0):
            return df[col_name] if col_name in df.columns else pd.Series(default_val, index=df.index)

        if style == 'SCALPING':
            # 1. SCALPING (HTF: 1M, MTF: 1w, LTF: 1d)
            # Remove ADX since it blocks almost all trades on Monthly
            df_htf.ta.supertrend(length=20, multiplier=4.0, append=True)
            df_htf['htf_bull'] = get_series(df_htf, 'SUPERTd_20_4.0') == 1
            df_htf['htf_bear'] = get_series(df_htf, 'SUPERTd_20_4.0') == -1

            df_mtf.ta.stoch(k=14, d=3, smooth_k=3, append=True)
            k_mtf = get_series(df_mtf, 'STOCHk_14_3_3')
            df_mtf['mtf_bull'] = k_mtf < 40
            df_mtf['mtf_bear'] = k_mtf > 60

            df_ltf.ta.stoch(k=14, d=3, smooth_k=3, append=True)
            df_ltf.ta.ema(length=9, append=True)
            k_ltf = get_series(df_ltf, 'STOCHk_14_3_3')
            d_ltf = get_series(df_ltf, 'STOCHd_14_3_3')
            ema9 = get_series(df_ltf, 'EMA_9')
            df_ltf['ltf_bull'] = (k_ltf > d_ltf) & (k_ltf.shift(1) <= d_ltf.shift(1)) & (df_ltf['close'] > ema9)
            df_ltf['ltf_bear'] = (k_ltf < d_ltf) & (k_ltf.shift(1) >= d_ltf.shift(1)) & (df_ltf['close'] < ema9)

        elif style == 'INTRADAY':
            # 2. INTRADAY (HTF: 1w, MTF: 1d, LTF: 4h)
            df_htf.ta.ema(length=50, append=True)
            df_htf.ta.ema(length=100, append=True)
            ema50 = get_series(df_htf, 'EMA_50')
            ema100 = get_series(df_htf, 'EMA_100')
            df_htf['htf_bull'] = (df_htf['close'] > ema50) & (ema50 > ema100)
            df_htf['htf_bear'] = (df_htf['close'] < ema50) & (ema50 < ema100)

            df_mtf.ta.supertrend(length=14, multiplier=3.0, append=True)
            df_mtf.ta.stoch(k=14, d=3, smooth_k=3, append=True)
            df_mtf['mtf_bull'] = (get_series(df_mtf, 'SUPERTd_14_3.0') == 1) & (get_series(df_mtf, 'STOCHk_14_3_3') < 50)
            df_mtf['mtf_bear'] = (get_series(df_mtf, 'SUPERTd_14_3.0') == -1) & (get_series(df_mtf, 'STOCHk_14_3_3') > 50)

            df_ltf.ta.stoch(k=21, d=5, smooth_k=3, append=True)
            k_ltf = get_series(df_ltf, 'STOCHk_21_5_3')
            d_ltf = get_series(df_ltf, 'STOCHd_21_5_3')
            df_ltf['ltf_bull'] = (k_ltf > d_ltf) & (k_ltf.shift(1) <= d_ltf.shift(1))
            df_ltf['ltf_bear'] = (k_ltf < d_ltf) & (k_ltf.shift(1) >= d_ltf.shift(1))

        elif style == 'SWING':
            # 3. SWING (HTF: 1d, MTF: 4h, LTF: 1h)
            df_htf.ta.supertrend(length=10, multiplier=2.0, append=True)
            df_htf.ta.ema(length=100, append=True)
            ema100 = get_series(df_htf, 'EMA_100')
            df_htf['htf_bull'] = (get_series(df_htf, 'SUPERTd_10_2.0') == 1) & (df_htf['close'] > ema100)
            df_htf['htf_bear'] = (get_series(df_htf, 'SUPERTd_10_2.0') == -1) & (df_htf['close'] < ema100)

            df_mtf.ta.ema(length=50, append=True)
            df_mtf.ta.rsi(length=14, append=True)
            ema50 = get_series(df_mtf, 'EMA_50')
            rsi_mtf = get_series(df_mtf, 'RSI_14')
            df_mtf['mtf_bull'] = (df_mtf['close'] > ema50) & (rsi_mtf < 50)
            df_mtf['mtf_bear'] = (df_mtf['close'] < ema50) & (rsi_mtf > 50)

            df_ltf.ta.stoch(k=14, d=3, smooth_k=3, append=True)
            df_ltf.ta.supertrend(length=10, multiplier=2.0, append=True)
            k_ltf = get_series(df_ltf, 'STOCHk_14_3_3')
            d_ltf = get_series(df_ltf, 'STOCHd_14_3_3')
            st_dir = get_series(df_ltf, 'SUPERTd_10_2.0')
            df_ltf['ltf_bull'] = (k_ltf > d_ltf) & (k_ltf.shift(1) <= d_ltf.shift(1)) & (st_dir == 1)
            df_ltf['ltf_bear'] = (k_ltf < d_ltf) & (k_ltf.shift(1) >= d_ltf.shift(1)) & (st_dir == -1)

        elif style == 'POSITIONAL':
            # 4. POSITIONAL (HTF: 4h, MTF: 1h, LTF: 15m)
            df_htf.ta.ema(length=50, append=True)
            df_htf.ta.ema(length=200, append=True)
            df_htf.ta.adx(length=14, append=True)
            ema50 = get_series(df_htf, 'EMA_50')
            ema200 = get_series(df_htf, 'EMA_200')
            adx_htf = get_series(df_htf, 'ADX_14')
            df_htf['htf_bull'] = (ema50 > ema200) & (adx_htf > 20)
            df_htf['htf_bear'] = (ema50 < ema200) & (adx_htf > 20)

            df_mtf.ta.stoch(k=30, d=10, smooth_k=10, append=True)
            k_mtf = get_series(df_mtf, 'STOCHk_30_10_10')
            df_mtf['mtf_bull'] = k_mtf < 40
            df_mtf['mtf_bear'] = k_mtf > 60

            df_ltf.ta.supertrend(length=7, multiplier=1.5, append=True)
            df_ltf.ta.ema(length=20, append=True)
            st_dir = get_series(df_ltf, 'SUPERTd_7_1.5')
            ema20 = get_series(df_ltf, 'EMA_20')
            df_ltf['ltf_bull'] = (st_dir == 1) & (st_dir.shift(1) == -1) & (df_ltf['close'] > ema20)
            df_ltf['ltf_bear'] = (st_dir == -1) & (st_dir.shift(1) == 1) & (df_ltf['close'] < ema20)

        elif style == 'INVESTING':
            # 5. INVESTING (HTF: 1h, MTF: 15m, LTF: 5m)
            df_htf.ta.supertrend(length=30, multiplier=5.0, append=True)
            df_htf.ta.ema(length=100, append=True)
            ema100 = get_series(df_htf, 'EMA_100')
            st_dir = get_series(df_htf, 'SUPERTd_30_5.0')
            df_htf['htf_bull'] = (st_dir == 1) & (df_htf['close'] > ema100)
            df_htf['htf_bear'] = (st_dir == -1) & (df_htf['close'] < ema100)

            df_mtf.ta.ema(length=20, append=True)
            df_mtf.ta.stoch(k=14, d=3, smooth_k=3, append=True)
            ema20 = get_series(df_mtf, 'EMA_20')
            k_mtf = get_series(df_mtf, 'STOCHk_14_3_3')
            df_mtf['mtf_bull'] = (df_mtf['close'] > ema20) & (k_mtf < 40)
            df_mtf['mtf_bear'] = (df_mtf['close'] < ema20) & (k_mtf > 60)

            df_ltf.ta.stoch(k=14, d=3, smooth_k=3, append=True)
            k_ltf = get_series(df_ltf, 'STOCHk_14_3_3')
            d_ltf = get_series(df_ltf, 'STOCHd_14_3_3')
            df_ltf['ltf_bull'] = (k_ltf > d_ltf) & (k_ltf.shift(1) <= d_ltf.shift(1)) & (k_ltf < 30)
            df_ltf['ltf_bear'] = (k_ltf < d_ltf) & (k_ltf.shift(1) >= d_ltf.shift(1)) & (k_ltf > 70)

        elif style == 'MACRO':
            # 6. MACRO (HTF: 15m, MTF: 5m, LTF: 1m)
            # Inverse of Macro Investing -> looking for extreme oversold conditions on LTF 
            df_htf.ta.stoch(k=50, d=10, smooth_k=3, append=True)
            df_htf.ta.ema(length=50, append=True)
            k_htf = get_series(df_htf, 'STOCHk_50_10_3')
            d_htf = get_series(df_htf, 'STOCHd_50_10_3')
            ema50_htf = get_series(df_htf, 'EMA_50')
            df_htf['htf_bull'] = (k_htf > d_htf) & (df_htf['close'] > ema50_htf)
            df_htf['htf_bear'] = (k_htf < d_htf) & (df_htf['close'] < ema50_htf)

            df_mtf.ta.rsi(length=14, append=True)
            rsi_mtf = get_series(df_mtf, 'RSI_14')
            df_mtf['mtf_bull'] = rsi_mtf < 45
            df_mtf['mtf_bear'] = rsi_mtf > 55

            df_ltf.ta.rsi(length=14, append=True)
            df_ltf.ta.stoch(k=14, d=3, smooth_k=3, append=True)
            rsi_ltf = get_series(df_ltf, 'RSI_14')
            k_ltf = get_series(df_ltf, 'STOCHk_14_3_3')
            d_ltf = get_series(df_ltf, 'STOCHd_14_3_3')
            df_ltf['ltf_bull'] = (rsi_ltf < 30) & (k_ltf > d_ltf) & (k_ltf.shift(1) <= d_ltf.shift(1))
            df_ltf['ltf_bear'] = (rsi_ltf > 70) & (k_ltf < d_ltf) & (k_ltf.shift(1) >= d_ltf.shift(1))

        else:
            df_ltf['ltf_bull'] = False
            df_ltf['ltf_bear'] = False

        # --- ALIGNMENT LOGIC ---
        df_ltf['htf_bull_ffill'] = df_htf['htf_bull'].reindex(df_ltf.index, method='ffill')
        df_ltf['htf_bear_ffill'] = df_htf['htf_bear'].reindex(df_ltf.index, method='ffill')
        
        df_ltf['mtf_bull_ffill'] = df_mtf['mtf_bull'].reindex(df_ltf.index, method='ffill')
        df_ltf['mtf_bear_ffill'] = df_mtf['mtf_bear'].reindex(df_ltf.index, method='ffill')

        signal = pd.Series(0, index=df_ltf.index)
        
        bull_cond = df_ltf['htf_bull_ffill'] & df_ltf['mtf_bull_ffill'] & df_ltf['ltf_bull']
        bear_cond = df_ltf['htf_bear_ffill'] & df_ltf['mtf_bear_ffill'] & df_ltf['ltf_bear']

        signal[bull_cond] = 1
        signal[bear_cond] = -1

        return signal
