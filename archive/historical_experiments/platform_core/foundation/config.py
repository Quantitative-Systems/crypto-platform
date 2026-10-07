"""
Quantitative Crypto Platform (QCP) — Platform Configuration.

Centralized configuration engine with environment detection, immutable defaults,
and strict fail-closed capital safety guards.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class Environment(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    RESEARCH = "RESEARCH"
    PAPER_TRADING = "PAPER_TRADING"
    PRODUCTION = "PRODUCTION"


@dataclass(frozen=True)
class PlatformConfig:
    environment: Environment = Environment.RESEARCH
    live_capital_enabled: bool = False
    max_portfolio_heat_pct: float = 3.00
    max_asset_allocation_pct: float = 50.00
    max_strategy_risk_pct: float = 1.50
    default_starting_equity_usd: float = 100_000.0
    telemetry_interval_sec: float = 15.0
    heartbeat_interval_sec: float = 60.0
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    
    @property
    def data_dir(self) -> Path:
        return self.base_dir / "market_data" / "cache"
        
    @property
    def results_dir(self) -> Path:
        return self.base_dir / "research" / "results"
        
    @property
    def telemetry_dir(self) -> Path:
        return self.results_dir / "telemetry"

    def validate_invariants(self) -> None:
        """Enforces mandatory platform safety invariants."""
        if self.live_capital_enabled:
            raise RuntimeError("CRITICAL INVARIANT VIOLATION: Live capital is forbidden under current directive.")
        if self.max_portfolio_heat_pct > 3.00:
            raise ValueError("CRITICAL INVARIANT VIOLATION: Portfolio heat cannot exceed 3.00% ceiling.")
            
    def to_dict(self) -> Dict[str, Any]:
        return {
            "environment": self.environment.value,
            "live_capital_enabled": self.live_capital_enabled,
            "max_portfolio_heat_pct": self.max_portfolio_heat_pct,
            "max_asset_allocation_pct": self.max_asset_allocation_pct,
            "max_strategy_risk_pct": self.max_strategy_risk_pct,
            "default_starting_equity_usd": self.default_starting_equity_usd,
            "telemetry_interval_sec": self.telemetry_interval_sec,
            "heartbeat_interval_sec": self.heartbeat_interval_sec,
            "base_dir": str(self.base_dir),
        }


def get_platform_config() -> PlatformConfig:
    env_str = os.getenv("QCP_ENV", "RESEARCH").upper()
    env = Environment.RESEARCH
    for e in Environment:
        if e.value == env_str:
            env = e
            break
            
    cfg = PlatformConfig(
        environment=env,
        live_capital_enabled=False,
        max_portfolio_heat_pct=float(os.getenv("QCP_MAX_PORTFOLIO_HEAT_PCT", 3.00)),
    )
    cfg.validate_invariants()
    return cfg


class PlatformConfigManager:
    """Convenience manager for querying and inspecting platform configuration."""

    def __init__(self, config: Optional[PlatformConfig] = None):
        self._config = config or get_platform_config()

    def get_config(self) -> PlatformConfig:
        return self._config

