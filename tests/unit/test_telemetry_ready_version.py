"""STRATA — Telemetry, Readiness and Versioning API Unit Tests."""

import unittest
from unittest.mock import MagicMock
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web

from web.server import StrataInstitutionalWebServer
from execution.king.king_engine_contract import EXPECTED_KING_CONTRACT_HASH


class TestTelemetryReadyVersionAPI(AioHTTPTestCase):

    async def get_application(self):
        self.mock_supervisor = MagicMock()
        self.mock_supervisor.running = True
        self.mock_supervisor.watchdog = None
        self.mock_supervisor.reconciliation_engine.last_report = None
        self.mock_supervisor.get_system_telemetry.return_value = {
            "uptime_seconds": 3600,
            "connected_venues": ["BINANCE"],
            "active_positions_count": 0,
        }
        self.mock_supervisor.active_positions = {}
        self.mock_supervisor.closed_positions = []
        self.mock_supervisor.orders_history = []
        self.mock_supervisor.decisions_history = []
        
        server = StrataInstitutionalWebServer(supervisor=self.mock_supervisor, port=8899)
        return server.app

    @unittest_run_loop
    async def test_api_ready_endpoint(self):
        resp = await self.client.get("/api/ready")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "READY")
        self.assertTrue(data["supervisor_running"])
        self.assertTrue(data["reconciliation_intact"])

    @unittest_run_loop
    async def test_api_version_endpoint(self):
        resp = await self.client.get("/api/version")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["platform"], "STRATA Digital Trading Platform")
        self.assertEqual(data["king_contract_hash"], EXPECTED_KING_CONTRACT_HASH)
        self.assertEqual(data["contract_status"], "VERIFIED_IMMUTABLE")
        self.assertEqual(data["real_capital_authorized_usd"], 0.0)

    @unittest_run_loop
    async def test_api_telemetry_endpoint(self):
        resp = await self.client.get("/api/telemetry")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["uptime_seconds"], 3600)


if __name__ == "__main__":
    unittest.main()
