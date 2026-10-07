"""Phase R — Frozen Q.2 Research Contract Runtime Guard.

Enforces absolute invariance of the Phase Q.2 research contract during runtime.
Prevents accidental parameter tuning, live capital enablement, target distortion,
or risk boundary tampering.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

CONTRACT_PATH = Path(__file__).resolve().parent / "PHASE_R_FROZEN_Q2_CONTRACT.json"


class FrozenContractViolationError(RuntimeError):
    """Raised when an operation attempts to violate the immutable Phase Q.2 contract."""
    pass


class FrozenContractGuard:
    """Singleton runtime guard that asserts research parameters match frozen constants."""

    _instance: Optional[FrozenContractGuard] = None

    def __init__(self, contract_path: Optional[Path] = None):
        self.path = contract_path or CONTRACT_PATH
        if not self.path.exists():
            raise FileNotFoundError(f"Frozen contract missing at {self.path}")
        with open(self.path, "r", encoding="utf-8") as f:
            self.contract: Dict[str, Any] = json.load(f)

    @classmethod
    def get_instance(cls) -> FrozenContractGuard:
        if cls._instance is None:
            cls._instance = FrozenContractGuard()
        return cls._instance

    def assert_capital_safety(self, real_capital_authorized: float, live_trading_enabled: bool) -> None:
        """Asserts that real capital remains strictly $0.00 and live trading is disabled."""
        if real_capital_authorized > 0.0:
            raise FrozenContractViolationError(
                f"FATAL: Real capital authorization ({real_capital_authorized}) violates frozen $0.00 policy!"
            )
        if live_trading_enabled:
            raise FrozenContractViolationError(
                "FATAL: Live trading enabled violates Phase R frozen safety boundary!"
            )

    def assert_confidence_weights(self, weights: Dict[str, float]) -> None:
        """Asserts that confidence weights match the frozen contract exactly."""
        frozen_weights = self.contract["confidence_system"]["weights"]
        for k, v in frozen_weights.items():
            if abs(weights.get(k, 0.0) - v) > 1e-6:
                raise FrozenContractViolationError(
                    f"FATAL: Confidence weight '{k}'={weights.get(k)} diverged from frozen value {v}!"
                )

    def assert_target_floor(self, planned_r: float) -> None:
        """Asserts that every trade candidate satisfies the >= 4.0R destination floor."""
        floor = self.contract["target_geometry"]["minimum_destination_r"]
        if planned_r < floor:
            raise FrozenContractViolationError(
                f"FATAL: Planned target {planned_r:.2f}R is below the frozen floor of {floor:.1f}R!"
            )

    def assert_risk_limits(self, risk_pct: float, asset_heat_pct: float, total_heat_pct: float) -> None:
        """Asserts that trade and portfolio risk do not exceed frozen governor thresholds."""
        max_trade = self.contract["risk_governance"]["max_risk_per_trade_pct"]
        max_asset = self.contract["risk_governance"]["max_base_asset_exposure_pct"]
        max_heat = self.contract["risk_governance"]["max_total_portfolio_heat_pct"]

        if risk_pct > max_trade + 1e-6:
            raise FrozenContractViolationError(
                f"FATAL: Trade risk {risk_pct:.2f}% exceeds frozen limit {max_trade:.2f}%!"
            )
        if asset_heat_pct > max_asset + 1e-6:
            raise FrozenContractViolationError(
                f"FATAL: Asset exposure {asset_heat_pct:.2f}% exceeds frozen limit {max_asset:.2f}%!"
            )
        if total_heat_pct > max_heat + 1e-6:
            raise FrozenContractViolationError(
                f"FATAL: Portfolio heat {total_heat_pct:.2f}% exceeds frozen limit {max_heat:.2f}%!"
            )


# Global guard access
FROZEN_GUARD = FrozenContractGuard.get_instance()
