"""
Quantitative Crypto Platform (QCP) — Strategy Graveyard.

Permanent immutable repository of all rejected, falsified, and degraded strategies.
Preserves institutional memory to prevent repeated failure modes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class GraveyardEntry:
    strategy_id: str
    family: str
    symbol: str
    timeframe: str
    falsification_stage: str  # DEV, VAL, OOS, FORWARD_PAPER, ADVERSARIAL
    primary_failure_reason: str
    decomposed_drag_analysis: Dict[str, Any]
    economic_post_mortem: str
    date_buried_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StrategyGraveyard:
    """
    Registry preventing resurrection of falsified alpha mechanisms.
    """

    def __init__(self, storage_file: Optional[Path] = None):
        base = Path(__file__).resolve().parent.parent.parent
        self.storage_file = storage_file or base / "research" / "results" / "STRATEGY_GRAVEYARD.json"
        self._entries: Dict[str, GraveyardEntry] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("graveyard", []):
                        entry = GraveyardEntry(**item)
                        self._entries[entry.strategy_id] = entry
            except Exception:
                pass

    def _save(self) -> None:
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump({"graveyard": [e.to_dict() for e in self._entries.values()]}, f, indent=2)

    def bury_strategy(self, entry: GraveyardEntry) -> None:
        self._entries[entry.strategy_id] = entry
        self._save()

    def is_buried(self, strategy_id: str) -> bool:
        return strategy_id in self._entries

    def get_entry(self, strategy_id: str) -> Optional[GraveyardEntry]:
        return self._entries.get(strategy_id)

    def list_buried(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._entries.values()]
