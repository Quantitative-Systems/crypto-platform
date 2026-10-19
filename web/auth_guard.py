"""Crypto Platform — API Authentication and Authorization Guard.

Enforces:
1. Bearer token extraction and validation against durable AuthService sessions.
2. Immediate 401 Unauthorized for missing, invalid, expired, or revoked tokens.
3. Strict Role-Based Access Control (RBAC) with 403 Forbidden for insufficient permissions.
4. Tenant context binding (request["user"] and request["tenant_id"]) to enforce multi-tenant isolation.
"""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Iterable, List, Optional, Set, Union
from aiohttp import web

from core.auth.user_model import User, UserRole

logger = logging.getLogger(__name__)


USER_KEY: web.RequestKey[User] = web.RequestKey("user", User)
TENANT_ID_KEY: web.RequestKey[str] = web.RequestKey("tenant_id", str)


def extract_bearer_token(request: web.Request) -> Optional[str]:
    """Extracts the Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        token_param = request.query.get("token", "").strip()
        return token_param if token_param else None

    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        return token if token else None

    return auth_header


def get_authenticated_user(request: web.Request) -> Optional[User]:
    """Convenience helper to retrieve the authenticated user from request context."""
    return request.get(USER_KEY) or request.get("user")


def get_authenticated_tenant_id(request: web.Request) -> Optional[str]:
    """Convenience helper to retrieve the authenticated tenant_id from request context."""
    return request.get(TENANT_ID_KEY) or request.get("tenant_id")


def require_auth(
    required_roles: Optional[Union[UserRole, Iterable[UserRole]]] = None
) -> Callable:
    """Decorator requiring valid authentication and optional role authorization.

    Returns:
        401 Unauthorized if token is missing, invalid, expired, or revoked.
        403 Forbidden if user is inactive or lacks required roles.
    """
    allowed_roles: Optional[Set[UserRole]] = None
    if isinstance(required_roles, UserRole):
        allowed_roles = {required_roles}
    elif required_roles is not None:
        allowed_roles = set(required_roles)

    def decorator(handler: Callable) -> Callable:
        @functools.wraps(handler)
        async def wrapper(self: Any, request: web.Request, *args: Any, **kwargs: Any) -> web.Response:
            token = extract_bearer_token(request)
            if not token:
                return web.json_response(
                    {
                        "error": "Authentication required. Missing Authorization header.",
                        "status": 401,
                    },
                    status=401,
                )

            auth_service = getattr(self, "auth_service", None)
            if auth_service is None:
                return web.json_response(
                    {"error": "Authentication service unavailable.", "status": 500},
                    status=500,
                )

            user: Optional[User] = auth_service.validate_session(token)
            if not user:
                return web.json_response(
                    {
                        "error": "Invalid, expired, or revoked session token.",
                        "status": 401,
                    },
                    status=401,
                )

            if not user.is_active:
                return web.json_response(
                    {"error": "User account is deactivated.", "status": 403},
                    status=403,
                )

            if allowed_roles and user.role not in allowed_roles:
                return web.json_response(
                    {
                        "error": f"Forbidden: Insufficient permissions. Required role: {[r.value for r in allowed_roles]}, user role: {user.role.value}",
                        "status": 403,
                    },
                    status=403,
                )

            request[USER_KEY] = user
            request[TENANT_ID_KEY] = user.tenant_id
            return await handler(self, request, *args, **kwargs)

        return wrapper

    return decorator
