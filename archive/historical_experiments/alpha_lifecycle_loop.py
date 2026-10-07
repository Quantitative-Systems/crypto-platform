"""
QCP Alpha Lifecycle Manager & Autonomous Replacement Loop.
Automates the lifecycle of all alpha candidates:
- Progression through evidence gates (Discovered -> Research -> Audited -> Paper -> Qualified)
- Continuous monitoring for performance degradation
- Quarantine and Graveyard management
- Autonomous replacement hypothesis triggering
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from platform_core.alpha_genome import AlphaGenome, AlphaLifecycleState
from research.autonomous_research_factory import AutonomousResearchFactory


@dataclass
class LifecycleTransitionEvent:
    alpha_id: str
    from_state: str
    to_state: str
    timestamp_utc: str
    rationale: str


class AlphaLifecycleManager:
    """
    Supervises alpha lifecycles, quaratines failing strategies, and triggers
    autonomous research factory to discover replacements.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path("/home/mrcn2/crypto-platform/research/results")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.graveyard_file = self.storage_dir / "ALPHA_GRAVEYARD_REGISTRY.json"
        self.history_file = self.storage_dir / "LIFECYCLE_TRANSITIONS.json"
        self.events: List[LifecycleTransitionEvent] = []

    def transition_state(
        self,
        genome: AlphaGenome,
        new_state: AlphaLifecycleState,
        rationale: str
    ) -> LifecycleTransitionEvent:
        """Executes a formal lifecycle transition and logs the event."""
        old_state = genome.lifecycle_state
        genome.lifecycle_state = new_state
        genome.last_updated_utc = datetime.now(timezone.utc).isoformat()

        event = LifecycleTransitionEvent(
            alpha_id=genome.alpha_id,
            from_state=old_state.value,
            to_state=new_state.value,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            rationale=rationale
        )
        self.events.append(event)

        # If entering graveyard, record permanent institutional memory
        if new_state == AlphaLifecycleState.GRAVEYARD:
            self._archive_to_graveyard(genome, rationale)

        return event

    def evaluate_degradation_and_replace(
        self,
        genome: AlphaGenome,
        is_degraded: bool,
        diagnosis_reason: str,
        factory: AutonomousResearchFactory,
        hypotheses: Optional[List[Any]] = None
    ) -> Optional[AlphaGenome]:
        """
        If alpha is degraded, demotes it to QUARANTINED or GRAVEYARD and
        autonomously requests the factory to generate a replacement hypothesis.
        """
        if not is_degraded:
            return None

        # Transition degraded alpha
        self.transition_state(
            genome,
            AlphaLifecycleState.QUARANTINED,
            f"Automated degradation detected: {diagnosis_reason}"
        )

        # Trigger Autonomous Research Factory for a replacement
        population = factory.generate_candidate_population(hypotheses or [])
        # Find replacement from same family or unrepresented family
        replacement = None
        for cand in population:
            if cand.alpha_id != genome.alpha_id and cand.family == genome.family:
                replacement = cand
                break

        if not replacement and len(population) > 0:
            replacement = population[0]

        return replacement

    def _archive_to_graveyard(self, genome: AlphaGenome, rationale: str) -> None:
        graveyard = []
        if self.graveyard_file.exists():
            try:
                with open(self.graveyard_file, "r") as f:
                    graveyard = json.load(f)
            except Exception:
                graveyard = []

        entry = {
            "alpha_id": genome.alpha_id,
            "family": genome.family.value,
            "version": genome.version,
            "rationale_for_archival": rationale,
            "archived_at_utc": datetime.now(timezone.utc).isoformat(),
            "evidence_hash": genome.evidence_hash
        }
        graveyard.append(entry)
        with open(self.graveyard_file, "w") as f:
            json.dump(graveyard, f, indent=2)
