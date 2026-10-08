"""STRATA — Authentication Service.

Provides secure password hashing (PBKDF2-HMAC-SHA256, 100k iterations), user registration,
credential verification, and cryptographically secure session management.
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
import uuid
from typing import Dict, Optional, Tuple

from core.auth.user_model import SessionToken, User, UserRole

logger = logging.getLogger(__name__)


class AuthService:
    """Production authentication service for STRATA users."""

    PBKDF2_ITERATIONS = 100_000

    def __init__(self, session_ttl_seconds: float = 86400.0):
        self.session_ttl_seconds = session_ttl_seconds
        self._users_by_email: Dict[str, User] = {}
        self._users_by_id: Dict[str, User] = {}
        self._active_sessions: Dict[str, SessionToken] = {}

    @classmethod
    def hash_password(cls, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hashes password using PBKDF2-HMAC-SHA256 with cryptographic salt."""
        salt_bytes = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt_bytes,
            cls.PBKDF2_ITERATIONS,
        )
        return pwd_hash.hex(), salt_bytes.hex()

    def register_user(
        self,
        email: str,
        password: str,
        role: UserRole = UserRole.TRADER,
    ) -> User:
        """Registers a new user with dedicated tenant ID."""
        clean_email = email.strip().lower()
        if not clean_email or "@" not in clean_email:
            raise ValueError("Invalid email format")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        if clean_email in self._users_by_email:
            raise ValueError(f"User with email '{clean_email}' already exists")

        pwd_hash, salt = self.hash_password(password)
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        tenant_id = f"tenant_{user_id}"

        user = User(
            user_id=user_id,
            email=clean_email,
            password_hash=pwd_hash,
            salt=salt,
            tenant_id=tenant_id,
            role=role,
            is_active=True,
        )

        self._users_by_email[clean_email] = user
        self._users_by_id[user_id] = user
        logger.info(f"Registered user {user.user_id} with tenant {user.tenant_id}")
        return user

    def authenticate(self, email: str, password: str) -> Optional[SessionToken]:
        """Authenticates user credentials and issues session token."""
        clean_email = email.strip().lower()
        user = self._users_by_email.get(clean_email)
        if not user or not user.is_active:
            return None

        computed_hash, _ = self.hash_password(password, salt=user.salt)
        if not secrets.compare_digest(computed_hash, user.password_hash):
            return None

        # Issue session token
        token_str = f"strata_{secrets.token_urlsafe(32)}"
        now = time.time()
        session = SessionToken(
            token=token_str,
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            role=user.role,
            created_at_ts=now,
            expires_at_ts=now + self.session_ttl_seconds,
        )

        self._active_sessions[token_str] = session
        return session

    def validate_session(self, token_str: str) -> Optional[User]:
        """Validates session token and returns active User if valid."""
        session = self._active_sessions.get(token_str)
        if not session or session.is_expired:
            if session and session.is_expired:
                del self._active_sessions[token_str]
            return None

        return self._users_by_id.get(session.user_id)

    def logout(self, token_str: str) -> bool:
        """Revokes an active session token."""
        if token_str in self._active_sessions:
            del self._active_sessions[token_str]
            return True
        return False
