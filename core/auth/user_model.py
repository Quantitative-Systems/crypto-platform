"""STRATA — Authentication & User Data Models.

Defines users, credentials, roles, and cryptographic session tokens for multi-tenant isolation.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class UserRole(str, Enum):
    TRADER = "TRADER"
    RESEARCHER = "RESEARCHER"
    ADMIN = "ADMIN"


@dataclass
class User:
    user_id: str
    email: str
    password_hash: str
    salt: str
    tenant_id: str
    name: str = ""
    role: UserRole = UserRole.TRADER
    is_active: bool = True
    created_at_ts: float = field(default_factory=time.time)

    def to_safe_dict(self) -> Dict[str, Any]:
        """Returns safe user representation excluding password hash and salt."""
        return {
            "user_id": self.user_id,
            "name": self.name or self.email.split("@")[0].title(),
            "email": self.email,
            "tenant_id": self.tenant_id,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at_ts": self.created_at_ts,
        }


@dataclass
class SessionToken:
    token: str
    user_id: str
    tenant_id: str
    role: UserRole
    created_at_ts: float
    expires_at_ts: float

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at_ts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token": self.token,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "role": self.role.value,
            "created_at_ts": self.created_at_ts,
            "expires_at_ts": self.expires_at_ts,
        }
