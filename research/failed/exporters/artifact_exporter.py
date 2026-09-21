"""
Product 04 — Research Laboratory: Artifact Exporter
Exports reproducible experiment traces, trade ledgers, and performance summaries
to research/results/ with full metadata provenance (dataset hash, config hash, release tag).
"""

import os
import json
import hashlib
from typing import Dict, Any, List
from datetime import datetime, timezone


class ArtifactExporter:
    """
    Serializes research experiment outputs to JSON and CSV artifacts.
    """

    def __init__(self, output_dir: str = "research/results"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _generate_provenance_hash(self, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def export_run(
        self,
        experiment_name: str,
        asset: str,
        timeframe_set: str,
        hypothesis_id: str,
        metrics: Dict[str, Any],
        exit_attribution: Dict[str, Any],
        failure_modes: Dict[str, Any],
        trades: List[Dict[str, Any]],
        equity_curve: List[Dict[str, Any]],
        config: Dict[str, Any],
        dataset_info: Dict[str, Any]
    ) -> str:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename_base = f"{experiment_name}_{asset}_{timeframe_set}_{hypothesis_id}_{timestamp_str}"
        
        full_provenance = {
            "experiment_name": experiment_name,
            "asset": asset,
            "timeframe_set": timeframe_set,
            "hypothesis_id": hypothesis_id,
            "release_version": "v0.4.0-product-04",
            "execution_model_version": "1.0.0-causal-adverse-first",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config": config,
            "dataset_info": dataset_info
        }

        provenance_hash = self._generate_provenance_hash(full_provenance)
        full_provenance["provenance_hash"] = provenance_hash

        artifact_payload = {
            "provenance": full_provenance,
            "metrics": metrics,
            "exit_attribution": exit_attribution,
            "failure_modes": failure_modes,
            "trades_summary": {
                "total_trades": len(trades),
                "trades": trades
            },
            "equity_curve": equity_curve
        }

        json_path = os.path.join(self.output_dir, f"{filename_base}_{provenance_hash}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(artifact_payload, f, indent=2, default=str)

        return json_path
