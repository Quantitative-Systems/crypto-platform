"""Crypto Platform — Production Web Security Middleware.

Implements institutional web security:
1. Hardened Security & CORS Headers:
   - X-Frame-Options: DENY (clickjacking protection)
   - X-Content-Type-Options: nosniff (MIME sniffing prevention)
   - X-XSS-Protection: 1; mode=block
   - Referrer-Policy: strict-origin-when-cross-origin
   - Access-Control-Allow-Origin: * (CORS support for cloud staging & mobile apps)
2. Sliding-Window Rate Limiter per client IP (prevents DoS and brute-force).
3. Structured Problem Details (RFC 7807) error handler without stack trace leakage.
"""
from __future__ import annotations

import collections
import logging
import time
from typing import Callable, Deque, Dict
from aiohttp import web

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding-window IP rate limiter."""

    def __init__(self, max_requests_per_window: int = 120, window_seconds: float = 60.0):
        self.max_requests = max_requests_per_window
        self.window_seconds = window_seconds
        self.ip_hits: Dict[str, Deque[float]] = collections.defaultdict(collections.deque)

    def is_allowed(self, ip: str) -> bool:
        now = time.time()
        hits = self.ip_hits[ip]

        # Purge hits outside sliding window
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()

        if len(hits) >= self.max_requests:
            return False

        hits.append(now)
        return True


@web.middleware
async def security_headers_middleware(request: web.Request, handler: Callable) -> web.Response:
    """Appends OWASP-recommended security and CORS headers to all HTTP responses."""
    if request.method == "OPTIONS":
        # Handle CORS preflight
        response = web.Response(status=204)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Tenant-ID, Accept"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

    try:
        response = await handler(request)
    except web.HTTPException as http_ex:
        response = http_ex
    except Exception as ex:
        logger.error(f"Unhandled server exception: {ex}", exc_info=True)
        response = web.json_response(
            {
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An internal operational error occurred. Details have been logged securely.",
            },
            status=500,
        )

    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Server"] = "Crypto-Platform-Gateway"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Tenant-ID, Accept"
    return response


def create_rate_limit_middleware(max_requests: int = 120, window_seconds: float = 60.0):
    limiter = RateLimiter(max_requests, window_seconds)

    @web.middleware
    async def rate_limit_middleware(request: web.Request, handler: Callable) -> web.Response:
        client_ip = request.remote or "unknown"
        if not limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for client IP: {client_ip}")
            return web.json_response(
                {
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": "Client rate limit exceeded. Please throttle request frequency.",
                },
                status=429,
            )
        return await handler(request)

    return rate_limit_middleware
