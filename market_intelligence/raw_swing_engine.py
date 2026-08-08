"""
APEX Product 01 — Engine 1: Raw Swing Engine

Single responsibility:
    Convert validated OHLCV candles into confirmed geometric swing points.

This engine knows NOTHING about:
    BOS
    CHOCH
    MSS
    Trend
    Liquidity
    Inducement
    Keyzones
    Market Phase
    Strategy
    Risk
    Execution

A swing is only geometry.

Confirmation is explicitly separated from the timestamp of
the price extreme so that downstream historical replay cannot
accidentally use future information.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


__module_name__ = "raw_swing_engine"
__build_version__ = "1.0.0"


class SwingType(Enum):
    HIGH = "SWING_HIGH"
    LOW = "SWING_LOW"


class SwingStatus(Enum):
    CONFIRMED = "CONFIRMED"


@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class RawSwing:
    swing_id: str

    # Time/price of the actual geometric extreme.
    timestamp: int
    candle_index: int
    price: float
    swing_type: SwingType

    # Time at which enough future candles have closed to confirm it.
    confirmation_timestamp: int
    confirmation_index: int

    timeframe: str
    status: SwingStatus = SwingStatus.CONFIRMED


@dataclass(frozen=True)
class RawSwingConfig:
    left_bars: int = 2
    right_bars: int = 2
    timeframe: str = "1H"

    def __post_init__(self) -> None:
        if self.left_bars < 1:
            raise ValueError("left_bars must be >= 1")

        if self.right_bars < 1:
            raise ValueError("right_bars must be >= 1")

        if not self.timeframe:
            raise ValueError("timeframe cannot be empty")


class RawSwingEngine:
    """
    Deterministic confirmed swing detector.

    A swing at index i is only emitted when candles
    i + right_bars are available.

    This means the emitted swing is historically anchored to:
        extreme_index
        confirmation_index

    Downstream engines must use confirmation_index when replaying
    information availability.
    """

    def __init__(self, config: RawSwingConfig | None = None) -> None:
        self.config = config or RawSwingConfig()

    def detect(self, candles: List[Candle]) -> List[RawSwing]:
        """
        Detect all confirmed geometric swing highs and lows.

        The returned list is chronological by confirmation index,
        then candle index.

        Equal neighboring extremes are rejected. This prevents
        arbitrary selection from flat-topped or flat-bottomed
        structures.
        """

        self._validate_candles(candles)

        left = self.config.left_bars
        right = self.config.right_bars

        minimum = left + right + 1

        if len(candles) < minimum:
            return []

        swings: List[RawSwing] = []

        last_candidate_index = len(candles) - right - 1

        for index in range(left, last_candidate_index + 1):
            current = candles[index]

            is_swing_high = self._is_strict_swing_high(
                candles,
                index,
                left,
                right,
            )

            is_swing_low = self._is_strict_swing_low(
                candles,
                index,
                left,
                right,
            )

            confirmation_index = index + right
            confirmation_candle = candles[confirmation_index]

            # A candle can technically satisfy both geometric tests
            # on pathological data. Preserve both facts rather than
            # silently discarding one.
            if is_swing_high:
                swings.append(
                    RawSwing(
                        swing_id=f"SW_HIGH_{index}",
                        timestamp=current.timestamp,
                        candle_index=index,
                        price=current.high,
                        swing_type=SwingType.HIGH,
                        confirmation_timestamp=confirmation_candle.timestamp,
                        confirmation_index=confirmation_index,
                        timeframe=self.config.timeframe,
                    )
                )

            if is_swing_low:
                swings.append(
                    RawSwing(
                        swing_id=f"SW_LOW_{index}",
                        timestamp=current.timestamp,
                        candle_index=index,
                        price=current.low,
                        swing_type=SwingType.LOW,
                        confirmation_timestamp=confirmation_candle.timestamp,
                        confirmation_index=confirmation_index,
                        timeframe=self.config.timeframe,
                    )
                )

        swings.sort(
            key=lambda swing: (
                swing.confirmation_index,
                swing.candle_index,
                swing.swing_type.value,
            )
        )

        return swings

    @staticmethod
    def _is_strict_swing_high(
        candles: List[Candle],
        index: int,
        left: int,
        right: int,
    ) -> bool:
        current_high = candles[index].high

        left_range = range(index - left, index)
        right_range = range(index + 1, index + right + 1)

        return (
            all(candles[i].high < current_high for i in left_range)
            and all(candles[i].high < current_high for i in right_range)
        )

    @staticmethod
    def _is_strict_swing_low(
        candles: List[Candle],
        index: int,
        left: int,
        right: int,
    ) -> bool:
        current_low = candles[index].low

        left_range = range(index - left, index)
        right_range = range(index + 1, index + right + 1)

        return (
            all(candles[i].low > current_low for i in left_range)
            and all(candles[i].low > current_low for i in right_range)
        )

    @staticmethod
    def _validate_candles(candles: List[Candle]) -> None:
        previous_timestamp = None

        for index, candle in enumerate(candles):
            if candle.high < candle.low:
                raise ValueError(
                    f"Candle {index}: high cannot be below low"
                )

            if candle.open > candle.high or candle.open < candle.low:
                raise ValueError(
                    f"Candle {index}: open outside OHLC range"
                )

            if candle.close > candle.high or candle.close < candle.low:
                raise ValueError(
                    f"Candle {index}: close outside OHLC range"
                )

            if candle.volume < 0:
                raise ValueError(
                    f"Candle {index}: volume cannot be negative"
                )

            if previous_timestamp is not None:
                if candle.timestamp <= previous_timestamp:
                    raise ValueError(
                        "Candle timestamps must be strictly increasing"
                    )

            previous_timestamp = candle.timestamp
