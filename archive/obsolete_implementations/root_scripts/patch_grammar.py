import re

with open("research/strategy_grammar.py", "r") as f:
    content = f.read()

# Fix evaluate_htf_bias
old_htf = """def evaluate_htf_bias(df: pd.DataFrame, bias: HTFBias, scale_factor: int = 4) -> Tuple[pd.Series, pd.Series]:
    \"\"\"Returns (bullish_bias, bearish_bias) boolean masks.\"\"\"
    close = df["close"]"""

new_htf = """def evaluate_htf_bias(df: pd.DataFrame, bias: HTFBias, scale_factor: int = 4) -> Tuple[pd.Series, pd.Series]:
    \"\"\"Returns (bullish_bias, bearish_bias) boolean masks.\"\"\"
    close = df["close"]
    high = df["high"]
    low = df["low"]"""

content = content.replace(old_htf, new_htf)

new_htf_logic = """
    elif bias == HTFBias.MARKET_STRUCTURE:
        roll_high = high.rolling(20 * scale_factor).max()
        roll_low = low.rolling(20 * scale_factor).min()
        bull_ms = (roll_high > roll_high.shift(20 * scale_factor)) & (roll_low > roll_low.shift(20 * scale_factor))
        bear_ms = (roll_high < roll_high.shift(20 * scale_factor)) & (roll_low < roll_low.shift(20 * scale_factor))
        return bull_ms, bear_ms
        
    elif bias == HTFBias.MACD_MOMENTUM:
        ema12 = _ema(close, 12 * scale_factor)
        ema26 = _ema(close, 26 * scale_factor)
        macd_line = ema12 - ema26
        signal_line = _ema(macd_line, 9 * scale_factor)
        macd_hist = macd_line - signal_line
        bull_macd = (macd_line > signal_line) & (macd_hist > 0)
        bear_macd = (macd_line < signal_line) & (macd_hist < 0)
        return bull_macd, bear_macd
        
    elif bias == HTFBias.MEAN_REVERSION_STRETCH:
        sma = close.rolling(20 * scale_factor).mean()
        std = close.rolling(20 * scale_factor).std()
        upper_bb = sma + (2 * std)
        lower_bb = sma - (2 * std)
        return (close < lower_bb), (close > upper_bb)
"""

content = content.replace("    else: # NEUTRAL", new_htf_logic + "\n    else: # NEUTRAL")


# Fix evaluate_mtf_setup
old_mtf = """def evaluate_mtf_setup(df: pd.DataFrame, setup: MTFSetup, scale_factor: int = 1) -> Tuple[pd.Series, pd.Series]:
    \"\"\"Returns (bullish_setup, bearish_setup) boolean masks.\"\"\"
    close, high, low = df["close"], df["high"], df["low"]"""

new_mtf = """def evaluate_mtf_setup(df: pd.DataFrame, setup: MTFSetup, scale_factor: int = 1) -> Tuple[pd.Series, pd.Series]:
    \"\"\"Returns (bullish_setup, bearish_setup) boolean masks.\"\"\"
    close, high, low, open_ = df["close"], df["high"], df["low"], df["open"]"""

content = content.replace(old_mtf, new_mtf)

new_mtf_logic = """
    elif setup == MTFSetup.LIQUIDITY_SWEEP:
        prior_low = low.rolling(20 * scale_factor).min().shift(1)
        prior_high = high.rolling(20 * scale_factor).max().shift(1)
        bull_sweep = (low < prior_low) & (close > prior_low)
        bear_sweep = (high > prior_high) & (close < prior_high)
        return bull_sweep, bear_sweep
        
    elif setup == MTFSetup.ORDER_BLOCK_TAP:
        atr = compute_atr(df, 14 * scale_factor)
        down_candle = close < open_
        up_candle = close > open_
        strong_up = up_candle & ((close - open_) > atr * 0.8)
        strong_down = down_candle & ((open_ - close) > atr * 0.8)
        bull_ob_formed = strong_up & down_candle.shift(1)
        bear_ob_formed = strong_down & up_candle.shift(1)
        recent_bull_ob = bull_ob_formed.rolling(10 * scale_factor).max() > 0
        recent_bear_ob = bear_ob_formed.rolling(10 * scale_factor).max() > 0
        fast = _ema(close, 20 * scale_factor)
        pulled_back_bull = low <= fast
        pulled_back_bear = high >= fast
        return (recent_bull_ob & pulled_back_bull), (recent_bear_ob & pulled_back_bear)

    elif setup == MTFSetup.BOLLINGER_SQUEEZE:
        sma = close.rolling(20 * scale_factor).mean()
        std = close.rolling(20 * scale_factor).std()
        upper_bb = sma + (2 * std)
        lower_bb = sma - (2 * std)
        bb_width = (upper_bb - lower_bb) / sma
        bb_pct = bb_width.rolling(50 * scale_factor).rank(pct=True)
        in_squeeze = bb_pct <= 0.20
        return in_squeeze, in_squeeze
"""

content = content.replace("    else: # NO_SETUP", new_mtf_logic + "\n    else: # NO_SETUP")


# Fix evaluate_ltf_entry
new_ltf_logic = """
    elif entry == LTFEntry.PIN_BAR_REJECTION:
        candle_range = high - low
        body_size = (close - open_).abs()
        lower_wick = open_.combine(close, min) - low
        upper_wick = high - open_.combine(close, max)
        bull_pin = (lower_wick > candle_range * 0.5) & (body_size < candle_range * 0.3)
        bear_pin = (upper_wick > candle_range * 0.5) & (body_size < candle_range * 0.3)
        return bull_pin, bear_pin

    elif entry == LTFEntry.INSIDE_BAR_BREAKOUT:
        inside_bar = (high.shift(1) < high.shift(2)) & (low.shift(1) > low.shift(2))
        bull_breakout = inside_bar & (close > high.shift(1))
        bear_breakout = inside_bar & (close < low.shift(1))
        return bull_breakout, bear_breakout

    elif entry == LTFEntry.ENGULFING_CONFIRMATION:
        bull_engulf = (close > open_.shift(1)) & (open_ <= close.shift(1)) & (close.shift(1) < open_.shift(1))
        bear_engulf = (close < open_.shift(1)) & (open_ >= close.shift(1)) & (close.shift(1) > open_.shift(1))
        return bull_engulf, bear_engulf
"""

content = content.replace("    return pd.Series(False, index=df.index), pd.Series(False, index=df.index)", new_ltf_logic + "\n    return pd.Series(False, index=df.index), pd.Series(False, index=df.index)")


with open("research/strategy_grammar.py", "w") as f:
    f.write(content)
