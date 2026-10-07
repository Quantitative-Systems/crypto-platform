"""STRATA Digital Trading Platform — Multi-Account and Broker Account Architecture.

Manages multiple execution accounts across:
- Virtual Paper Accounts
- Exchange Testnets (Demo)
- Regulated Exchange Live Accounts (Spot & Futures)

Security Invariants:
1. API credentials are NEVER stored in source code or committed to git.
2. Credentials are only resolved from environment variables at runtime.
3. Live accounts require explicit cryptographic authorization and fail closed by default.
"""
from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AccountEnvironment(str, Enum):
    """Execution environment classification."""
    SHADOW = "SHADOW"
    PAPER = "PAPER"
    BROKER_DEMO = "BROKER_DEMO"
    MICRO_LIVE = "MICRO_LIVE"
    CONTROLLED_LIVE = "CONTROLLED_LIVE"


class BrokerVenue(str, Enum):
    """Supported broker and exchange venues."""
    SIMULATED = "SIMULATED"
    BINANCE_SPOT = "BINANCE_SPOT"
    BINANCE_FUTURES = "BINANCE_FUTURES"
    BINANCE_TESTNET = "BINANCE_TESTNET"
    BYBIT = "BYBIT"
    COINBASE = "COINBASE"


@dataclass
class AccountConfig:
    """Static configuration for a broker or paper account."""
    account_id: str
    name: str
    venue: BrokerVenue
    environment: AccountEnvironment
    is_active: bool = True
    base_currency: str = "USDT"
    initial_equity_usd: float = 100_000.0
    max_leverage: float = 1.0
    api_key_env_var: Optional[str] = None
    api_secret_env_var: Optional[str] = None
    passphrase_env_var: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_live(self) -> bool:
        return self.environment in (AccountEnvironment.MICRO_LIVE, AccountEnvironment.CONTROLLED_LIVE)

    def resolve_credentials(self) -> Dict[str, Optional[str]]:
        """Safely fetch API credentials from environment variables."""
        return {
            "api_key": os.environ.get(self.api_key_env_var) if self.api_key_env_var else None,
            "api_secret": os.environ.get(self.api_secret_env_var) if self.api_secret_env_var else None,
            "passphrase": os.environ.get(self.passphrase_env_var) if self.passphrase_env_var else None,
        }


@dataclass
class AccountSnapshot:
    """Dynamic operational state of an account."""
    account_id: str
    name: str
    venue: BrokerVenue
    environment: AccountEnvironment
    total_equity_usd: float
    available_margin_usd: float
    maintenance_margin_usd: float
    unrealized_pnl_usd: float
    realized_pnl_usd: float
    open_positions_count: int
    open_orders_count: int
    health_ratio: float  # Margin health (1.0 = 100% healthy)
    is_connected: bool
    last_sync_timestamp_ms: int
    status_message: str = "NORMAL"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "name": self.name,
            "venue": self.venue.value,
            "environment": self.environment.value,
            "total_equity_usd": round(self.total_equity_usd, 2),
            "available_margin_usd": round(self.available_margin_usd, 2),
            "maintenance_margin_usd": round(self.maintenance_margin_usd, 2),
            "unrealized_pnl_usd": round(self.unrealized_pnl_usd, 2),
            "realized_pnl_usd": round(self.realized_pnl_usd, 2),
            "open_positions_count": self.open_positions_count,
            "open_orders_count": self.open_orders_count,
            "health_ratio": round(self.health_ratio, 4),
            "is_connected": self.is_connected,
            "last_sync_timestamp_ms": self.last_sync_timestamp_ms,
            "status_message": self.status_message,
        }


class AccountManager:
    """Central repository and manager for broker and simulated accounts."""

    def __init__(self):
        self._accounts: Dict[str, AccountConfig] = {}
        self._snapshots: Dict[str, AccountSnapshot] = {}
        self._active_account_id: Optional[str] = None
        self._initialize_default_accounts()

    def _initialize_default_accounts(self) -> None:
        """Register the platform's standard default institutional accounts."""
        # 1. Primary Paper Trading Account
        paper_acc = AccountConfig(
            account_id="ACC_PAPER_PRIMARY",
            name="Strata Paper Primary (Simulated)",
            venue=BrokerVenue.SIMULATED,
            environment=AccountEnvironment.PAPER,
            initial_equity_usd=100_000.0,
            max_leverage=1.0,
        )
        self.register_account(paper_acc)

        # 2. Binance Testnet (Broker Demo) Account
        demo_acc = AccountConfig(
            account_id="ACC_BINANCE_DEMO",
            name="Binance Futures Testnet (Demo)",
            venue=BrokerVenue.BINANCE_TESTNET,
            environment=AccountEnvironment.BROKER_DEMO,
            initial_equity_usd=10_000.0,
            max_leverage=2.0,
            api_key_env_var="BINANCE_TESTNET_API_KEY",
            api_secret_env_var="BINANCE_TESTNET_API_SECRET",
        )
        self.register_account(demo_acc)

        # 3. Micro-Live Account (Hard-gated, fails closed)
        micro_acc = AccountConfig(
            account_id="ACC_BINANCE_MICRO_LIVE",
            name="Binance Micro-Live (Fail-Closed)",
            venue=BrokerVenue.BINANCE_FUTURES,
            environment=AccountEnvironment.MICRO_LIVE,
            initial_equity_usd=500.0,
            max_leverage=1.0,
            api_key_env_var="BINANCE_LIVE_API_KEY",
            api_secret_env_var="BINANCE_LIVE_API_SECRET",
        )
        self.register_account(micro_acc)

        # Default active account is Paper Primary
        self._active_account_id = paper_acc.account_id

    def register_account(self, config: AccountConfig) -> None:
        """Register a new broker account configuration."""
        self._accounts[config.account_id] = config
        self._snapshots[config.account_id] = AccountSnapshot(
            account_id=config.account_id,
            name=config.name,
            venue=config.venue,
            environment=config.environment,
            total_equity_usd=config.initial_equity_usd,
            available_margin_usd=config.initial_equity_usd,
            maintenance_margin_usd=0.0,
            unrealized_pnl_usd=0.0,
            realized_pnl_usd=0.0,
            open_positions_count=0,
            open_orders_count=0,
            health_ratio=1.0,
            is_connected=True,
            last_sync_timestamp_ms=0,
            status_message="READY",
        )
        logger.info(f"Account registered: {config.account_id} ({config.name}) [{config.environment.value}]")

    def get_account_config(self, account_id: str) -> Optional[AccountConfig]:
        return self._accounts.get(account_id)

    def get_account_snapshot(self, account_id: str) -> Optional[AccountSnapshot]:
        return self._snapshots.get(account_id)

    def get_active_account(self) -> AccountConfig:
        if not self._active_account_id or self._active_account_id not in self._accounts:
            self._active_account_id = "ACC_PAPER_PRIMARY"
        return self._accounts[self._active_account_id]

    def set_active_account(self, account_id: str) -> None:
        if account_id not in self._accounts:
            raise ValueError(f"Unknown account_id: {account_id}")
        self._active_account_id = account_id
        logger.info(f"Active account switched to: {account_id}")

    def list_accounts(self) -> List[Dict[str, Any]]:
        """Return list of all accounts with current snapshot data."""
        results = []
        for acc_id, config in self._accounts.items():
            snap = self._snapshots.get(acc_id)
            d = snap.to_dict() if snap else {}
            d["is_active_account"] = (acc_id == self._active_account_id)
            d["is_live"] = config.is_live
            results.append(d)
        return results

    def update_snapshot(self, account_id: str, **kwargs: Any) -> None:
        """Update snapshot metrics for an account."""
        if account_id in self._snapshots:
            snap = self._snapshots[account_id]
            for k, v in kwargs.items():
                if hasattr(snap, k):
                    setattr(snap, k, v)
