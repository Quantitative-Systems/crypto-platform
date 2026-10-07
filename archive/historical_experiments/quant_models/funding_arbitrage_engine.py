import pandas as pd
import numpy as np

def generate_carry_signal(df: pd.DataFrame, funding_df: pd.DataFrame, window_periods: int = 21) -> np.ndarray:
    """
    Smart Delta-Neutral Carry Trade Signal.
    
    Instead of 'ALWAYS_IN', this analyzes the funding rate dataframe.
    If the moving average (default 21 periods = 7 days at 8h funding intervals)
    of the funding rate is positive, it signals 1 (HOLD).
    If the moving average drops below 0, it signals 0 (FLAT).
    
    This ensures we only capture yield in bull/neutral markets and exit
    before deep bear markets force us to pay negative funding.
    """
    # Create an aligned signal array (defaults to 0)
    signal = np.zeros(len(df), dtype=int)
    
    if funding_df.empty or "funding_rate" not in funding_df.columns:
        return signal

    # Calculate rolling MA of funding rate
    funding_ma = funding_df["funding_rate"].rolling(window=window_periods, min_periods=1).mean()
    
    # We need to map the funding decision to the main OHLCV dataframe timestamps
    df_times = df["timestamp"].astype('int64')
    fund_times = funding_df["timestamp"].astype('int64')
    
    # Simple forward fill: find the latest funding MA for each OHLCV bar
    # Since this is causal, we shift the MA by 1 so we only use past funding to make decisions
    causal_funding_ma = funding_ma.shift(1).fillna(0)
    
    # Create a mapping
    funding_dict = dict(zip(fund_times, causal_funding_ma))
    
    # Extract keys and sort them for fast lookup
    fund_ts_keys = np.array(sorted(funding_dict.keys()))
    
    for i in range(len(df)):
        current_ts = df_times.iloc[i]
        
        # Find the most recent funding timestamp prior to current_ts
        idx = np.searchsorted(fund_ts_keys, current_ts, side='right') - 1
        
        if idx >= 0:
            latest_fund_ts = fund_ts_keys[idx]
            current_ma = funding_dict[latest_fund_ts]
            
            # Entry condition: MA is positive and significantly above zero to overcome friction
            if current_ma > 0.00005:  # 0.005% threshold
                signal[i] = 1
                
    return signal
