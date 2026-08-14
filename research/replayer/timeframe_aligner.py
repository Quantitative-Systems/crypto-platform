"""
Product 04 — Research Laboratory: Timeframe Aligner
Enforces canonical multi-timeframe sets and zero-lookahead candle visibility rules.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from market_intelligence.primitives import Candle


@dataclass(frozen=True)
class TimeframeSet:
    set_id: str
    htf: str
    mtf: str
    ltf: str
    description: str


CANONICAL_TIMEFRAME_SETS: Dict[str, TimeframeSet] = {
    "SET_1": TimeframeSet(
        set_id="SET_1",
        htf="1M",
        mtf="1W",
        ltf="1D",
        description="Position / Macro Horizon (1 Month -> 1 Week -> 1 Day)"
    ),
    "SET_2": TimeframeSet(
        set_id="SET_2",
        htf="1W",
        mtf="1D",
        ltf="4H",
        description="Swing Horizon (1 Week -> 1 Day -> 4 Hours)"
    ),
    "SET_3": TimeframeSet(
        set_id="SET_3",
        htf="1D",
        mtf="4H",
        ltf="1H",
        description="Intraday / Swing Hybrid (1 Day -> 4 Hours -> 1 Hour)"
    ),
    "SET_4": TimeframeSet(
        set_id="SET_4",
        htf="4H",
        mtf="1H",
        ltf="15M",
        description="Tactical Intraday (4 Hours -> 1 Hour -> 15 Minutes)"
    ),
}

# Milliseconds per canonical timeframe for precise alignment
TIMEFRAME_DURATIONS_MS: Dict[str, int] = {
    "15M": 15 * 60 * 1000,
    "1H": 60 * 60 * 1000,
    "4H": 4 * 60 * 60 * 1000,
    "1D": 24 * 60 * 60 * 1000,
    "1W": 7 * 24 * 60 * 60 * 1000,
    "1M": 30 * 24 * 60 * 60 * 1000,  # Approximate standard month
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
        duration = TIMEFRAME_DURATIONS_MS.get(timeframe, 0)
        
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
