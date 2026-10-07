import pandas as pd
import numpy as np

def generate_stat_arb_signal(df_leg1: pd.DataFrame, df_leg2: pd.DataFrame, window_periods: int = 100, z_score_threshold: float = 2.0) -> np.ndarray:
    """
    Statistical Arbitrage (Pairs Trading) Signal Generator.
    
    Expects two aligned OHLCV dataframes (df_leg1 and df_leg2).
    Calculates the rolling spread using a simple price ratio or rolling OLS beta.
    For simplicity and speed in this causal implementation, we use the ratio of close prices.
    
    Returns an array of signals for the spread:
     1: Go Long the Spread (Long Leg1, Short Leg2) - when z_score < -threshold
    -1: Go Short the Spread (Short Leg1, Long Leg2) - when z_score > threshold
     0: Flat (z_score converges to 0)
    """
    if len(df_leg1) != len(df_leg2):
        raise ValueError("Dataframes for Leg1 and Leg2 must be strictly aligned by timestamp.")
        
    signal = np.zeros(len(df_leg1), dtype=int)
    
    # 1. Calculate the price ratio (simplest hedge ratio approximation)
    # Using close prices up to bar i to make decisions for bar i+1
    ratio = df_leg1["close"] / df_leg2["close"]
    
    # 2. Calculate rolling mean and standard deviation of the ratio
    rolling_mean = ratio.rolling(window=window_periods, min_periods=window_periods).mean()
    rolling_std = ratio.rolling(window=window_periods, min_periods=window_periods).std()
    
    # 3. Calculate Z-Score
    z_score = (ratio - rolling_mean) / rolling_std
    
    # 4. Generate Signal
    # Note: the z_score at index i is calculated using data up to index i (closed bar).
    # The backtester applies this signal to open[i+1].
    
    in_position = 0 # 1 for Long Spread, -1 for Short Spread
    
    for i in range(window_periods, len(df_leg1)):
        current_z = z_score.iloc[i]
        
        if np.isnan(current_z):
            continue
            
        if in_position == 0:
            if current_z < -z_score_threshold:
                in_position = 1
            elif current_z > z_score_threshold:
                in_position = -1
        elif in_position == 1:
            if current_z >= 0: # Mean reversion completed
                in_position = 0
        elif in_position == -1:
            if current_z <= 0: # Mean reversion completed
                in_position = 0
                
        signal[i] = in_position
        
    return signal
