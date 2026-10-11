"""Crypto Platform — Authentication & Persistence Service.

Provides durable, restart-safe user registration, credential verification,
salted PBKDF2-HMAC-SHA256 password hashing (100,000 iterations), and
cryptographically secure, hashed session tokens stored in SQLite.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from core.auth.user_model import SessionToken, User, UserRole
from core.persistence.database import DatabaseManager, get_db_manager

logger = logging.getLogger(__name__)


class AuthService:
    """Durable authentication service for Crypto Platform users."""

    PBKDF2_ITERATIONS = 100_000

    def __init__(
        self,
        session_ttl_seconds: float = 86400.0,
        db_manager: Optional[DatabaseManager] = None,
        db_path: Optional[Union[str, Path]] = None,
        in_memory: bool = False,
    ):
        self.session_ttl_seconds = session_ttl_seconds
        if db_manager is not None:
            self.db = db_manager
        else:
            self.db = get_db_manager(db_path=db_path, in_memory=in_memory)

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

    @staticmethod
    def hash_token(token_str: str) -> str:
        """Hash token using SHA-256 for secure database storage."""
        return hashlib.sha256(token_str.encode("utf-8")).hexdigest()

    def register_user(
        self,
        email: str,
        password: str,
        name: str = "",
        password_confirmation: Optional[str] = None,
        role: UserRole = UserRole.TRADER,
    ) -> User:
        """Registers a new user with dedicated tenant ID and credential validation."""
        clean_email = email.strip().lower()
        if not clean_email or "@" not in clean_email or "." not in clean_email.split("@")[-1]:
            raise ValueError("Invalid email address format.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if password_confirmation is not None and password != password_confirmation:
            raise ValueError("Password and password confirmation do not match.")

        # Check existing user in database
        existing = self.db.fetchone("SELECT user_id FROM users WHERE email = ?;", (clean_email,))
        if existing:
            raise ValueError(f"An account with email '{clean_email}' already exists.")

        pwd_hash, salt = self.hash_password(password)
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        tenant_id = f"tenant_{user_id}"
        now = time.time()

        user = User(
            user_id=user_id,
            name=name.strip(),
            email=clean_email,
            password_hash=pwd_hash,
            salt=salt,
            tenant_id=tenant_id,
            role=role,
            is_active=True,
            created_at_ts=now,
        )

        with self.db.transaction():
            self.db.execute(
                """
                INSERT INTO users (user_id, email, name, password_hash, salt, tenant_id, role, is_active, created_at_ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (user.user_id, user.email, user.name, user.password_hash, user.salt, user.tenant_id, user.role.value, 1, user.created_at_ts)
            )

        logger.info(f"Registered user {user.user_id} ({user.name}) with tenant {user.tenant_id}")
        return user

    def authenticate(self, email: str, password: str) -> Optional[SessionToken]:
        """Authenticates user credentials and issues session token."""
        clean_email = email.strip().lower()
        row = self.db.fetchone(
            "SELECT user_id, email, password_hash, salt, tenant_id, role, is_active FROM users WHERE email = ?;",
            (clean_email,)
        )
        if not row or not bool(row["is_active"]):
            return None

        computed_hash, _ = self.hash_password(password, salt=row["salt"])
        if not secrets.compare_digest(computed_hash, row["password_hash"]):
            return None

        # Issue session token
        token_str = f"strata_{secrets.token_urlsafe(32)}"
        token_hash = self.hash_token(token_str)
        now = time.time()
        expires_at = now + self.session_ttl_seconds
        prefix = token_str[:12]

        user_role = UserRole(row["role"]) if row["role"] in UserRole.__members__ else UserRole.TRADER
        session = SessionToken(
            token=token_str,
            user_id=row["user_id"],
            tenant_id=row["tenant_id"],
            role=user_role,
            created_at_ts=now,
            expires_at_ts=expires_at,
        )

        with self.db.transaction():
            self.db.execute(
                """
                INSERT INTO sessions (token_hash, user_id, tenant_id, role, created_at_ts, expires_at_ts, revoked, raw_token_prefix)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?);
                """,
                (token_hash, session.user_id, session.tenant_id, session.role.value, session.created_at_ts, session.expires_at_ts, prefix)
            )

        return session

    def validate_session(self, token_str: str) -> Optional[User]:
        """Validates session token and returns active User if valid."""
        if not token_str:
            return None

        token_hash = self.hash_token(token_str)
        now = time.time()

        row = self.db.fetchone(
            """
            SELECT s.expires_at_ts, s.revoked, u.user_id, u.email, u.name, u.password_hash, u.salt, u.tenant_id, u.role, u.is_active, u.created_at_ts
            FROM sessions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.token_hash = ?;
            """,
            (token_hash,)
        )

        if not row:
            return None

        if bool(row["revoked"]):
            return None

        if now > row["expires_at_ts"]:
            # Expired session -> mark revoked
            with self.db.transaction():
                self.db.execute("UPDATE sessions SET revoked = 1 WHERE token_hash = ?;", (token_hash,))
            return None

        if not bool(row["is_active"]):
            return None

        user_role = UserRole(row["role"]) if row["role"] in UserRole.__members__ else UserRole.TRADER
        return User(
            user_id=row["user_id"],
            name=row["name"],
            email=row["email"],
            password_hash=row["password_hash"],
            salt=row["salt"],
            tenant_id=row["tenant_id"],
            role=user_role,
            is_active=bool(row["is_active"]),
            created_at_ts=row["created_at_ts"],
        )

    def logout(self, token_str: str) -> bool:
        """Revokes an active session token."""
        if not token_str:
            return False

        token_hash = self.hash_token(token_str)
        row = self.db.fetchone("SELECT revoked FROM sessions WHERE token_hash = ?;", (token_hash,))
        if not row:
            return False

        if bool(row["revoked"]):
            return False

        with self.db.transaction():
            self.db.execute("UPDATE sessions SET revoked = 1 WHERE token_hash = ?;", (token_hash,))
        return True

    def revoke_session(self, token_str: str) -> bool:
        """Revokes session token (alias for logout)."""
        return self.logout(token_str)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Fetch user by ID."""
        row = self.db.fetchone("SELECT * FROM users WHERE user_id = ?;", (user_id,))
        if not row:
            return None
        user_role = UserRole(row["role"]) if row["role"] in UserRole.__members__ else UserRole.TRADER
        return User(
            user_id=row["user_id"],
            name=row["name"],
            email=row["email"],
            password_hash=row["password_hash"],
            salt=row["salt"],
            tenant_id=row["tenant_id"],
            role=user_role,
            is_active=bool(row["is_active"]),
            created_at_ts=row["created_at_ts"],
        )

    def get_user_watchlist(self, user_id: str) -> Set[str]:
        """Retrieve watchlist symbols for user."""
        rows = self.db.fetchall("SELECT symbol FROM user_watchlists WHERE user_id = ?;", (user_id,))
        return {r["symbol"] for r in rows}

    def set_user_watchlist(self, user_id: str, symbols: Set[str]) -> None:
        """Replace user watchlist transactionally."""
        now = time.time()
        with self.db.transaction():
            self.db.execute("DELETE FROM user_watchlists WHERE user_id = ?;", (user_id,))
            for sym in symbols:
                self.db.execute(
                    "INSERT INTO user_watchlists (user_id, symbol, created_at_ts) VALUES (?, ?, ?);",
                    (user_id, sym.strip().upper(), now)
                )

    def close(self) -> None:
        """Close database connection handle."""
        if self.db:
            self.db.close()
