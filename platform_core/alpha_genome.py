"""
QCP Universal Alpha Genome & Representation Contract.
Standardized, machine-readable specification for any alpha candidate across all venues,
instruments, asset classes, and time horizons.
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class AlphaFamily(str, enum.Enum):
    DIRECTIONAL = "DIRECTIONAL"
    RELATIVE_VALUE = "RELATIVE_VALUE"
    CARRY = "CARRY"
    ARBITRAGE = "ARBITRAGE"
    MARKET_MAKING = "MARKET_MAKING"
    MICROSTRUCTURE = "MICROSTRUCTURE"
    MACHINE_LEARNING = "MACHINE_LEARNING"
    EVENT_DRIVEN = "EVENT_DRIVEN"


class AlphaLifecycleState(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    RESEARCH = "RESEARCH"
    DEV = "DEV"
    AUDITED = "AUDITED"
    BACKTESTED = "BACKTESTED"
    OOS = "OOS"
    ROBUST = "ROBUST"
    INDEPENDENT = "INDEPENDENT"
    PAPER = "PAPER"
    FORWARD_VALIDATION = "FORWARD_VALIDATION"
    QUALIFIED = "QUALIFIED"
    CONTROLLED_CAPITAL = "CONTROLLED_CAPITAL"
    PRODUCTION = "PRODUCTION"
    DEGRADED = "DEGRADED"
    THROTTLED = "THROTTLED"
    QUARANTINED = "QUARANTINED"
    GRAVEYARD = "GRAVEYARD"


@dataclass
class MicrostructureProfile:
    spread_cost_bps: float = 2.0
    slippage_cost_bps: float = 3.0
    taker_fee_bps: float = 5.0
    maker_fee_bps: float = 2.0
    borrow_rate_apr: float = 6.0
    market_impact_parameter: float = 0.15  # Kyle/Almgren lambda
    latency_sensitivity_half_life_min: float = 120.0
    capacity_usd_ceiling: float = 1_000_000.0


@dataclass
class EconomicPerformance:
    gross_edge_r: float = 0.0
    net_edge_r: float = 0.0
    uncertainty_se: float = 0.0
    trade_count: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_r: float = 0.0
    annualized_sharpe: float = 0.0
    calmar_ratio: float = 0.0
    hurdle_rate_r: float = 0.20


@dataclass
class AlphaGenome:
    alpha_id: str
    family: AlphaFamily
    version: str
    asset_universe: List[str]
    venues: List[str]
    instruments: List[str]  # e.g., ["SPOT", "PERPETUAL"]
    timeframe: str          # e.g., "4h", "1h", "15m", "1m"
    expected_holding_period_hours: float
    economic_rationale: str
    features: List[str]
    entry_mechanism: str
    exit_mechanism: str
    microstructure: MicrostructureProfile = field(default_factory=MicrostructureProfile)
    performance: EconomicPerformance = field(default_factory=EconomicPerformance)
    regime_dependencies: Dict[str, float] = field(default_factory=dict)
    factor_exposures: Dict[str, float] = field(default_factory=dict)
    downside_correlation: Dict[str, float] = field(default_factory=dict)
    failure_modes: List[str] = field(default_factory=list)
    lifecycle_state: AlphaLifecycleState = AlphaLifecycleState.DISCOVERED
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence_hash: str = ""

    def compute_evidence_hash(self) -> str:
        """Computes deterministic SHA-256 fingerprint of the alpha genome specification."""
        payload = {
            "alpha_id": self.alpha_id,
            "family": self.family.value,
            "version": self.version,
            "asset_universe": sorted(self.asset_universe),
            "venues": sorted(self.venues),
            "instruments": sorted(self.instruments),
            "timeframe": self.timeframe,
            "economic_rationale": self.economic_rationale,
            "features": sorted(self.features),
            "entry_mechanism": self.entry_mechanism,
            "exit_mechanism": self.exit_mechanism,
            "performance": asdict(self.performance),
            "microstructure": asdict(self.microstructure),
        }
        raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.evidence_hash = hashlib.sha256(raw_bytes).hexdigest()
        return self.evidence_hash

    def to_dict(self) -> Dict[str, Any]:
        if not self.evidence_hash:
            self.compute_evidence_hash()
        d = asdict(self)
        d["family"] = self.family.value
        d["lifecycle_state"] = self.lifecycle_state.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AlphaGenome:
        family = AlphaFamily(data.get("family", "DIRECTIONAL"))
        state = AlphaLifecycleState(data.get("lifecycle_state", "DISCOVERED"))
        micro = MicrostructureProfile(**data.get("microstructure", {}))
        perf = EconomicPerformance(**data.get("performance", {}))
        return cls(
            alpha_id=data["alpha_id"],
            family=family,
            version=data.get("version", "v1.0"),
            asset_universe=data.get("asset_universe", []),
            venues=data.get("venues", []),
            instruments=data.get("instruments", []),
            timeframe=data.get("timeframe", "4h"),
            expected_holding_period_hours=float(data.get("expected_holding_period_hours", 24.0)),
            economic_rationale=data.get("economic_rationale", ""),
            features=data.get("features", []),
            entry_mechanism=data.get("entry_mechanism", ""),
            exit_mechanism=data.get("exit_mechanism", ""),
            microstructure=micro,
            performance=perf,
            regime_dependencies=data.get("regime_dependencies", {}),
            factor_exposures=data.get("factor_exposures", {}),
            downside_correlation=data.get("downside_correlation", {}),
            failure_modes=data.get("failure_modes", []),
            lifecycle_state=state,
            created_at_utc=data.get("created_at_utc", datetime.now(timezone.utc).isoformat()),
            last_updated_utc=data.get("last_updated_utc", datetime.now(timezone.utc).isoformat()),
            evidence_hash=data.get("evidence_hash", ""),
        )
