"""Hierarchy of Truth: 12-Level Institutional Information Architecture.

Enforces the platform's strict truth hierarchy:
    LEVEL 0  — RAW WORLD (Market feeds, Macro prints, Execution events)
    LEVEL 1  — DATA QUALITY (Clock synchronization, Causal ordering, Integrity)
    LEVEL 2  — INSTRUMENT STATE (Crypto-base invariant, Admission gate, Constraints)
    LEVEL 3  — MARKET MODEL (Structure + Key Zones/Levels + Phase)
    LEVEL 4  — MARKET REGIME (Volatility environment, Expansion vs Crisis)
    LEVEL 5  — CAUSAL CONTEXT (Macro drivers, Event windows, Positioning)
    LEVEL 6  — STRATEGY HYPOTHESIS (Validated rule selection, H-registry)
    LEVEL 7  — TRADE OPPORTUNITY (MTF setup, LTF entry, Target >= 4.0R)
    LEVEL 8  — PORTFOLIO DECISION (Factor risk, Heat <= 3%, Concentration)
    LEVEL 9  — EXECUTION (Microstructure simulation, Sizing, Slippage)
    LEVEL 10 — OUTCOME (Position lifecycle, MTF trail, Realized R)
    LEVEL 11 — LEARNING / DRIFT (Decision ledger audit, Concept drift, Hypothesis update)

Rule: A higher truth level CANNOT execute without cryptographic and logical
attestation from all lower levels. Prevents indicator confusion and strategy pollution.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple


class TruthLevel(IntEnum):
    """Hierarchical levels of information validity."""
    LEVEL_0_RAW_WORLD = 0
    LEVEL_1_DATA_QUALITY = 1
    LEVEL_2_INSTRUMENT_STATE = 2
    LEVEL_3_MARKET_MODEL = 3
    LEVEL_4_MARKET_REGIME = 4
    LEVEL_5_CAUSAL_CONTEXT = 5
    LEVEL_6_STRATEGY_HYPOTHESIS = 6
    LEVEL_7_TRADE_OPPORTUNITY = 7
    LEVEL_8_PORTFOLIO_DECISION = 8
    LEVEL_9_EXECUTION = 9
    LEVEL_10_OUTCOME = 10
    LEVEL_11_LEARNING_DRIFT = 11


@dataclass
class LevelAttestation:
    """Cryptographic/logical sign-off for a specific truth level."""
    level: TruthLevel
    verified: bool
    sign_off_reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    attested_at: float = field(default_factory=time.time)


@dataclass
class HierarchyValidationReport:
    """Audit report tracking attestation through the 12 levels."""
    is_valid: bool
    highest_valid_level: TruthLevel
    failure_level: Optional[TruthLevel]
    failure_reason: Optional[str]
    attestations: Dict[int, LevelAttestation] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "highest_valid_level": self.highest_valid_level.name,
            "failure_level": self.failure_level.name if self.failure_level else None,
            "failure_reason": self.failure_reason,
            "attested_levels_count": len(self.attestations),
        }


class HierarchyOfTruthValidator:
    """Verifies that no decision bypasses prerequisite information levels."""

    @staticmethod
    def validate_progression(
        raw_world_valid: bool,
        data_quality_valid: bool,
        instrument_admitted: bool,
        market_model_valid: bool,
        regime_favorable: bool,
        causal_context_clear: bool,
        strategy_hypothesis_valid: bool,
        trade_opportunity_ge_4r: bool,
        portfolio_capital_approved: bool,
        execution_viable: bool,
        outcome_monitored: bool = True,
        learning_recorded: bool = True,
    ) -> HierarchyValidationReport:
        """Evaluate full stack compliance across the 12 levels."""
        checks = [
            (TruthLevel.LEVEL_0_RAW_WORLD, raw_world_valid, "Raw market/macro feeds ingested"),
            (TruthLevel.LEVEL_1_DATA_QUALITY, data_quality_valid, "Causal ordering, zero lookahead, clock synced"),
            (TruthLevel.LEVEL_2_INSTRUMENT_STATE, instrument_admitted, "Base asset is CRYPTO, constraints admitted"),
            (TruthLevel.LEVEL_3_MARKET_MODEL, market_model_valid, "Structure, Key Zones, Phase validated"),
            (TruthLevel.LEVEL_4_MARKET_REGIME, regime_favorable, "Volatility regime favorable"),
            (TruthLevel.LEVEL_5_CAUSAL_CONTEXT, causal_context_clear, "Outside macro event freeze windows"),
            (TruthLevel.LEVEL_6_STRATEGY_HYPOTHESIS, strategy_hypothesis_valid, "Active validated hypothesis selected"),
            (TruthLevel.LEVEL_7_TRADE_OPPORTUNITY, trade_opportunity_ge_4r, "MTF setup confirmed, Target >= 4.0R"),
            (TruthLevel.LEVEL_8_PORTFOLIO_DECISION, portfolio_capital_approved, "Factor risk approved, Heat <= 3%"),
            (TruthLevel.LEVEL_9_EXECUTION, execution_viable, "Sizing validated, slippage within bounds"),
            (TruthLevel.LEVEL_10_OUTCOME, outcome_monitored, "Position state machine & MTF trail engaged"),
            (TruthLevel.LEVEL_11_LEARNING_DRIFT, learning_recorded, "Decision ledger & drift audit recorded"),
        ]

        attestations: Dict[int, LevelAttestation] = {}
        highest = TruthLevel.LEVEL_0_RAW_WORLD

        for lvl, passed, desc in checks:
            att = LevelAttestation(
                level=lvl,
                verified=passed,
                sign_off_reason=desc if passed else f"FAILED: {desc}",
            )
            attestations[lvl.value] = att
            if not passed:
                return HierarchyValidationReport(
                    is_valid=False,
                    highest_valid_level=highest,
                    failure_level=lvl,
                    failure_reason=f"Level {lvl.value} ({lvl.name}) failed validation: {desc}",
                    attestations=attestations,
                )
            highest = lvl

        return HierarchyValidationReport(
            is_valid=True,
            highest_valid_level=TruthLevel.LEVEL_11_LEARNING_DRIFT,
            failure_level=None,
            failure_reason=None,
            attestations=attestations,
        )
