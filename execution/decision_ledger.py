"""Decision Ledger: Auditable Quantitative Decision & Explanation Logging.

Provides an immutable, institutional-grade explanation ledger for every single trade
and NO-TRADE decision, detailing technical structure, macro drivers, positioning,
event proximity, target geometry, and risk allocations.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class DecisionType(str, Enum):
    TRADE = "TRADE"
    NO_TRADE = "NO_TRADE"


@dataclass
class DecisionRecord:
    """Complete audit record for a trading decision at timestamp t."""
    decision_id: str
    timestamp_ms: int
    symbol: str
    timeframe_set: str
    decision: DecisionType
    direction: Optional[str] = None       # "LONG", "SHORT", or None
    htf_context: str = ""
    mtf_context: str = ""
    ltf_context: str = ""
    macro_context: str = ""
    liquidity_context: str = ""
    positioning_context: str = ""
    event_risk_context: str = ""
    htf_destination_r: float = 0.0
    expected_edge_r: float = 0.0
    risk_allocated_pct: float = 0.0        # Max 1.0%
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    primary_reason: str = ""
    blockers: List[str] = field(default_factory=list)
    recorded_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "timestamp_ms": self.timestamp_ms,
            "symbol": self.symbol,
            "timeframe_set": self.timeframe_set,
            "decision": self.decision.value,
            "direction": self.direction,
            "htf_context": self.htf_context,
            "mtf_context": self.mtf_context,
            "ltf_context": self.ltf_context,
            "macro_context": self.macro_context,
            "liquidity_context": self.liquidity_context,
            "positioning_context": self.positioning_context,
            "event_risk_context": self.event_risk_context,
            "htf_destination_r": self.htf_destination_r,
            "expected_edge_r": self.expected_edge_r,
            "risk_allocated_pct": self.risk_allocated_pct,
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
            "target_price": self.target_price,
            "primary_reason": self.primary_reason,
            "blockers": self.blockers,
            "recorded_at_utc": self.recorded_at_utc,
            "meta": self.meta,
        }

    def format_human_card(self) -> str:
        """Produce clean, readable institutional audit text."""
        lines = [
            f"=== DECISION {self.decision_id} | {self.symbol} ({self.timeframe_set}) ===",
            f"DECISION: {self.decision.value}" + (f" ({self.direction})" if self.direction else " (FLAT)"),
            f"PRIMARY REASON: {self.primary_reason}",
        ]
        if self.decision == DecisionType.TRADE:
            lines.extend([
                f"HTF: {self.htf_context}",
                f"MTF: {self.mtf_context}",
                f"LTF: {self.ltf_context}",
                f"Macro: {self.macro_context}",
                f"Liquidity: {self.liquidity_context}",
                f"Positioning: {self.positioning_context}",
                f"Event Risk: {self.event_risk_context}",
                f"HTF Destination: {self.htf_destination_r:.2f}R",
                f"Expected Edge: {self.expected_edge_r:+.2f}R",
                f"Risk: {self.risk_allocated_pct:.2f}%",
                f"Entry: {self.entry_price} | SL: {self.stop_price} | TP: {self.target_price}",
            ])
        else:
            lines.append("BLOCKERS:")
            for b in self.blockers:
                lines.append(f"  - {b}")
            lines.extend([
                f"HTF State: {self.htf_context}",
                f"MTF State: {self.mtf_context}",
                f"Event Context: {self.event_risk_context}",
            ])
        lines.append("=" * 55)
        return "\n".join(lines)


class DecisionLedger:
    """Central repository and auditor for trading and no-trade decision logs."""

    def __init__(self, ledger_file: Optional[Path] = None):
        self.ledger_file = ledger_file
        self.records: List[DecisionRecord] = []
        self._counter = 1000

    def record_decision(
        self,
        timestamp_ms: int,
        symbol: str,
        timeframe_set: str,
        decision: DecisionType,
        primary_reason: str,
        direction: Optional[str] = None,
        htf_context: str = "",
        mtf_context: str = "",
        ltf_context: str = "",
        macro_context: str = "",
        liquidity_context: str = "",
        positioning_context: str = "",
        event_risk_context: str = "",
        htf_destination_r: float = 0.0,
        expected_edge_r: float = 0.0,
        risk_allocated_pct: float = 0.0,
        entry_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        target_price: Optional[float] = None,
        blockers: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> DecisionRecord:
        """Create and store an audit decision record."""
        self._counter += 1
        decision_id = f"DEC-{self._counter:05d}"
        
        record = DecisionRecord(
            decision_id=decision_id,
            timestamp_ms=timestamp_ms,
            symbol=symbol,
            timeframe_set=timeframe_set,
            decision=decision,
            direction=direction,
            htf_context=htf_context,
            mtf_context=mtf_context,
            ltf_context=ltf_context,
            macro_context=macro_context,
            liquidity_context=liquidity_context,
            positioning_context=positioning_context,
            event_risk_context=event_risk_context,
            htf_destination_r=htf_destination_r,
            expected_edge_r=expected_edge_r,
            risk_allocated_pct=risk_allocated_pct,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            primary_reason=primary_reason,
            blockers=blockers or [],
            meta=meta or {},
        )
        self.records.append(record)
        return record

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Aggregate decision counts and top gating blockers."""
        trade_count = sum(1 for r in self.records if r.decision == DecisionType.TRADE)
        no_trade_count = sum(1 for r in self.records if r.decision == DecisionType.NO_TRADE)
        
        blocker_counts: Dict[str, int] = {}
        for r in self.records:
            for b in r.blockers:
                blocker_counts[b] = blocker_counts.get(b, 0) + 1

        return {
            "total_decisions": len(self.records),
            "trade_decisions": trade_count,
            "no_trade_decisions": no_trade_count,
            "trade_rate_pct": round(trade_count / len(self.records) * 100, 2) if self.records else 0.0,
            "top_blockers": sorted(blocker_counts.items(), key=lambda x: x[1], reverse=True),
        }

    def save_to_file(self) -> None:
        """Persist full decision ledger to disk."""
        if not self.ledger_file:
            return
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        payload = [r.to_dict() for r in self.records]
        with open(self.ledger_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
