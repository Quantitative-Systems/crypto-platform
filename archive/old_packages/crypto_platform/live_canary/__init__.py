"""Crypto Trading Platform — LIVE-CANARY Operating Subsystem.

Provides controlled, real-money micro-canary execution, pre-flight broker auditing,
capital boundary enforcement, and failsafe emergency kill controls.
"""
from .verifier import CanaryBrokerVerifier, CanaryVerificationReport, CheckResult
from .harness import CanaryState, LiveCanaryHarness

__all__ = [
    "CanaryBrokerVerifier",
    "CanaryVerificationReport",
    "CheckResult",
    "CanaryState",
    "LiveCanaryHarness",
]
