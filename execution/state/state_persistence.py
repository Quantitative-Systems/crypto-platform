"""STRATA Digital Trading Platform — State Checkpointing & Restart Recovery.

Ensures continuous 24/7/365 resilience by maintaining deterministic state checkpoints:
- Active open positions & order intents
- Simulated account equity and PnL metrics
- Processed candle timestamps
- Circuit breaker trip states

On platform restart:
- Reads the last valid checkpoint
- Verifies integrity checksum
- Restores internal position state
- Triggers reconciliation against broker before enabling order submission
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_STATE_DIR = Path(__file__).resolve().parent.parent.parent / "research" / "results" / "state"


class StatePersistenceManager:
    """Manages atomic state serialization and restart recovery."""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or DEFAULT_STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.state_dir / "platform_checkpoint.json"

    def save_checkpoint(
        self,
        equity_usd: float,
        peak_equity_usd: float,
        active_positions: List[Dict[str, Any]],
        closed_trades_count: int,
        metrics: Dict[str, Any],
        candle_sync_timestamps: Dict[str, int],
        circuit_breakers_state: Dict[str, Any],
    ) -> bool:
        """Atomically save platform state to disk with SHA-256 checksum."""
        try:
            payload = {
                "timestamp_ms": int(time.time() * 1000),
                "equity_usd": round(equity_usd, 2),
                "peak_equity_usd": round(peak_equity_usd, 2),
                "active_positions": active_positions,
                "closed_trades_count": closed_trades_count,
                "metrics": metrics,
                "candle_sync_timestamps": candle_sync_timestamps,
                "circuit_breakers_state": circuit_breakers_state,
            }
            raw_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            checksum = hashlib.sha256(raw_bytes).hexdigest()

            envelope = {
                "checksum_sha256": checksum,
                "data": payload,
            }

            temp_file = self.state_dir / f"checkpoint_temp_{os.getpid()}.json"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(envelope, f, indent=2)

            # Atomic rename
            temp_file.replace(self.checkpoint_file)
            logger.debug(f"Platform checkpoint saved successfully. Hash: {checksum[:8]}")
            return True
        except Exception as e:
            logger.error(f"Failed to save platform checkpoint: {e}", exc_info=True)
            return False

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load and verify platform checkpoint from disk."""
        if not self.checkpoint_file.exists():
            logger.info("No existing checkpoint found. Starting with pristine state.")
            return None

        try:
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                envelope = json.load(f)

            stored_checksum = envelope.get("checksum_sha256")
            data = envelope.get("data", {})
            raw_bytes = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
            calculated_checksum = hashlib.sha256(raw_bytes).hexdigest()

            if stored_checksum != calculated_checksum:
                logger.critical(
                    f"CHECKPOINT CORRUPTION DETECTED: Stored hash {stored_checksum} != "
                    f"Calculated hash {calculated_checksum}. Rejecting checkpoint."
                )
                return None

            logger.info(
                f"RESTART RECOVERY: Loaded checkpoint from {data.get('timestamp_ms')} "
                f"with {len(data.get('active_positions', []))} active positions. Checksum verified."
            )
            return data
        except Exception as e:
            logger.error(f"Failed to load platform checkpoint: {e}", exc_info=True)
            return None
