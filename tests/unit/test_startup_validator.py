"""Tests for STRATA Production Startup Validator.
Verifies fail-closed startup validation gates.
"""

import os
import unittest
from unittest.mock import patch

from core.config.startup_validator import (
    StartupValidator,
    StartupValidationError,
)


class TestStartupValidator(unittest.TestCase):
    """Test suite for pre-flight startup validation gates."""

    def test_default_paper_mode_passes(self):
        """Standard PAPER mode with clean environment passes pre-flight validation."""
        report = StartupValidator.validate_preflight(strict_fail_closed=True)
        self.assertTrue(report.is_valid)
        self.assertEqual(report.real_capital_authorized, 0.0)
        self.assertIn("KING_ENGINE_CONTRACT_INTEGRITY", report.checked_invariants)
        self.assertIn("CREDENTIAL_WITHDRAWAL_PERMISSION_CHECK", report.checked_invariants)

    def test_rejection_on_withdrawal_permission_detected(self):
        """Startup validator must fail-closed if withdrawal permissions exist in env."""
        with patch.dict(os.environ, {"BINANCE_PERMISSIONS_SCOPE": "ENABLE_WITHDRAWALS"}):
            with self.assertRaises(StartupValidationError):
                StartupValidator.validate_preflight(strict_fail_closed=True)

    def test_rejection_on_unauthorized_live_mode(self):
        """Startup validator must fail-closed if LIVE mode is requested without token."""
        with patch.dict(os.environ, {"PLATFORM_ENV": "LIVE", "PLATFORM_LIVE_AUTH_TOKEN": ""}):
            with self.assertRaises(StartupValidationError):
                StartupValidator.validate_preflight(strict_fail_closed=True)

    def test_lenient_mode_returns_report_with_rejections(self):
        """When strict_fail_closed=False, returns report detailing rejections without crashing."""
        with patch.dict(os.environ, {"BINANCE_KEY_PERMISSIONS": "WITHDRAW"}):
            report = StartupValidator.validate_preflight(strict_fail_closed=False)
            self.assertFalse(report.is_valid)
            self.assertTrue(any("Withdrawal" in r for r in report.rejection_reasons))


if __name__ == "__main__":
    unittest.main()
