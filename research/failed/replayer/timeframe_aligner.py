"""
Product 04 — Research Laboratory: Timeframe Aligner
Enforces canonical multi-timeframe sets and zero-lookahead candle visibility rules.

The canonical ladder is owned by `config.timeframe_sets.CANONICAL_6_TIMEFRAME_SETS`.
This module DERIVES its `CANONICAL_TIMEFRAME_SETS` from that single source of truth so
that research replay, configuration, and the strategy grammar enum cannot drift apart.

Canonical 6-Set ladder (HTF -> MTF -> LTF):
    SET_1  Investing / Macro       1M  -> 1W  -> 1D
    SET_2  Position Trading        1W  -> 1D  -> 4H
    SET_3  Swing Trading           1D  -> 4H  -> 1H
    SET_4  Intraday                4H  -> 1H  -> 15M
    SET_5  Short-Term Intraday     1H  -> 15M -> 5M
    SET_6  Scalping                15M -> 5M  -> 1m
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from market_intelligence.primitives import Candle
from config.timeframe_sets import CANONICAL_6_TIMEFRAME_SETS as _AUTHORITATIVE_SETS


@dataclass(frozen=True)
class TimeframeSet:
    set_id: str
    htf: str
    mtf: str
    ltf: str
    description: str


CANONICAL_TIMEFRAME_SETS: Dict[str, TimeframeSet] = {
    set_id: TimeframeSet(
        set_id=set_id,
        htf=cfg.htf,
        mtf=cfg.mtf,
        ltf=cfg.ltf,
        description=f"{cfg.style_name} ({cfg.htf} -> {cfg.mtf} -> {cfg.ltf})",
    )
    for set_id, cfg in _AUTHORITATIVE_SETS.items()
}

# Seconds per canonical timeframe for precise alignment
TIMEFRAME_DURATIONS_SEC: Dict[str, int] = {
    "1M": 30 * 24 * 60 * 60,  # Approximate standard month
    "1MO": 30 * 24 * 60 * 60,
    "1W": 7 * 24 * 60 * 60,
    "1D": 24 * 60 * 60,
    "4H": 4 * 60 * 60,
    "1H": 60 * 60,
    "15M": 15 * 60,
    "5M": 5 * 60,
    "1m": 60,
    "1min": 60,
    "1MIN": 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
    "1w": 7 * 24 * 60 * 60,
}

# Milliseconds per canonical timeframe for precise alignment
TIMEFRAME_DURATIONS_MS: Dict[str, int] = {
    k: v * 1000 for k, v in TIMEFRAME_DURATIONS_SEC.items()
}


class TimeframeAligner:
    """
    Guarantees that at decision timestamp T, higher and middle timeframe bars
    are only exposed if they have completely closed at or before T.
    """

    @staticmethod
    def get_set(set_id: str) -> TimeframeSet:
        if set_id not in CANONICAL_TIMEFRAME_SETS:
            raise ValueError(f"Invalid timeframe set '{set_id}'. Supported sets: {list(CANONICAL_TIMEFRAME_SETS.keys())}")
        return CANONICAL_TIMEFRAME_SETS[set_id]

    @staticmethod
    def filter_visible_candles(
        candles: List[Candle],
        decision_timestamp: int,
        timeframe: str,
        buffer_size: int = 150
    ) -> List[Candle]:
        """
        Returns only the historical candles that closed at or before decision_timestamp.
        Strictly excludes any open/unfinalized candle.
        """
        if decision_timestamp < 100_000_000_000:
            duration = TIMEFRAME_DURATIONS_SEC.get(timeframe, TIMEFRAME_DURATIONS_SEC.get(timeframe.upper(), 0))
        else:
            duration = TIMEFRAME_DURATIONS_MS.get(timeframe, TIMEFRAME_DURATIONS_MS.get(timeframe.upper(), 0))
        
        # A candle with start timestamp is closed when (timestamp + duration) <= decision_timestamp
        # which is equivalent to timestamp <= (decision_timestamp - duration)
        cutoff = decision_timestamp - duration if duration > 0 else decision_timestamp
        
        # Binary search on sorted timestamps
        # Extract or search over timestamps
        low = 0
        high = len(candles)
        
        while low < high:
            mid = (low + high) // 2
            if candles[mid].timestamp <= cutoff:
                low = mid + 1
            else:
                high = mid
                
        # low is the count of visible closed candles
        visible_count = low
        start_idx = max(0, visible_count - buffer_size)
        return candles[start_idx:visible_count]
