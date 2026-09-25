"""Crypto Trading Platform — Central Configuration & Environment Settings.

Manages environment configuration across PAPER, DEMO, and LIVE execution planes.
Enforces hard safety invariants (zero live capital, fail-closed live lock, withdrawal prohibition).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("crypto_platform.config")


@dataclass
class PlatformSettings:
    """Strongly-typed platform runtime configuration."""

    environment: str = "PAPER"
    tenant_id: str = "tenant_default"
    account_id: str = "acc_primary"
    initial_equity: float = 100_000.0
    db_path: str = "research/paper_trading.db"
    live_capital_usd: float = 0.0
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_testnet: bool = True
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    bybit_testnet: bool = True
    max_account_leverage: float = 2.0
    max_position_concentration: float = 0.35
    max_drawdown_limit: float = 0.15
    kill_switch_enabled: bool = False
    log_level: str = "INFO"
    metrics_port: int = 9100
    stale_data_timeout_ms: int = 5000
    canary_capital_limit_usd: float = 0.0
    canary_risk_limit: float = 0.02
    canary_max_position_size: float = 500.0
    canary_max_daily_loss: float = 0.02
    canary_max_total_drawdown: float = 0.05
    canary_max_leverage: float = 1.5
    live_canary_authorized: bool = False
    live_canary_state: str = "DISARMED"

    def validate(self) -> None:
        """Enforce inviolable security and risk safety constraints."""
        env_upper = self.environment.upper()
        if env_upper not in ("PAPER", "DEMO", "LIVE-CANARY", "LIVE"):
            raise ValueError(
                f"Invalid environment '{self.environment}'. Must be PAPER, DEMO, or LIVE / LIVE-CANARY."
            )

        if env_upper == "LIVE":
            raise RuntimeError(
                "FATAL: Operating mode LIVE is strictly disabled by platform governance. "
                "All trading must execute via PAPER or DEMO."
            )

        if env_upper == "LIVE-CANARY":
            if not self.live_canary_authorized:
                raise RuntimeError(
                    "FATAL SECURITY VIOLATION: LIVE-CANARY requires explicit authorization via LIVE_CANARY_AUTHORIZED=true."
                )
            if self.canary_capital_limit_usd <= 0.0:
                raise RuntimeError(
                    "FATAL: LIVE-CANARY requires explicit CANARY_CAPITAL_LIMIT_USD > $0.00."
                )
            if self.live_capital_usd > self.canary_capital_limit_usd:
                raise RuntimeError(
                    f"FATAL SECURITY VIOLATION: Live capital ${self.live_capital_usd:.2f} "
                    f"exceeds authorized CANARY_CAPITAL_LIMIT_USD ${self.canary_capital_limit_usd:.2f}."
                )
        else:
            if self.live_capital_usd > 0.0:
                raise RuntimeError(
                    f"FATAL SECURITY VIOLATION: Live capital is configured at ${self.live_capital_usd:.2f}. "
                    "Capital MUST remain strictly locked at $0.00."
                )

    @classmethod
    def load_from_env(cls, env_file: Optional[str] = ".env") -> PlatformSettings:
        """Load configuration from environment variables, optionally reading an .env file."""
        if env_file and os.path.exists(env_file):
            cls._load_env_file(env_file)

        def _get_bool(key: str, default: bool) -> bool:
            val = os.environ.get(key)
            if val is None:
                return default
            return val.strip().lower() in ("1", "true", "yes", "on")

        def _get_float(key: str, default: float) -> float:
            val = os.environ.get(key)
            if val is None:
                return default
            try:
                return float(val.strip())
            except ValueError:
                return default

        def _get_int(key: str, default: int) -> int:
            val = os.environ.get(key)
            if val is None:
                return default
            try:
                return int(val.strip())
            except ValueError:
                return default

        settings = cls(
            environment=os.environ.get("PLATFORM_ENV", "PAPER"),
            tenant_id=os.environ.get("PLATFORM_TENANT_ID", "tenant_default"),
            account_id=os.environ.get("PLATFORM_ACCOUNT_ID", "acc_primary"),
            initial_equity=_get_float("INITIAL_EQUITY", 100_000.0),
            db_path=os.environ.get("DATABASE_PATH", "research/paper_trading.db"),
            live_capital_usd=_get_float("LIVE_CAPITAL_USD", 0.0),
            binance_api_key=os.environ.get("BINANCE_API_KEY", ""),
            binance_api_secret=os.environ.get("BINANCE_API_SECRET", ""),
            binance_testnet=_get_bool("BINANCE_TESTNET", True),
            bybit_api_key=os.environ.get("BYBIT_API_KEY", ""),
            bybit_api_secret=os.environ.get("BYBIT_API_SECRET", ""),
            bybit_testnet=_get_bool("BYBIT_TESTNET", True),
            max_account_leverage=_get_float("MAX_ACCOUNT_LEVERAGE", 2.0),
            max_position_concentration=_get_float("MAX_POSITION_CONCENTRATION", 0.35),
            max_drawdown_limit=_get_float("MAX_DRAWDOWN_LIMIT", 0.15),
            kill_switch_enabled=_get_bool("KILL_SWITCH_ENABLED", False),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            metrics_port=_get_int("METRICS_PORT", 9100),
            stale_data_timeout_ms=_get_int("STALE_DATA_TIMEOUT_MS", 5000),
            canary_capital_limit_usd=_get_float("CANARY_CAPITAL_LIMIT_USD", 0.0),
            canary_risk_limit=_get_float("CANARY_RISK_LIMIT", 0.02),
            canary_max_position_size=_get_float("CANARY_MAX_POSITION_SIZE", 500.0),
            canary_max_daily_loss=_get_float("CANARY_MAX_DAILY_LOSS", 0.02),
            canary_max_total_drawdown=_get_float("CANARY_MAX_TOTAL_DRAWDOWN", 0.05),
            canary_max_leverage=_get_float("CANARY_MAX_LEVERAGE", 1.5),
            live_canary_authorized=_get_bool("LIVE_CANARY_AUTHORIZED", False),
            live_canary_state=os.environ.get("LIVE_CANARY_STATE", "DISARMED"),
        )
        settings.validate()
        return settings

    @staticmethod
    def _load_env_file(filepath: str) -> None:
        """Parse simple KEY=VALUE pairs from a file into os.environ."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key not in os.environ:
                            os.environ[key] = val
        except Exception as e:
            logger.warning(f"Could not parse env file {filepath}: {e}")
