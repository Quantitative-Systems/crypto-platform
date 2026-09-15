"""
Quantitative Crypto Platform (QCP) — Family 06: Volatility Expansion Squeeze.

Economic Mechanism:
Asset prices alternate between regimes of low-volatility consolidation (compression/energy storage)
and high-volatility expansion (directional trending). By detecting when Bollinger Bands contract
inside Keltner Channels (the classic Squeeze), and taking directional breakout positions as the bands
expand, the strategy captures early trend impulses while risking tight initial stops during low-volatility phases.

Causal Specification:
- Closed candles only (no intrabar lookahead)
- Stop loss: 1.5 * ATR(14)
- Target: 2.5R - 3.0R with dynamic trailing
- Collision policy: ADVERSE_FIRST
- Friction model: 8.0 bps round-trip taker + slippage
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from platform_core.canonical_strategy_spec import CanonicalStrategySpec, StrategyLifecycleState


def bollinger_bands_numpy(close: np.ndarray, period: int = 20, num_std: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Computes Bollinger Bands using pure NumPy."""
    n = len(close)
    mid = np.zeros(n, dtype=np.float64)
    upper = np.zeros(n, dtype=np.float64)
    lower = np.zeros(n, dtype=np.float64)

    for i in range(period - 1, n):
        window = close[i - period + 1 : i + 1]
        m = np.mean(window)
        s = np.std(window, ddof=0)
        mid[i] = m
        upper[i] = m + num_std * s
        lower[i] = m - num_std * s

    mid[: period - 1] = close[: period - 1]
    upper[: period - 1] = close[: period - 1]
    lower[: period - 1] = close[: period - 1]
    return mid, upper, lower


def keltner_channels_numpy(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 20,
    atr_period: int = 14,
    atr_multiplier: float = 1.5,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Computes Keltner Channels (EMA center line + ATR bands)."""
    n = len(close)
    # EMA center
    alpha = 2.0 / (period + 1.0)
    ema = np.zeros(n, dtype=np.float64)
    ema[0] = close[0]
    for i in range(1, n):
        ema[i] = alpha * close[i] + (1.0 - alpha) * ema[i - 1]

    # True Range & ATR
    tr = np.zeros(n, dtype=np.float64)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    atr = np.zeros(n, dtype=np.float64)
    atr[0] = tr[0]
    alpha_atr = 1.0 / atr_period
    for i in range(1, n):
        atr[i] = alpha_atr * tr[i] + (1.0 - alpha_atr) * atr[i - 1]

    upper = ema + (atr_multiplier * atr)
    lower = ema - (atr_multiplier * atr)
    return ema, upper, lower


def atr_numpy(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    tr = np.zeros(n, dtype=np.float64)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    atr = np.zeros(n, dtype=np.float64)
    atr[0] = tr[0]
    alpha = 1.0 / period
    for i in range(1, n):
        atr[i] = alpha * tr[i] + (1.0 - alpha) * atr[i - 1]
    return atr


def compute_volatility_squeeze_signals(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    bb_period: int = 20,
    bb_std: float = 2.0,
    kc_period: int = 20,
    kc_mult: float = 1.5,
    atr_period: int = 14,
    lookback_warmup: int = 50,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes directional breakout signals from Volatility Squeeze expansion.
    Returns: (long_signals, short_signals, atr_values)
    """
    n = len(close)
    bb_mid, bb_upper, bb_lower = bollinger_bands_numpy(close, bb_period, bb_std)
    kc_mid, kc_upper, kc_lower = keltner_channels_numpy(high, low, close, kc_period, atr_period, kc_mult)
    atr_vals = atr_numpy(high, low, close, atr_period)

    # Squeeze is active when Bollinger Band is inside Keltner Channel
    is_squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)

    # Squeeze fired: previous bar was in squeeze, current bar expands out
    squeeze_fired = np.roll(is_squeeze, 1) & (~is_squeeze)
    squeeze_fired[:lookback_warmup] = False

    # Momentum confirmation: close relative to EMA center
    momentum = close - kc_mid

    long_signals = squeeze_fired & (close > bb_upper) & (momentum > 0)
    short_signals = squeeze_fired & (close < bb_lower) & (momentum < 0)

    long_signals[:lookback_warmup] = False
    short_signals[:lookback_warmup] = False

    return long_signals, short_signals, atr_vals


def create_fam06_spec(
    symbol: str = "SOLUSDT",
    timeframe_set: int = 2,
    lifecycle_state: StrategyLifecycleState = StrategyLifecycleState.RESEARCH,
    notes: Optional[str] = None,
) -> CanonicalStrategySpec:
    """
    Factory creating canonical specification for Family 06: Volatility Expansion Squeeze.
    """
    tf_mapping = {
        1: {"HTF": "1M", "MTF": "1W", "LTF": "1D"},
        2: {"HTF": "1W", "MTF": "1D", "LTF": "4H"},
        3: {"HTF": "1D", "MTF": "4H", "LTF": "1H"},
        4: {"HTF": "4H", "MTF": "1H", "LTF": "15m"},
    }
    timeframes = tf_mapping.get(timeframe_set, {"HTF": "1W", "MTF": "1D", "LTF": "4H"})
    clean_sym = symbol.replace("/", "").replace("_", "")

    strategy_id = f"FAM-06-VOLSQUEEZE_{clean_sym}_Set{timeframe_set}"

    params = {
        "tp_r": 3.0,
        "atr_mult": 1.5,
        "bb_period": 20,
        "bb_std": 2.0,
        "kc_period": 20,
        "kc_mult": 1.5,
        "atr_period": 14,
        "direction": "BOTH",
    }

    rules = {
        "squeeze_condition": "BB_Upper(20, 2.0) < KC_Upper(20, 1.5) AND BB_Lower(20, 2.0) > KC_Lower(20, 1.5)",
        "entry_long": "Prior bar was in Squeeze AND Current Close > BB_Upper AND Close > KC_EMA(20)",
        "entry_short": "Prior bar was in Squeeze AND Current Close < BB_Lower AND Close < KC_EMA(20)",
        "stop_loss": "1.5 * ATR(14)",
        "take_profit": "Entry +/- (Risk * 3.0)",
        "collision_policy": "ADVERSE_FIRST",
        "same_bar_confirmation": "CLOSED_CANDLES_ONLY",
    }

    return CanonicalStrategySpec(
        strategy_id=strategy_id,
        family_id="FAM-06-VOLSQUEEZE",
        family_name="Volatility Expansion Squeeze",
        symbol=symbol,
        timeframe_set=timeframe_set,
        timeframes=timeframes,
        parameters=params,
        rules=rules,
        lifecycle_state=lifecycle_state,
        notes=notes,
    )
