"""
Certified Research Universe Inventory.
Audits the physical warehouse kline archives and emits the authoritative
machine-readable inventory required by Directive Point 2.

Only certified data may enter economic research.
All missing external data streams (funding history, L2 depth, tick liquidations)
are explicitly cataloged as BLOCKED_EXTERNAL_DATA.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from market_data.dataset_manifest import DatasetManifestManager


@dataclass
class CertifiedDatasetRecord:
    asset: str
    venue: str
    timeframe: str
    start_timestamp: int
    end_timestamp: int
    start_utc: str
    end_utc: str
    bar_count: int
    granularity_seconds: int
    missingness_count: int
    maximum_gap_bars: int
    source: str
    lineage_hash: str
    quality_status: str
    research_eligibility: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CertifiedResearchUniverseEngine:
    """
    Scans, verifies, and publishes the certified research universe.
    """

    TIMEFRAME_SECONDS = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
        "1w": 604800,
        "1M": 2592000,
    }

    UNAVAILABLE_DATA_STREAMS = [
        {
            "stream_name": "HISTORICAL_FUNDING_RATES",
            "required_for": ["CARRY", "BASIS_ARBITRAGE"],
            "status": "BLOCKED_EXTERNAL_DATA",
            "reason": "Binance historical funding rates archive not stored locally. Simulated approximations prohibited.",
        },
        {
            "stream_name": "L2_ORDER_BOOK_DEPTH",
            "required_for": ["MICROSTRUCTURE", "MARKET_MAKING", "OFI"],
            "status": "BLOCKED_EXTERNAL_DATA",
            "reason": "Historical millisecond L2 depth snapshots not available in local warehouse.",
        },
        {
            "stream_name": "TICK_LIQUIDATION_FLOW",
            "required_for": ["EVENT_DRIVEN", "LIQUIDATION_CASCADE"],
            "status": "BLOCKED_EXTERNAL_DATA",
            "reason": "WebSocket tick liquidation prints not warehoused historically.",
        },
        {
            "stream_name": "CROSS_VENUE_TICK_PRICES",
            "required_for": ["SPATIAL_ARBITRAGE"],
            "status": "BLOCKED_EXTERNAL_DATA",
            "reason": "Simultaneous secondary exchange (Bybit/OKX) tick books not archived.",
        },
    ]

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
        self.cache_dir = self.repo_root / "market_data" / "cache"
        self.output_path = self.repo_root / "research" / "results" / "CERTIFIED_RESEARCH_UNIVERSE.json"

    def audit_and_generate_inventory(self) -> Dict[str, Any]:
        """Audits all cache files and outputs CERTIFIED_RESEARCH_UNIVERSE.json."""
        manifests = DatasetManifestManager.audit_and_save_manifests()
        
        certified_datasets: List[CertifiedDatasetRecord] = []
        for m in manifests:
            gran_sec = self.TIMEFRAME_SECONDS.get(m.timeframe, 0)
            rec = CertifiedDatasetRecord(
                asset=m.symbol,
                venue=m.venue,
                timeframe=m.timeframe,
                start_timestamp=m.start_timestamp_utc,
                end_timestamp=m.end_timestamp_utc,
                start_utc=m.start_date_str,
                end_utc=m.end_date_str,
                bar_count=m.row_count,
                granularity_seconds=gran_sec,
                missingness_count=m.missing_intervals,
                maximum_gap_bars=m.maximum_gap_bars,
                source=m.source,
                lineage_hash=m.sha256_checksum,
                quality_status=m.certification_status,
                research_eligibility=m.research_eligibility,
            )
            certified_datasets.append(rec)

        inventory = {
            "inventory_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_certified_datasets": len(certified_datasets),
            "eligible_for_research_count": sum(1 for d in certified_datasets if d.research_eligibility),
            "available_assets": sorted(list({d.asset for d in certified_datasets})),
            "available_timeframes": sorted(list({d.timeframe for d in certified_datasets})),
            "certified_datasets": [d.to_dict() for d in certified_datasets],
            "unavailable_data_streams": self.UNAVAILABLE_DATA_STREAMS,
            "governance_rule": (
                "Only datasets marked research_eligibility=True with verified SHA-256 lineage "
                "may enter research. Unavailable data streams are permanently blocked."
            ),
        }

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w") as f:
            json.dump(inventory, f, indent=2)

        return inventory


if __name__ == "__main__":
    engine = CertifiedResearchUniverseEngine()
    inv = engine.audit_and_generate_inventory()
    print(f"Certified {inv['total_certified_datasets']} datasets across {inv['available_assets']}.")
    print(f"Output saved to {engine.output_path}")
