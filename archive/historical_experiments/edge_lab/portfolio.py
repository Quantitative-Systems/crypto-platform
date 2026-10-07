"""Production portfolio: trade ONLY promotable streams, paper-only, kill-switches.

- Universe: streams passing promotion.evaluate (paper observation).
- Sizing: 0.25% risk per stream (quarter of 1% research risk) with
  portfolio cap: max 3 concurrent positions, max 1% portfolio heat.
- Kill-switches: daily loss -3R halts; per-stream 6R drawdown retires stream;
  weekly review required (ledger timestamp).
- Live capital: $0.00. This module SIMULATES paper fills only; order
  submission remains DISABLED by governance.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class PaperPortfolio:
    risk_per_stream: float = 0.0025
    max_concurrent: int = 3
    max_heat: float = 0.01
    daily_stop_r: float = -3.0
    stream_dd_retire_r: float = 6.0
    ledger: List[Dict[str, Any]] = field(default_factory=list)
    retired: Dict[str, str] = field(default_factory=dict)

    def eligible(self, stream_key: str, verdicts: Dict[str, str]) -> bool:
        if stream_key in self.retired:
            return False
        return verdicts.get(stream_key) == "PROMOTABLE_PAPER_ONLY"

    def retire(self, stream_key: str, reason: str) -> None:
        self.retired[stream_key] = reason
