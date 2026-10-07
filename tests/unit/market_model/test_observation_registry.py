"""Unit tests for Market Model Observation Registry."""
import pytest

from market_model.contracts import (
    KeyZone,
    MarketPhaseType,
    MarketState,
    MeasurementsSnapshot,
    PhaseSnapshot,
    StructureSnapshot,
    SwingPoint,
    TrendDirection,
    ZonesSnapshot,
)
from market_model.observations import (
    OBSERVATION_REGISTRY,
    ObservationCategory,
    ObservationRegistry,
)


def test_observation_registry_extract_all():
    reg = ObservationRegistry()
    state = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1700000000000,
        timeframe="4h",
        close_price=49500.0,
        structure=StructureSnapshot(
            external_trend=TrendDirection.BULLISH,
            internal_trend=TrendDirection.BULLISH,
            last_major_high=SwingPoint(1700000000000, 50000.0, True),
            last_major_low=SwingPoint(1699900000000, 48000.0, False),
            trend_strength=0.85,
        ),
        zones=ZonesSnapshot(
            order_blocks=[
                KeyZone(
                    zone_id="OB_1",
                    zone_type="ORDER_BLOCK",
                    high_price=48500.0,
                    low_price=48000.0,
                    created_at_ms=1699900000000,
                    is_bullish=True,
                    is_mitigated=False,
                )
            ]
        ),
        phase=PhaseSnapshot(
            current_phase=MarketPhaseType.CONTINUATION,
            depth_pct=0.25,
            duration_bars=5,
        ),
        measurements=MeasurementsSnapshot(atr=450.0, adx=32.0),
    )

    observations = reg.extract_all(state)
    assert "structure.external_trend" in observations
    assert observations["structure.external_trend"].value == "BULLISH"
    assert "phase.current_phase" in observations
    assert observations["phase.current_phase"].value == "CONTINUATION"
    assert "zones.active_order_blocks" in observations
    assert "OB_1" in observations["zones.active_order_blocks"].value
    assert "regime.market_regime" in observations
    assert observations["regime.market_regime"].value == "BULL_TRENDING"


def test_observation_registry_categories():
    categories = OBSERVATION_REGISTRY.list_observations(ObservationCategory.STRUCTURE)
    assert len(categories) >= 4
    assert "structure.external_trend" in categories
    assert "structure.trend_strength" in categories
