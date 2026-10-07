"""Live Decision Ledger.

Logs and audits every cycle's decision (both TRADE and NO_TRADE):
- Immutable JSON event recording
- Human-readable cards
- Blocker and attribution aggregations
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from execution.decision.decision_engine import AutonomousDecisionOutcome, NoTradeReason


class LiveDecisionLedger:
    """Institutional decision ledger recording full causal and market model contexts."""

    def __init__(self, ledger_file: Optional[Path] = None):
        self.ledger_file = ledger_file
        self.records: List[AutonomousDecisionOutcome] = []

    def record(self, outcome: AutonomousDecisionOutcome) -> None:
        """Record decision outcome."""
        self.records.append(outcome)

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Aggregate statistics of recorded decisions."""
        total = len(self.records)
        trade_count = sum(1 for r in self.records if r.decision == "TRADE")
        no_trade_count = sum(1 for r in self.records if r.decision == "NO_TRADE")

        reason_counts: Dict[str, int] = {}
        for r in self.records:
            if r.decision == "NO_TRADE":
                code = r.no_trade_code.value if r.no_trade_code else "UNKNOWN"
                reason_counts[code] = reason_counts.get(code, 0) + 1

        return {
            "total_decisions": total,
            "trade_decisions": trade_count,
            "no_trade_decisions": no_trade_count,
            "trade_rate_pct": round(trade_count / total * 100, 2) if total > 0 else 0.0,
            "top_no_trade_reasons": sorted(reason_counts.items(), key=lambda x: x[1], reverse=True),
        }

    def save_to_file(self) -> None:
        """Persist decision history to JSON on disk."""
        if not self.ledger_file:
            return
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        payload = [r.to_dict() for r in self.records]
        with open(self.ledger_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
