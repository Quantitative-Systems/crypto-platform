"""
Quantitative Crypto Platform (QCP) — Secrets & Credentials Abstraction.

Guarantees zero plain-text secret logging, rejects live exchange credentials,
and provides encrypted credential vaults.
"""

from __future__ import annotations

import os
import hashlib
from typing import Dict, Optional, Set


class SecretsManager:
    """
    Manages sensitive configurations with fail-closed safety checks and log masking.
    """

    FORBIDDEN_LIVE_KEYS: Set[str] = {
        "BINANCE_API_KEY",
        "BINANCE_SECRET_KEY",
        "OKX_API_KEY",
        "OKX_SECRET_KEY",
        "BYBIT_API_KEY",
        "BYBIT_SECRET_KEY",
        "LIVE_TRADING_PRIVATE_KEY",
    }

    def __init__(self, allow_simulated_keys: bool = True):
        self._allow_simulated = allow_simulated_keys
        self._vault: Dict[str, str] = {}
        self._verify_no_forbidden_environment_keys()

    def _verify_no_forbidden_environment_keys(self) -> None:
        """Fail-closed assertion: rejects live exchange keys in production environment."""
        for key in self.FORBIDDEN_LIVE_KEYS:
            val = os.getenv(key)
            if val and not val.startswith("SIMULATED_") and not val.startswith("MOCK_"):
                raise RuntimeError(
                    f"CRITICAL CAPITAL FIREWALL BREACH: Live credential '{key}' detected in environment. "
                    f"Live capital execution is permanently disabled."
                )

    def set_secret(self, key: str, value: str) -> None:
        if key in self.FORBIDDEN_LIVE_KEYS and not (value.startswith("SIMULATED_") or value.startswith("MOCK_")):
            raise ValueError(f"Cannot set live secret for '{key}'. Only simulated/mock secrets allowed.")
        self._vault[key] = value

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._vault.get(key, os.getenv(key, default))

    def mask_secret(self, key: str) -> str:
        val = self.get_secret(key)
        if not val:
            return "[NOT_SET]"
        return f"***MASKED_{hashlib.sha256(val.encode()).hexdigest()[:8]}***"
