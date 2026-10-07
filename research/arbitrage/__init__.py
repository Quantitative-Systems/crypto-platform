"""Arbitrage Research Domain.

Isolated research family for non-directional trading:
- Spot / Perpetual Basis Arbitrage (Cash-and-Carry)
- Funding Rate Harvesting
- Cross-Exchange Spread Arbitrage

Kept strictly separated from directional Market Model research.
"""
from __future__ import annotations

DOMAIN_NAME = "ARBITRAGE"
