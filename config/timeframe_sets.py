"""
Product 01: Crypto Platform Configuration
Defines liquid asset universe and the 4 Operational Timeframe Execution Scales.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class TimeframeSetID(str, Enum):
    SET_1_INVESTING = "SET_1_INVESTING"
    SET_2_POSITION = "SET_2_POSITION"
    SET_3_SWING = "SET_3_SWING"
    SET_4_INTRADAY = "SET_4_INTRADAY"
 

@dataclass(frozen=True)
class TimeframeSet:
    set_id: TimeframeSetID
    style_name: str
    htf: str  # Destination & Permission (Bias, Expected Phase, TP)
    mtf: str  # Navigation & Trailing (Setup, Realignment, Trailing SL)
    ltf: str  # Execution & Invalidation (Sweep, Trigger, Invalidation SL)


TIMEFRAME_SETS = {
    TimeframeSetID.SET_1_INVESTING: TimeframeSet(
        set_id=TimeframeSetID.SET_1_INVESTING, style_name="Investing", htf="1M", mtf="1W", ltf="1D"
    ),
    TimeframeSetID.SET_2_POSITION: TimeframeSet(
        set_id=TimeframeSetID.SET_2_POSITION, style_name="Position Trading", htf="1W", mtf="1D", ltf="4H"
    ),
    TimeframeSetID.SET_3_SWING: TimeframeSet(
        set_id=TimeframeSetID.SET_3_SWING, style_name="Swing Trading", htf="1D", mtf="4H", ltf="1H"
    ),
    TimeframeSetID.SET_4_INTRADAY: TimeframeSet(
        set_id=TimeframeSetID.SET_4_INTRADAY, style_name="Intraday Scaling", htf="4H", mtf="1H", ltf="15M"
    ),
}

PRIMARY_ASSET_UNIVERSE: List[str] = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
