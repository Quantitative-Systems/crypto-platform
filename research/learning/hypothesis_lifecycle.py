"""Hypothesis Lifecycle & Autonomous Learning Loop.

Implements institutional relationship learning without compromising the frozen core:
    OBSERVE
       ↓
    DETECT
       ↓
    FORM HYPOTHESIS (e.g., H-CONT-001)
       ↓
    REGISTER HYPOTHESIS
       ↓
    WALK-FORWARD & OOS VALIDATION
       ↓
    ROBUSTNESS & STRESS
       ↓
    SHADOW REPLAY
       ↓
    PAPER LIVE
       ↓
    CAPITAL PROMOTION (RESEARCH_ACTIVE -> PAPER_ELIGIBLE -> MICRO_LIVE -> LIVE)

Hypothesis Lifecycle States:
    CANDIDATE ──► TESTING ──► ACTIVE ──► DEGRADED ──► SUSPENDED

Capital Separation Tiers:
    RESEARCH_ACTIVE    (0.0% capital, research/shadow observation only)
           ↓
    PAPER_ELIGIBLE     (0.0% capital, real-venue API paper trading soak)
           ↓
    MICRO_LIVE_ELIGIBLE (0.1% max capital, real microstructure validation)
           ↓
    LIVE_ELIGIBLE      (1.0% max capital, full institutional risk budget)

CRITICAL ARCHITECTURAL LAW:
A trading loss NEVER triggers automatic live parameter adjustments.
The learning loop tests hypotheses chronologically through versioned,
statistically governed releases, preserving scientific integrity.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class HypothesisStatus(str, Enum):
    """Lifecycle stages for learned market relationships."""
    CANDIDATE = "CANDIDATE"      # Newly proposed by Intelligence Brain
    TESTING = "TESTING"          # Undergoing chronological OOS validation
    ACTIVE = "ACTIVE"            # Certified in OOS & robustness, active in research engine
    DEGRADED = "DEGRADED"        # Performance decaying below threshold, scaled down
    SUSPENDED = "SUSPENDED"      # Invalidation confirmed, retired from engine


class CapitalEligibilityTier(str, Enum):
    """Capital authorization tier for learned hypotheses."""
    RESEARCH_ACTIVE = "RESEARCH_ACTIVE"          # 0.0% capital (Research / Shadow soak only)
    PAPER_ELIGIBLE = "PAPER_ELIGIBLE"            # 0.0% capital (Real venue sandbox / paper live)
    MICRO_LIVE_ELIGIBLE = "MICRO_LIVE_ELIGIBLE"  # 0.1% max risk (Micro-Live capital testing)
    LIVE_ELIGIBLE = "LIVE_ELIGIBLE"              # 1.0% max risk (Scaled institutional capital)


@dataclass
class SystemicHypothesis:
    """A structured, testable hypothesis linking market context to edge."""
    hypothesis_id: str
    title: str
    description: str
    market_model_phase: str          # "PULLBACK" or "CONTINUATION"
    causal_conditions: Dict[str, Any]
    status: HypothesisStatus = HypothesisStatus.CANDIDATE
    capital_tier: CapitalEligibilityTier = CapitalEligibilityTier.RESEARCH_ACTIVE
    sample_size: int = 0
    win_rate: float = 0.0
    expectancy_r: float = 0.0
    stability_score: float = 1.0     # 0.0 to 1.0
    created_at: float = field(default_factory=time.time)
    last_evaluated_at: float = field(default_factory=time.time)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "title": self.title,
            "description": self.description,
            "market_model_phase": self.market_model_phase,
            "causal_conditions": self.causal_conditions,
            "status": self.status.value,
            "capital_tier": self.capital_tier.value,
            "sample_size": self.sample_size,
            "win_rate": round(self.win_rate, 4),
            "expectancy_r": round(self.expectancy_r, 3),
            "stability_score": round(self.stability_score, 3),
            "created_at": self.created_at,
            "last_evaluated_at": self.last_evaluated_at,
            "notes": self.notes,
        }


class AutonomousHypothesisRegistry:
    """Central repository managing the lifecycle and capital tiers of learned relationships."""

    def __init__(self, registry_file: Optional[Path] = None):
        self.registry_file = registry_file
        self.hypotheses: Dict[str, SystemicHypothesis] = {}
        self._initialize_canonical_hypotheses()

    def _initialize_canonical_hypotheses(self) -> None:
        """Register initial research-validated hypotheses from Phases A-M."""
        h1 = SystemicHypothesis(
            hypothesis_id="H-CONT-001",
            title="Bullish Continuation with Negative Funding & Stable Liquidity",
            description="When HTF is Bullish Continuation, negative perpetual funding rates indicate short-squeeze asymmetry, improving continuation edge.",
            market_model_phase="CONTINUATION",
            causal_conditions={"funding_rate": "NEGATIVE", "liquidity": "STABLE", "htf_bias": "BULLISH"},
            status=HypothesisStatus.ACTIVE,
            capital_tier=CapitalEligibilityTier.RESEARCH_ACTIVE,
            sample_size=68,
            win_rate=0.441,
            expectancy_r=0.499,
            stability_score=0.92,
        )
        h2 = SystemicHypothesis(
            hypothesis_id="H-PULL-002",
            title="Macro Event Proximity Destabilizes Pullback Order Blocks",
            description="Pullbacks into MTF key zones within 2 hours of high-impact macro releases suffer elevated slippage and false breakouts.",
            market_model_phase="PULLBACK",
            causal_conditions={"event_window": "ACTIVE_FREEZE", "volatility": "ELEVATED"},
            status=HypothesisStatus.ACTIVE,
            capital_tier=CapitalEligibilityTier.RESEARCH_ACTIVE,
            sample_size=42,
            win_rate=0.214,
            expectancy_r=-0.380,
            stability_score=0.88,
        )
        self.hypotheses[h1.hypothesis_id] = h1
        self.hypotheses[h2.hypothesis_id] = h2

    def register(self, hypothesis: SystemicHypothesis) -> str:
        """Register a new hypothesis candidate."""
        self.hypotheses[hypothesis.hypothesis_id] = hypothesis
        return hypothesis.hypothesis_id

    def update_lifecycle(
        self,
        hypothesis_id: str,
        recent_r_multiples: List[float],
        now: Optional[float] = None,
    ) -> HypothesisStatus:
        """Evaluate recent trade results and manage lifecycle transitions."""
        hyp = self.hypotheses.get(hypothesis_id)
        if not hyp:
            raise KeyError(f"Hypothesis {hypothesis_id} not registered")

        eval_time = now if now is not None else time.time()
        hyp.last_evaluated_at = eval_time

        if not recent_r_multiples:
            return hyp.status

        n = len(recent_r_multiples)
        wins = sum(1 for r in recent_r_multiples if r > 0)
        win_rate = wins / n
        avg_r = sum(recent_r_multiples) / n

        hyp.sample_size += n
        # Exponentially update metrics
        hyp.win_rate = 0.7 * hyp.win_rate + 0.3 * win_rate
        hyp.expectancy_r = 0.7 * hyp.expectancy_r + 0.3 * avg_r

        # Lifecycle state transitions
        if hyp.status == HypothesisStatus.TESTING:
            if hyp.sample_size >= 30 and hyp.expectancy_r > 0.20:
                hyp.status = HypothesisStatus.ACTIVE
                hyp.capital_tier = CapitalEligibilityTier.RESEARCH_ACTIVE
                hyp.notes.append(f"Promoted to ACTIVE (RESEARCH_ACTIVE) at sample {hyp.sample_size} with ExpR={hyp.expectancy_r:+.2f}")
            elif hyp.sample_size >= 30 and hyp.expectancy_r <= 0.0:
                hyp.status = HypothesisStatus.SUSPENDED
                hyp.notes.append(f"Suspended from TESTING due to non-positive ExpR={hyp.expectancy_r:+.2f}")

        elif hyp.status == HypothesisStatus.ACTIVE:
            if avg_r < -0.10:  # Recent performance decaying
                hyp.status = HypothesisStatus.DEGRADED
                hyp.stability_score *= 0.8
                hyp.notes.append(f"Demoted to DEGRADED due to recent drag (AvgR={avg_r:+.2f})")

        elif hyp.status == HypothesisStatus.DEGRADED:
            if avg_r > 0.20:  # Recovering
                hyp.status = HypothesisStatus.ACTIVE
                hyp.stability_score = min(1.0, hyp.stability_score * 1.2)
                hyp.notes.append(f"Restored to ACTIVE after recovery (AvgR={avg_r:+.2f})")
            elif hyp.sample_size >= 50 and hyp.expectancy_r < 0.0:
                hyp.status = HypothesisStatus.SUSPENDED
                hyp.notes.append(f"Permanently SUSPENDED due to persistent decay")

        return hyp.status

    def promote_capital_tier(self, hypothesis_id: str, new_tier: CapitalEligibilityTier, reason: str) -> None:
        """Explicitly promote a hypothesis to a higher capital authorization tier."""
        hyp = self.hypotheses.get(hypothesis_id)
        if not hyp:
            raise KeyError(f"Hypothesis {hypothesis_id} not registered")
        if hyp.status != HypothesisStatus.ACTIVE:
            raise ValueError(f"Cannot promote capital tier for non-ACTIVE hypothesis (current status: {hyp.status.value})")
        hyp.capital_tier = new_tier
        hyp.notes.append(f"Capital Tier promoted to {new_tier.value}: {reason}")

    def get_active_hypotheses(self) -> List[SystemicHypothesis]:
        """Return all certified active hypotheses."""
        return [h for h in self.hypotheses.values() if h.status == HypothesisStatus.ACTIVE]
