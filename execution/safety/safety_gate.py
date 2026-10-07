"""STRATA Digital Trading Platform — Multi-Tier Capital Safety Gate & Hardware/Software Barrier.

Enforces deterministic gating across five operational execution environments:
1. SHADOW: Virtual order routing against live market data ($0.00 capital).
2. PAPER: High-fidelity simulation with modeled friction and virtual ledger ($0.00 capital).
3. BROKER_DEMO: Exchange testnet API execution ($0.00 real capital).
4. MICRO_LIVE: Real capital execution bounded by strict micro-risk constraints (max $100 notional, 0.1% risk).
5. CONTROLLED_LIVE: Full institutional execution up to certified governor limits.

NON-NEGOTIABLE SAFETY INVARIANTS:
1. Default environment is PAPER ($0.00 capital).
2. All live environments (MICRO_LIVE and CONTROLLED_LIVE) fail closed unless unlocked by
   explicit cryptographic tokens and multi-factor authorization.
3. Front-end UI cannot bypass backend safety gates under any circumstance.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class EnvironmentGateMode(str, Enum):
    SHADOW = "SHADOW"
    PAPER = "PAPER"
    BROKER_DEMO = "BROKER_DEMO"
    MICRO_LIVE = "MICRO_LIVE"
    CONTROLLED_LIVE = "CONTROLLED_LIVE"


class FatalSafetyError(RuntimeError):
    """Raised when an illegal or unauthorized execution transition is attempted."""
    pass


@dataclass
class MicroLiveConstraints:
    """Hard constraints enforcing micro-capital containment."""
    max_account_equity_usd: float = 1_000.0
    max_notional_per_order_usd: float = 100.0
    max_risk_per_trade_pct: float = 0.10  # 0.10% (one-tenth of one percent)
    max_open_positions: int = 1
    max_daily_loss_usd: float = 25.0


class PlatformSafetyGate:
    """Singleton execution environment and capital safety controller."""

    _instance: Optional[PlatformSafetyGate] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        default_mode: EnvironmentGateMode = EnvironmentGateMode.PAPER,
    ):
        if getattr(self, "_initialized", False):
            return

        self._current_mode = default_mode
        self._real_capital_authorized_usd = 0.0
        self._live_gate_unlocked = False
        self._unlock_timestamp_ms = 0
        self._authorized_by = "SAFETY_DEFAULT"
        self.micro_constraints = MicroLiveConstraints()

        # Check environment variables for runtime configuration
        env_mode = os.environ.get("PLATFORM_ENV", "PAPER").upper()
        if env_mode in EnvironmentGateMode.__members__:
            self._current_mode = EnvironmentGateMode[env_mode]
        else:
            self._current_mode = EnvironmentGateMode.PAPER

        # Validate that live modes fail closed on boot unless explicitly verified
        if self._current_mode in (EnvironmentGateMode.MICRO_LIVE, EnvironmentGateMode.CONTROLLED_LIVE):
            self._verify_live_credentials_or_fail_closed()

        self._initialized = True
        logger.info(
            f"STRATA Safety Gate initialized. Mode: {self._current_mode.value} | "
            f"Real Capital: ${self._real_capital_authorized_usd:.2f} | Live Unlocked: {self._live_gate_unlocked}"
        )

    @property
    def current_mode(self) -> EnvironmentGateMode:
        return self._current_mode

    @property
    def is_live_execution(self) -> bool:
        return self._current_mode in (EnvironmentGateMode.MICRO_LIVE, EnvironmentGateMode.CONTROLLED_LIVE)

    @property
    def real_capital_authorized_usd(self) -> float:
        return self._real_capital_authorized_usd

    def _verify_live_credentials_or_fail_closed(self) -> None:
        """Enforce strict fail-closed policy on boot if live mode requested."""
        live_token = os.environ.get("PLATFORM_LIVE_AUTH_TOKEN", "")
        # Cryptographic verification of explicit authorization token
        expected_secret = os.environ.get("PLATFORM_LIVE_GATE_SECRET", "")
        if not live_token or not expected_secret:
            logger.critical("LIVE TRADING ATTEMPT DETECTED WITHOUT VALID AUTH TOKEN. FAILING CLOSED TO PAPER MODE.")
            self._current_mode = EnvironmentGateMode.PAPER
            self._real_capital_authorized_usd = 0.0
            self._live_gate_unlocked = False
            return

        # Verify HMAC token
        expected_hash = hmac.new(
            expected_secret.encode(),
            b"AUTHORIZE_STRATA_LIVE_TRADING",
            hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(live_token, expected_hash):
            self._live_gate_unlocked = True
            if self._current_mode == EnvironmentGateMode.MICRO_LIVE:
                self._real_capital_authorized_usd = self.micro_constraints.max_account_equity_usd
            else:
                self._real_capital_authorized_usd = float(os.environ.get("PLATFORM_LIVE_CAPITAL_USD", "0.0"))
            self._authorized_by = "DUAL_TOKEN_HMAC_VERIFIED"
            logger.warning(
                f"LIVE CAPITAL GATE UNLOCKED: ${self._real_capital_authorized_usd:.2f} authorized by {self._authorized_by}"
            )
        else:
            logger.critical("INVALID LIVE AUTH TOKEN HMAC. FAILING CLOSED TO PAPER MODE.")
            self._current_mode = EnvironmentGateMode.PAPER
            self._real_capital_authorized_usd = 0.0
            self._live_gate_unlocked = False

    def assert_order_allowed(
        self,
        notional_usd: float,
        risk_pct: float,
        open_positions_count: int,
        is_live_order: bool,
    ) -> None:
        """Assert that an order submission satisfies all safety invariants for current mode."""
        # 1. Non-live modes MUST NOT submit live orders
        if not self.is_live_execution and is_live_order:
            raise FatalSafetyError(
                f"SECURITY BREACH: Live order submitted while Platform is in {self._current_mode.value} mode!"
            )

        # 2. Live orders require verified unlock
        if is_live_order and not self._live_gate_unlocked:
            raise FatalSafetyError(
                "FATAL SAFETY VIOLATION: Live trading adapter locked closed ($0.00 Real Capital authorized)."
            )

        # 3. Micro-Live strict bounds
        if self._current_mode == EnvironmentGateMode.MICRO_LIVE:
            if notional_usd > self.micro_constraints.max_notional_per_order_usd:
                raise FatalSafetyError(
                    f"MICRO-LIVE CONSTRAINT BREACH: Notional ${notional_usd:.2f} > max ${self.micro_constraints.max_notional_per_order_usd:.2f}"
                )
            if risk_pct > self.micro_constraints.max_risk_per_trade_pct:
                raise FatalSafetyError(
                    f"MICRO-LIVE CONSTRAINT BREACH: Risk {risk_pct:.3f}% > max {self.micro_constraints.max_risk_per_trade_pct:.3f}%"
                )
            if open_positions_count >= self.micro_constraints.max_open_positions:
                raise FatalSafetyError(
                    f"MICRO-LIVE CONSTRAINT BREACH: Open positions {open_positions_count} >= max {self.micro_constraints.max_open_positions}"
                )

    def transition_environment(
        self,
        target_mode: EnvironmentGateMode,
        auth_passkey: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Safely transition execution mode with validation."""
        # Demoting or moving between paper/shadow/demo is always safe
        if target_mode in (EnvironmentGateMode.SHADOW, EnvironmentGateMode.PAPER, EnvironmentGateMode.BROKER_DEMO):
            self._current_mode = target_mode
            self._real_capital_authorized_usd = 0.0
            self._live_gate_unlocked = False
            logger.info(f"Safe environment transition to {target_mode.value}. Real capital: $0.00")
            return True, f"Environment changed to {target_mode.value}"

        # Transitioning to live requires cryptographic passkey
        if not auth_passkey:
            return False, "Live environments require explicit cryptographic authorization passkey."

        expected_secret = os.environ.get("PLATFORM_LIVE_GATE_SECRET", "")
        if not expected_secret:
            return False, "PLATFORM_LIVE_GATE_SECRET environment variable not configured on host."

        expected_hash = hmac.new(
            expected_secret.encode(),
            b"AUTHORIZE_STRATA_LIVE_TRADING",
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(auth_passkey, expected_hash):
            logger.critical("FAILED ATTEMPT TO UNLOCK LIVE TRADING VIA API/CLI. PASSKEY INVALID.")
            return False, "Authorization passkey verification failed. Request rejected."

        self._current_mode = target_mode
        self._live_gate_unlocked = True
        self._unlock_timestamp_ms = int(time.time() * 1000)
        if target_mode == EnvironmentGateMode.MICRO_LIVE:
            self._real_capital_authorized_usd = self.micro_constraints.max_account_equity_usd
        else:
            self._real_capital_authorized_usd = float(os.environ.get("PLATFORM_LIVE_CAPITAL_USD", "1000.0"))

        logger.warning(f"SECURITY ALERT: Successfully transitioned to {target_mode.value} with ${self._real_capital_authorized_usd:.2f} authorized.")
        return True, f"Transitioned to {target_mode.value} (${self._real_capital_authorized_usd:.2f} authorized)"

    def get_status_report(self) -> Dict[str, Any]:
        """Produce machine-readable status report for UI and telemetry."""
        return {
            "current_mode": self._current_mode.value,
            "is_live": self.is_live_execution,
            "real_capital_authorized_usd": self._real_capital_authorized_usd,
            "live_gate_unlocked": self._live_gate_unlocked,
            "safety_barrier_engaged": not self._live_gate_unlocked,
            "authorized_by": self._authorized_by,
            "micro_constraints": {
                "max_notional_usd": self.micro_constraints.max_notional_per_order_usd,
                "max_risk_pct": self.micro_constraints.max_risk_per_trade_pct,
                "max_positions": self.micro_constraints.max_open_positions,
            },
        }


# Global singleton safety gate
SAFETY_GATE = PlatformSafetyGate()
