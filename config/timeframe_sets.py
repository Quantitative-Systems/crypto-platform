"""
Product 01: Crypto Platform Configuration
Defines the liquid asset universe, the authoritative 6-Set HTF -> MTF -> LTF operational
hierarchy, and the legacy 5-Set execution-scale alias table.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class TimeframeSetID(str, Enum):
    SET_1_INVESTING = "SET_1_INVESTING"
    SET_2_POSITION = "SET_2_POSITION"
    SET_3_SWING = "SET_3_SWING"
    SET_4_INTRADAY = "SET_4_INTRADAY"
    SET_5_SCALPING = "SET_5_SCALPING"  # Historical 5-set alias
    SET_5_SHORT_TERM = "SET_5_SHORT_TERM"
    SET_6_SCALPING = "SET_6_SCALPING"


@dataclass(frozen=True)
class TimeframeSet:
    set_id: str
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
    TimeframeSetID.SET_5_SCALPING: TimeframeSet(
        set_id=TimeframeSetID.SET_5_SCALPING, style_name="Intraday Scalping", htf="15M", mtf="5M", ltf="1m"
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# AUTHORITATIVE 6-SET OPERATIONAL MARKET-RESOLUTION HIERARCHY
#
# This mapping is the SINGLE SOURCE OF TRUTH for the HTF -> MTF -> LTF ladder.
# `research/replayer/timeframe_aligner.py` derives its `CANONICAL_TIMEFRAME_SETS`
# from this mapping, so the configuration layer, the strategy grammar enum
# (`research/strategy_grammar.py`) and the research replayer can never disagree.
#
# The foundation is: HTF BIAS -> MTF SETUP -> LTF ENTRY, then
# LTF structural stop -> HTF structural target -> MTF structural trailing.
#
# Style ladder (each set is an INDEPENDENT strategy instance):
#   SET_1  Investing / Macro        1M  -> 1W  -> 1D
#   SET_2  Position Trading         1W  -> 1D  -> 4H
#   SET_3  Swing Trading            1D  -> 4H  -> 1H
#   SET_4  Intraday                 4H  -> 1H  -> 15M
#   SET_5  Short-Term Intraday      1H  -> 15M -> 5M
#   SET_6  Scalping                 15M -> 5M  -> 1m
#
# Layer roles (structurally never flattened into one another):
#   HTF = Destination & Permission  (bias, expected phase, take-profit)
#   MTF = Navigation & Trailing     (setup, realignment, trailing stop)
#   LTF = Execution & Invalidation  (liquidity sweep, trigger, initial stop)
# ─────────────────────────────────────────────────────────────────────────────
CANONICAL_6_TIMEFRAME_SETS = {
    "SET_1": TimeframeSet(set_id="SET_1", style_name="Investing / Macro", htf="1M", mtf="1W", ltf="1D"),
    "SET_2": TimeframeSet(set_id="SET_2", style_name="Position Trading", htf="1W", mtf="1D", ltf="4H"),
    "SET_3": TimeframeSet(set_id="SET_3", style_name="Swing Trading", htf="1D", mtf="4H", ltf="1H"),
    "SET_4": TimeframeSet(set_id="SET_4", style_name="Intraday", htf="4H", mtf="1H", ltf="15M"),
    "SET_5": TimeframeSet(set_id="SET_5", style_name="Short-Term Intraday", htf="1H", mtf="15M", ltf="5M"),
    "SET_6": TimeframeSet(set_id="SET_6", style_name="Scalping", htf="15M", mtf="5M", ltf="1m"),
}


def get_canonical_timeframe_set(set_id: str) -> TimeframeSet:
    """Returns the authoritative TimeframeSet for SET_1..SET_6. Fail-closed on unknown ids."""
    try:
        return CANONICAL_6_TIMEFRAME_SETS[set_id]
    except KeyError:
        raise ValueError(
            f"Invalid canonical timeframe set '{set_id}'. "
            f"Supported sets: {list(CANONICAL_6_TIMEFRAME_SETS.keys())}"
        ) from None

PRIMARY_ASSET_UNIVERSE: List[str] = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

