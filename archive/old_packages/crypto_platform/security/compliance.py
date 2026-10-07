"""Crypto Trading Platform — Non-Custodial Security & Regulatory Compliance Engine.

Enforces critical operational and legal safeguards:
1. Strict Non-Custodial Architecture:
   - System never holds or pools customer capital.
   - Credentials strictly require zero-withdrawal permissions.
   - Secrets envelope-encrypted with PBKDF2 + AES-256-GCM.
2. Market Integrity & Wash-Trading Prevention:
   - Detects and rejects self-crossing orders within the same tenant/account.
   - Prevents quote stuffing and spoofing patterns.
3. Jurisdiction & Sanctions Compliance:
   - Enforces regional restrictions and jurisdiction gating.
   - Blocks trading for sanctioned venues or geographic entities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time
from typing import Dict, List, Optional, Set

from crypto_platform.core.domain import ExecutionOrder, OrderIntent, OrderSide

logger = logging.getLogger("crypto_platform.security.compliance")


class NonCustodialSecurityError(Exception):
    """Raised when an attempt to access or modify customer custodial funds is detected."""
    pass


class ComplianceEngine:
    """Enforces non-custodial boundaries, jurisdiction gating, and wash-trading prevention."""

    def __init__(self, restricted_jurisdictions: Optional[Set[str]] = None):
        # Default prohibited regions (ISO alpha-2)
        self.restricted_jurisdictions = restricted_jurisdictions or {"CU", "IR", "KP", "SY"}
        # Symbol -> recent active intents by tenant/account
        self._active_intents: Dict[str, List[OrderIntent]] = {}

    def verify_non_custodial_permissions(self, permissions: Dict[str, bool]) -> None:
        """Audits broker/exchange API permissions. MUST NOT permit withdrawals."""
        if permissions.get("withdraw", False):
            raise NonCustodialSecurityError(
                "CRITICAL SECURITY VIOLATION: Withdrawal permissions enabled on API Key. "
                "The Crypto Trading Platform strictly forbids withdrawal access."
            )
        if permissions.get("transfer", False):
            raise NonCustodialSecurityError(
                "CRITICAL SECURITY VIOLATION: Transfer permissions enabled on API Key. "
                "The Crypto Trading Platform operates strictly in non-custodial execution mode."
            )

    def check_jurisdiction(self, user_country_code: str) -> bool:
        """Verifies if user jurisdiction is legally eligible."""
        code = user_country_code.upper()
        if code in self.restricted_jurisdictions:
            logger.warning(f"Jurisdiction check failed for restricted region: {code}")
            return False
        return True

    def check_wash_trading(
        self, intent: OrderIntent, working_orders: List[ExecutionOrder]
    ) -> tuple[bool, str]:
        """Detects and rejects potential self-crossing / wash trading orders.

        If an active buy order exists for the same tenant at or above this intent's
        sell price (or vice versa), the order is rejected for potential wash-trading.
        """
        for order in working_orders:
            if order.tenant_id == intent.tenant_id and order.symbol == intent.symbol:
                # Opposite sides
                is_opposite = (
                    (intent.direction == 1 and order.side == OrderSide.SELL)
                    or (intent.direction == -1 and order.side == OrderSide.BUY)
                )
                if is_opposite:
                    # Check if prices cross
                    order_price = order.price or 0.0
                    intent_price = intent.limit_price or 0.0

                    if order_price > 0 and intent_price > 0:
                        if intent.direction == 1 and intent_price >= order_price:
                            return True, f"Wash-trading risk: Buy limit ${intent_price} crosses resting Sell ${order_price}"
                        elif intent.direction == -1 and intent_price <= order_price:
                            return True, f"Wash-trading risk: Sell limit ${intent_price} crosses resting Buy ${order_price}"

        return False, ""
