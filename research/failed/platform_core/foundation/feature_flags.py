"""
Quantitative Crypto Platform (QCP) — Dynamic Feature Flag Manager.

Controls runtime activation of platform features with fail-closed defaults
and immutable safety locks.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class FeatureFlags:
    """
    Central feature flags manager.
    """

    _flags: Dict[str, bool] = field(
        default_factory=lambda: {
            "LIVE_CAPITAL_TRADING": False,          # PERMANENTLY LOCKED FALSE
            "PAPER_TRADING_ENABLED": True,
            "DERIVATIVES_ENGINE_ENABLED": True,
            "MARKET_MAKING_ENABLED": True,
            "LOW_LATENCY_BUS_ENABLED": True,
            "MULTI_TENANCY_ENABLED": True,
            "SAAS_BILLING_ENABLED": True,
            "PROMETHEUS_METRICS_ENABLED": True,
            "DISASTER_RECOVERY_CHAOS_ENABLED": False,
        }
    )

    def is_enabled(self, flag_name: str) -> bool:
        # Immutable safety lock: LIVE_CAPITAL_TRADING can NEVER be enabled
        if flag_name == "LIVE_CAPITAL_TRADING":
            return False
        # Environment override
        env_val = os.getenv(f"QCP_FLAG_{flag_name}")
        if env_val is not None:
            return env_val.lower() in ("1", "true", "yes", "enabled")
        return self._flags.get(flag_name, False)

    def set_flag(self, flag_name: str, enabled: bool) -> None:
        if flag_name == "LIVE_CAPITAL_TRADING" and enabled:
            raise RuntimeError("CRITICAL SAFETY LOCK: LIVE_CAPITAL_TRADING cannot be enabled.")
        self._flags[flag_name] = enabled

    def get_all_flags(self) -> Dict[str, bool]:
        return {k: self.is_enabled(k) for k in self._flags}


FeatureFlagsManager = FeatureFlags


_GLOBAL_FLAGS = FeatureFlags()


def get_feature_flags() -> FeatureFlags:
    return _GLOBAL_FLAGS
