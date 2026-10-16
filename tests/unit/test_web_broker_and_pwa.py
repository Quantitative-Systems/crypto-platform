"""Unit Test Suite for Unified Single-Server Web, Mobile PWA, and Broker Connectivity.

Verifies:
1. Public Website (/) and Terminal (/app) rendering.
2. PWA Manifest (/manifest.json) and Service Worker (/sw.js) delivery.
3. Broker Connection API (/api/brokers/connect) with non-custodial validation.
4. Security firewall rejection of withdrawal permissions.
5. Active Broker Registry (/api/brokers/active) and Disconnect flow.
"""
from __future__ import annotations

import json
import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from web.server import PhaseRWebServer


class TestWebBrokerAndPwa(AioHTTPTestCase):
    """Rigorous verification of the unified server, PWA, and broker connectivity."""

    async def get_application(self) -> web.Application:
        # Instantiate web server with mock/simulated supervisor
        self.server = PhaseRWebServer(supervisor=None, host="127.0.0.1", port=8080)
        return self.server.app

    @unittest_run_loop
    async def test_public_website_delivery(self):
        """Tests that public website root / delivers the modern landing page."""
        resp = await self.client.get("/")
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.content_type, "text/html")
        text = await resp.text()
        self.assertIn("Autonomous Multi-Timeframe", text)
        self.assertIn("3-Pillar", text)
        self.assertIn("Connect Broker", text)

    @unittest_run_loop
    async def test_terminal_workstation_delivery(self):
        """Tests that /app delivers the quantitative workstation with broker modal."""
        resp = await self.client.get("/app")
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.content_type, "text/html")
        text = await resp.text()
        self.assertTrue(any(b in text for b in ("Crypto Engine", "Crypto Platform")))
        self.assertIn("connect-broker-modal", text)
        self.assertIn("mobile-bottom-nav", text)

    @unittest_run_loop
    async def test_pwa_manifest_delivery(self):
        """Tests that /manifest.json delivers valid PWA configuration."""
        resp = await self.client.get("/manifest.json")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertIn("name", data)
        self.assertEqual(data["display"], "standalone")
        self.assertEqual(data["start_url"], "/dashboard")

    @unittest_run_loop
    async def test_pwa_service_worker_delivery(self):
        """Tests that /sw.js delivers the service worker."""
        resp = await self.client.get("/sw.js")
        self.assertEqual(resp.status, 200)
        text = await resp.text()
        self.assertIn("Service Worker", text)
        self.assertIn("CACHE_NAME", text)

    @unittest_run_loop
    async def test_broker_connect_non_custodial_success(self):
        """Tests successful connection of Binance testnet broker with trade-only permissions."""
        payload = {
            "venue": "BINANCE",
            "api_key": "test_key_binance_12345678",
            "api_secret": "test_secret_binance_abcdefgh",
            "is_testnet": True,
            "permissions": {
                "enableSpotAndMarginTrading": True,
                "enableFutures": True,
                "enableWithdrawals": False
            }
        }
        resp = await self.client.post("/api/brokers/connect", json=payload)
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "CONNECTED")
        self.assertEqual(data["venue"], "BINANCE")
        self.assertTrue(data["non_custodial_verified"])

        # Check that it appears in active brokers
        active_resp = await self.client.get("/api/brokers/active")
        self.assertEqual(active_resp.status, 200)
        active_list = await active_resp.json()
        venues = [b["venue"] for b in active_list]
        self.assertIn("BINANCE", venues)

    @unittest_run_loop
    async def test_broker_connect_security_firewall_rejection(self):
        """Tests that an API key with withdrawal permissions is strictly rejected."""
        unsafe_payload = {
            "venue": "BYBIT",
            "api_key": "unsafe_bybit_key_1234",
            "api_secret": "unsafe_secret",
            "is_testnet": True,
            "permissions": {
                "enableSpotAndMarginTrading": True,
                "enableWithdrawals": True  # FORBIDDEN
            }
        }
        resp = await self.client.post("/api/brokers/connect", json=unsafe_payload)
        self.assertEqual(resp.status, 400)
        data = await resp.json()
        self.assertEqual(data["status"], "REJECTED_UNSAFE_PERMISSIONS")
        self.assertIn("SECURITY BREACH", data["error"])

    @unittest_run_loop
    async def test_broker_disconnect_flow(self):
        """Tests disconnecting an active exchange account."""
        # Connect first
        payload = {
            "venue": "BYBIT",
            "api_key": "bybit_safe_key_99887766",
            "api_secret": "bybit_safe_secret",
            "is_testnet": True,
            "permissions": {"enableWithdrawals": False}
        }
        await self.client.post("/api/brokers/connect", json=payload)

        # Disconnect
        disc_resp = await self.client.post("/api/brokers/disconnect", json={"venue": "BYBIT"})
        self.assertEqual(disc_resp.status, 200)
        data = await disc_resp.json()
        self.assertEqual(data["status"], "DISCONNECTED")
        self.assertEqual(data["venue"], "BYBIT")

        # Verify default Paper Sandbox cannot be disconnected
        paper_disc = await self.client.post("/api/brokers/disconnect", json={"venue": "PAPER"})
        self.assertEqual(paper_disc.status, 400)
