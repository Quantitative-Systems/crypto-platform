"""STRATA — Formal Strategy Specification Schema for Strategy Lab.

Defines the structured, machine-verifiable specification produced when natural language
descriptions are parsed and compiled in the Strategy Lab.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StrategyDomain(str, Enum):
    DOMAIN_A_KING = "DOMAIN_A_KING"
    DOMAIN_B_BUILT_IN = "DOMAIN_B_BUILT_IN"
    DOMAIN_C_USER = "DOMAIN_C_USER"


@dataclass
class ExecutionAssumptions:
    slippage_bps: float = 5.0
    maker_fee_bps: float = 2.0
    taker_fee_bps: float = 5.0
    latency_ms: float = 100.0
    fill_model: str = "CONSERVATIVE_NEXT_BAR_OPEN"


@dataclass
class StrategySpecification:
    strategy_id: str
    name: str
    description: str
    domain: StrategyDomain
    assets: List[str]  # Must be approved crypto assets (e.g. ["BTCUSDT", "ETHUSDT"])
    timeframes: List[str]  # e.g. ["1d", "4h", "15m"]
    market_conditions: List[str]  # e.g. ["BULLISH_TREND", "VOLATILITY_EXPANSION"]
    structure: str  # e.g. "HIGHER_HIGHS_HIGHER_LOWS"
    entry_rule: str  # e.g. "DISCOUNT_PULLBACK_CHOCH_CONFIRMATION"
    stop_rule: str  # e.g. "BELOW_SWING_LOW"
    target_rule: str  # e.g. "MINIMUM_4R_TARGET_OR_PREVIOUS_HIGH"
    risk_rule: str  # e.g. "MAX_1_PCT_TRADE_RISK"
    filters: List[str] = field(default_factory=list)
    exit_rule: str = "TARGET_OR_STOP"
    management_rule: str = "BREAK_EVEN_AT_2R"
    execution_assumptions: ExecutionAssumptions = field(default_factory=ExecutionAssumptions)
    tenant_id: str = "system"
    created_at_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["domain"] = self.domain.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StrategySpecification:
        ea = ExecutionAssumptions(**data.get("execution_assumptions", {}))
        return cls(
            strategy_id=data["strategy_id"],
            name=data["name"],
            description=data["description"],
            domain=StrategyDomain(data["domain"]),
            assets=data["assets"],
            timeframes=data["timeframes"],
            market_conditions=data.get("market_conditions", []),
            structure=data.get("structure", ""),
            entry_rule=data.get("entry_rule", ""),
            stop_rule=data.get("stop_rule", ""),
            target_rule=data.get("target_rule", ""),
            risk_rule=data.get("risk_rule", ""),
            filters=data.get("filters", []),
            exit_rule=data.get("exit_rule", "TARGET_OR_STOP"),
            management_rule=data.get("management_rule", "BREAK_EVEN_AT_2R"),
            execution_assumptions=ea,
            tenant_id=data.get("tenant_id", "system"),
            created_at_utc=data.get("created_at_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        )
