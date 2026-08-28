from typing import List, Optional
from market_intelligence.primitives import Candle

class DataCertifier:
    """
    Data Quality Certification Contract.
    Asserts integrity of loaded datasets before they enter the simulation pipeline.
    """

    @staticmethod
    def _tf_to_seconds(tf: str) -> int:
        tf = tf.upper()
        if tf == "15M": return 15 * 60
        if tf == "1H": return 3600
        if tf == "4H": return 4 * 3600
        if tf == "1D": return 24 * 3600
        if tf == "1W": return 7 * 24 * 3600
        if tf == "1M": return 30 * 24 * 3600
        raise ValueError(f"Unknown timeframe: {tf}")

    @staticmethod
    def certify_dataset(candles: List[Candle], timeframe: str, symbol: str, allow_gaps: bool = False, max_allowed_gap_bars: int = 12) -> bool:
        """
        Certifies a single dataset for OHLC integrity, timestamp ordering, and duplicates.
        Raises ValueError if certification fails.
        """
        if not candles:
            raise ValueError(f"[{symbol} {timeframe}] Dataset is empty.")

        expected_interval_sec = DataCertifier._tf_to_seconds(timeframe)
        
        # Check first candle OHLC
        for i, c in enumerate(candles):
            if c.high < c.low:
                raise ValueError(f"[{symbol} {timeframe}] Invalid OHLC (High < Low) at {c.timestamp}")
            if c.close > c.high or c.close < c.low:
                raise ValueError(f"[{symbol} {timeframe}] Invalid OHLC (Close outside High/Low) at {c.timestamp}")
            
            if i > 0:
                prev = candles[i-1]
                time_diff = c.timestamp - prev.timestamp
                
                if time_diff <= 0:
                    raise ValueError(f"[{symbol} {timeframe}] Non-chronological or duplicate timestamp at {c.timestamp}")
                    
                # Strict continuity check (for continuous markets like Crypto, exact interval is expected)
                # Allow some leniency for 1M (months have different days)
                if timeframe != "1M" and time_diff > expected_interval_sec:
                    gap_bars = (time_diff / expected_interval_sec) - 1
                    if not allow_gaps:
                        raise ValueError(f"[{symbol} {timeframe}] Gap detected at {c.timestamp}. Missing {int(gap_bars)} bars.")
                    elif gap_bars > max_allowed_gap_bars:
                        raise ValueError(f"[{symbol} {timeframe}] Gap detected at {c.timestamp}. Missing {int(gap_bars)} bars exceeds allowable threshold of {max_allowed_gap_bars}.")
                    else:
                        print(f"⚠️ [WARNING] [{symbol} {timeframe}] Gap detected at {c.timestamp}. Missing {gap_bars} bars.")

        return True

    @staticmethod
    def certify_overlap(htf_candles: List[Candle], mtf_candles: List[Candle], ltf_candles: List[Candle], min_lookback_bars: int = 100) -> bool:
        """
        Certifies that HTF and MTF datasets start early enough to provide warmup context 
        before the LTF dataset begins.
        """
        if not htf_candles or not mtf_candles or not ltf_candles:
            raise ValueError("Cannot certify overlap with empty datasets.")

        htf_start = htf_candles[0].timestamp
        mtf_start = mtf_candles[0].timestamp
        ltf_start = ltf_candles[0].timestamp

        # Calculate required warmup time for HTF and MTF
        # E.g., if HTF is 1D, we need 100 days of history before the LTF starts.
        htf_interval = htf_candles[1].timestamp - htf_candles[0].timestamp if len(htf_candles) > 1 else 0
        mtf_interval = mtf_candles[1].timestamp - mtf_candles[0].timestamp if len(mtf_candles) > 1 else 0

        htf_required_start = ltf_start - (min_lookback_bars * htf_interval)
        mtf_required_start = ltf_start - (min_lookback_bars * mtf_interval)

        if htf_start > htf_required_start:
            raise ValueError(f"HTF dataset starts too late ({htf_start}) for LTF start ({ltf_start}). Needs {min_lookback_bars} bars warmup.")
            
        if mtf_start > mtf_required_start:
            raise ValueError(f"MTF dataset starts too late ({mtf_start}) for LTF start ({ltf_start}). Needs {min_lookback_bars} bars warmup.")

        return True
