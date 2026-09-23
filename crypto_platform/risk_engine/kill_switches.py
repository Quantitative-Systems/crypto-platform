"""Crypto Trading Platform — Hierarchical Kill Switch Manager.

Provides instant, multi-level trading shutdowns accessible via API, UI, and automated SRE monitors:
- Global: Halts all trading platform-wide.
- Tenant: Halts trading for a specific customer.
- Account: Halts a specific connected broker/exchange account.
- Venue: Halts all trading routed to an exchange experiencing an outage.
- Strategy: Disables a specific strategy plugin.
- Instrument: Freezes trading on a specific symbol (e.g. de-pegs).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set
import time


@dataclass
class KillSwitchRecord:
    scope: str              # GLOBAL, TENANT, ACCOUNT, VENUE, STRATEGY, INSTRUMENT
    target: str             # target identifier or "*"
    reason: str
    activated_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    activated_by: str = "SYSTEM"


class KillSwitchManager:
    """Thread-safe hierarchical kill switch registry."""

    def __init__(self):
        self._active_switches: Dict[str, KillSwitchRecord] = {}

    def _key(self, scope: str, target: str) -> str:
        return f"{scope.upper()}:{target.upper()}"

    def activate(self, scope: str, target: str, reason: str, activated_by: str = "SYSTEM") -> None:
        key = self._key(scope, target)
        self._active_switches[key] = KillSwitchRecord(
            scope=scope.upper(),
            target=target.upper(),
            reason=reason,
            activated_by=activated_by,
        )

    def deactivate(self, scope: str, target: str) -> bool:
        key = self._key(scope, target)
        if key in self._active_switches:
            del self._active_switches[key]
            return True
        return False

    def is_active(
        self,
        tenant_id: str = "",
        account_id: str = "",
        venue: str = "",
        strategy_id: str = "",
        symbol: str = "",
    ) -> tuple[bool, str]:
        """Check all hierarchical levels. If any switch is tripped, return (True, reason)."""
        # 1. Global
        if self._key("GLOBAL", "*") in self._active_switches:
            return True, f"GLOBAL_KILL_SWITCH: {self._active_switches[self._key('GLOBAL', '*')].reason}"

        # 2. Tenant
        if tenant_id and self._key("TENANT", tenant_id) in self._active_switches:
            return True, f"TENANT_KILL_SWITCH: {self._active_switches[self._key('TENANT', tenant_id)].reason}"

        # 3. Account
        if account_id and self._key("ACCOUNT", account_id) in self._active_switches:
            return True, f"ACCOUNT_KILL_SWITCH: {self._active_switches[self._key('ACCOUNT', account_id)].reason}"

        # 4. Venue
        if venue and self._key("VENUE", venue) in self._active_switches:
            return True, f"VENUE_KILL_SWITCH: {self._active_switches[self._key('VENUE', venue)].reason}"

        # 5. Strategy
        if strategy_id and self._key("STRATEGY", strategy_id) in self._active_switches:
            return True, f"STRATEGY_KILL_SWITCH: {self._active_switches[self._key('STRATEGY', strategy_id)].reason}"

        # 6. Instrument
        if symbol and self._key("INSTRUMENT", symbol) in self._active_switches:
            return True, f"INSTRUMENT_KILL_SWITCH: {self._active_switches[self._key('INSTRUMENT', symbol)].reason}"

        return False, ""

    def list_active(self) -> Dict[str, KillSwitchRecord]:
        return dict(self._active_switches)
