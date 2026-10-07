"""Observation Contracts & Types for Canonical Market Model.

Defines standardized, typed, timestamped observation data structures
extracted from MarketState without altering the frozen Market Model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ObservationCategory(str, Enum):
    STRUCTURE = "STRUCTURE"
    ZONES = "ZONES"
    PHASE = "PHASE"
    TECHNICAL = "TECHNICAL"
    REGIME = "REGIME"
    MACRO = "MACRO"


@dataclass(frozen=True)
class ObservationValue:
    """An immutable, timestamped, causal observation extracted from MarketState."""
    observation_id: str
    category: ObservationCategory
    timestamp_ms: int
    timeframe: str
    symbol: str
    value: Any
    confidence: float = 1.0
    version: str = "v1"
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObservationDefinition:
    """Metadata definition for a registered observation."""
    observation_id: str
    category: ObservationCategory
    name: str
    description: str
    extractor: Callable[[Any], ObservationValue]
    version: str = "v1"
