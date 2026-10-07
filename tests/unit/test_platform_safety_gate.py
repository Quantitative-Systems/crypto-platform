"""Unit tests for STRATA Platform Safety Gate & Multi-Tier Capital Barriers."""
import os
import pytest
from execution.safety.safety_gate import (
    EnvironmentGateMode,
    FatalSafetyError,
    PlatformSafetyGate,
    SAFETY_GATE,
)


def test_safety_gate_defaults_to_paper_and_zero_capital():
    assert SAFETY_GATE.current_mode in (EnvironmentGateMode.PAPER, EnvironmentGateMode.SHADOW)
    assert SAFETY_GATE.real_capital_authorized_usd == 0.0
    assert not SAFETY_GATE.is_live_execution


def test_live_order_rejected_in_paper_mode():
    with pytest.raises(FatalSafetyError, match="SECURITY BREACH: Live order submitted"):
        SAFETY_GATE.assert_order_allowed(
            notional_usd=50.0,
            risk_pct=0.05,
            open_positions_count=0,
            is_live_order=True,
        )


def test_live_transition_rejected_without_passkey():
    success, msg = SAFETY_GATE.transition_environment(EnvironmentGateMode.CONTROLLED_LIVE, auth_passkey=None)
    assert not success
    assert "require explicit cryptographic authorization" in msg
    assert SAFETY_GATE.current_mode == EnvironmentGateMode.PAPER


def test_micro_live_constraints_enforced():
    gate = PlatformSafetyGate()
    # If forced into micro live without unlock, should fail
    with pytest.raises(FatalSafetyError):
        gate.assert_order_allowed(
            notional_usd=500.0,  # Exceeds max $100 notional
            risk_pct=0.05,
            open_positions_count=0,
            is_live_order=True,
        )
