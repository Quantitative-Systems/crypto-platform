"""
Product 02 — Strategy Engine: News Filter Architecture
Provides injectable scheduled news blackout overlay interface (30m before to 30m after qualifying event).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Set


class NewsImpact(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class NewsEvent:
    """
    Scheduled macroeconomic or high-impact news event contract.
    """
    event_id: str
    timestamp: int  # Exact scheduled epoch timestamp
    event_name: str
    impact: NewsImpact
    affected_symbols: List[str] = field(default_factory=list)
    currency: str = "USD"


class NewsProvider(ABC):
    """
    Abstract interface for scheduled major-news providers.
    """

    @abstractmethod
    def is_news_blackout(
        self,
        symbol: str,
        timestamp: int,
        blackout_seconds_before: int = 1800,  # 30 minutes
        blackout_seconds_after: int = 1800    # 30 minutes
    ) -> Tuple[bool, Optional[NewsEvent]]:
        """
        Determines whether the given timestamp falls within the news blackout window:
        [event.timestamp - blackout_seconds_before, event.timestamp + blackout_seconds_after]
        """
        pass


class NullNewsProvider(NewsProvider):
    """
    Default no-op news provider for standard simulation and baseline operations.
    """
    def is_news_blackout(
        self,
        symbol: str,
        timestamp: int,
        blackout_seconds_before: int = 1800,
        blackout_seconds_after: int = 1800
    ) -> Tuple[bool, Optional[NewsEvent]]:
        return False, None


class MemoryNewsProvider(NewsProvider):
    """
    In-memory news provider for deterministic unit testing and live calendar injection.
    """
    def __init__(self, events: Optional[List[NewsEvent]] = None):
        self.events: List[NewsEvent] = list(events or [])

    def add_event(self, event: NewsEvent):
        self.events.append(event)

    def is_news_blackout(
        self,
        symbol: str,
        timestamp: int,
        blackout_seconds_before: int = 1800,
        blackout_seconds_after: int = 1800
    ) -> Tuple[bool, Optional[NewsEvent]]:
        for ev in self.events:
            # Check symbol matching if specific symbols are defined
            if ev.affected_symbols:
                matches_symbol = any(s.upper() in symbol.upper() for s in ev.affected_symbols)
                if not matches_symbol:
                    continue

            start_window = ev.timestamp - blackout_seconds_before
            end_window = ev.timestamp + blackout_seconds_after

            if start_window <= timestamp <= end_window:
                return True, ev

        return False, None
