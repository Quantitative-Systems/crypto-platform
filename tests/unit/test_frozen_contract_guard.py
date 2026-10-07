"""Unit tests for Phase R Frozen Contract Runtime Guard."""
import pytest
from research.contracts.frozen_contract_guard import (
    FrozenContractGuard,
    FrozenContractViolationError,
)


def test_frozen_guard_passes_canonical_contract():
    guard = FrozenContractGuard.get_instance()
    # Canonical zero capital should pass
    guard.assert_capital_safety(real_capital_authorized=0.0, live_trading_enabled=False)
    # Canonical target floor should pass
    guard.assert_target_floor(planned_r=4.0)
    guard.assert_target_floor(planned_r=5.5)
    # Canonical risk limits should pass
    guard.assert_risk_limits(risk_pct=1.0, asset_heat_pct=1.0, total_heat_pct=3.0)


def test_frozen_guard_rejects_positive_real_capital():
    guard = FrozenContractGuard.get_instance()
    with pytest.raises(FrozenContractViolationError, match="Real capital authorization"):
        guard.assert_capital_safety(real_capital_authorized=100.0, live_trading_enabled=False)


def test_frozen_guard_rejects_live_trading_enabled():
    guard = FrozenContractGuard.get_instance()
    with pytest.raises(FrozenContractViolationError, match="Live trading enabled"):
        guard.assert_capital_safety(real_capital_authorized=0.0, live_trading_enabled=True)


def test_frozen_guard_rejects_sub_4r_target():
    guard = FrozenContractGuard.get_instance()
    with pytest.raises(FrozenContractViolationError, match="below the frozen floor"):
        guard.assert_target_floor(planned_r=3.8)


def test_frozen_guard_rejects_excess_risk():
    guard = FrozenContractGuard.get_instance()
    with pytest.raises(FrozenContractViolationError, match="Trade risk"):
        guard.assert_risk_limits(risk_pct=1.5, asset_heat_pct=1.0, total_heat_pct=3.0)

    with pytest.raises(FrozenContractViolationError, match="Portfolio heat"):
        guard.assert_risk_limits(risk_pct=1.0, asset_heat_pct=1.0, total_heat_pct=3.5)
