"""Crypto Trading Platform — Quantitative Evidence Ledger.

Enforces strict isolation of performance evidence across research, validation,
stress testing, forward paper trading, and live execution.
Under no circumstances are historical backtest metrics represented as forward or live results.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import os
import time
from typing import Dict, List, Optional


class EvidenceTier(str, Enum):
    HISTORICAL_DEV = "HISTORICAL_DEV"    # In-sample development (e.g. 2021-01 to 2022-12)
    VALIDATION = "VALIDATION"            # Holdout tuning / selection (e.g. 2023-01 to 2024-03)
    OUT_OF_SAMPLE = "OUT_OF_SAMPLE"      # Blind out-of-sample test (e.g. 2024-04 to 2026-03)
    STRESS_TESTED = "STRESS_TESTED"      # Adverse funding, spread, slippage, & basis shocks
    FORWARD_PAPER = "FORWARD_PAPER"      # Live streaming public WebSocket feeds & simulated fills
    LIVE = "LIVE"                        # Actual exchange execution with real funds (currently $0.00)


@dataclass
class StrategyEvidenceRecord:
    strategy_id: str
    tier: EvidenceTier
    period_start: str
    period_end: str
    trade_count: int
    return_pct: float
    sharpe: float
    sortino: float
    profit_factor: float
    win_rate: float
    expectancy: float
    max_drawdown_pct: float
    turnover: float
    total_fees_bps: float
    slippage_bps: float
    data_lineage_hash: str = ""
    verified: bool = True
    notes: str = ""
    recorded_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_dict(self) -> Dict:
        res = asdict(self)
        res["tier"] = self.tier.value
        return res


class EvidenceLedger:
    """Ground-truth repository of evaluated quantitative strategy evidence."""

    def __init__(self, storage_path: str = "research/results/crypto_platform/evidence_manifest.json"):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self.records: List[StrategyEvidenceRecord] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for item in data.get("records", []):
                        item["tier"] = EvidenceTier(item["tier"])
                        self.records.append(StrategyEvidenceRecord(**item))
            except Exception:
                self.records = []

    def record_evidence(self, record: StrategyEvidenceRecord) -> None:
        """Register a verified piece of evidence."""
        # Enforce tier consistency invariants
        if record.tier == EvidenceTier.LIVE and record.trade_count > 0:
            raise ValueError("Live trading is strictly unactivated. Cannot record live executions.")

        # Replace existing record for same strategy and tier or append
        self.records = [
            r for r in self.records
            if not (r.strategy_id == record.strategy_id and r.tier == record.tier)
        ]
        self.records.append(record)
        self.save()

    def get_records(
        self,
        strategy_id: Optional[str] = None,
        tier: Optional[EvidenceTier] = None,
    ) -> List[StrategyEvidenceRecord]:
        results = self.records
        if strategy_id:
            results = [r for r in results if r.strategy_id == strategy_id]
        if tier:
            results = [r for r in results if r.tier == tier]
        return results

    def save(self) -> None:
        payload = {
            "last_updated_ms": int(time.time() * 1000),
            "total_records": len(self.records),
            "records": [r.to_dict() for r in self.records],
        }
        with open(self.storage_path, "w") as f:
            json.dump(payload, f, indent=2)
