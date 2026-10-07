"""Canonical Market Model Observation Registry Module.

Decouples descriptive observations extracted from MarketState from individual
Strategy Hypotheses, allowing hundreds of strategy families to operate
without altering or redefining the frozen Market Model.
"""
from __future__ import annotations

from market_model.observations.contracts import (
    ObservationCategory,
    ObservationDefinition,
    ObservationValue,
)
from market_model.observations.registry import (
    ObservationRegistry,
    OBSERVATION_REGISTRY,
)

__all__ = [
    "ObservationCategory",
    "ObservationDefinition",
    "ObservationValue",
    "ObservationRegistry",
    "OBSERVATION_REGISTRY",
]
