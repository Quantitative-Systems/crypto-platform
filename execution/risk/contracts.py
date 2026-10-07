"""Risk Defense Contracts & Domain Definitions.

Formalizes the 7-Layer Capital Defense Architecture, the Unknown State Engine,
and multi-tier Drawdown Governance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MarketClarityState(str, Enum):
    """Categorization of market structural and contextual intelligibility."""
    KNOWN_FAVORABLE = "KNOWN_FAVORABLE"     # Aligned structure + supportive context -> Full trade permitted
    KNOWN_UNFAVORABLE = "KNOWN_UNFAVORABLE" # Known chop, counter-trend, toxic wicks -> NO TRADE (FLAT)
    TRANSITION = "TRANSITION"               # Structural inflection, range breakout testing -> REDUCED RISK
    UNKNOWN_UNSTABLE = "UNKNOWN_UNSTABLE"   # Uncharacterized shock, feed anomaly, low confidence -> STRICT FLAT


class DrawdownTier(str, Enum):
    """Tiered drawdown defense states based on peak-to-trough equity decline."""
    NORMAL = "NORMAL"                       # DD < 5.0% -> Full operational capacity
    ELEVATED = "ELEVATED"                   # 5.0% <= DD < 10.0% -> 50% risk haircut across all trades
    SEVERE = "SEVERE"                       # 10.0% <= DD < 15.0% -> 75% risk haircut; min target raised to 5.0R
    CRITICAL_HALT = "CRITICAL_HALT"         # DD >= 15.0% -> Hard trading circuit breaker; capital frozen


class RiskAction(str, Enum):
    TRADE_FULL = "TRADE_FULL"
    TRADE_REDUCED = "TRADE_REDUCED"
    NO_TRADE_FLAT = "NO_TRADE_FLAT"
    CIRCUIT_BREAKER_HALT = "CIRCUIT_BREAKER_HALT"


@dataclass
class DefenseLayerCheck:
    layer_name: str
    passed: bool
    risk_factor: float = 1.0                # Multiplier applied to position risk (0.0 to 1.0)
    target_r_floor: float = 4.0
    reason: str = ""


@dataclass
class SystemRiskVerdict:
    """Master institutional risk ruling for a trade candidate."""
    is_trade_allowed: bool
    risk_action: RiskAction
    approved_risk_pct: float                # Max 1.0% hard ceiling
    destination_r_floor: float             # Minimum R destination floor (>= 4.0R, or >= 5.0R in severe DD)
    clarity_state: MarketClarityState
    drawdown_tier: DrawdownTier
    current_drawdown_pct: float
    active_blockers: List[str] = field(default_factory=list)
    layer_audits: List[DefenseLayerCheck] = field(default_factory=list)
    primary_reason: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_trade_allowed": self.is_trade_allowed,
            "risk_action": self.risk_action.value,
            "approved_risk_pct": self.approved_risk_pct,
            "destination_r_floor": self.destination_r_floor,
            "clarity_state": self.clarity_state.value,
            "drawdown_tier": self.drawdown_tier.value,
            "current_drawdown_pct": self.current_drawdown_pct,
            "active_blockers": self.active_blockers,
            "primary_reason": self.primary_reason,
            "meta": self.meta,
        }


@dataclass
class DefenseEfficiencyMetrics:
    """Quantitative efficiency and trade-off metrics for a defensive layer or governor."""
    layer_id: str
    total_signals_evaluated: int
    approved_trades: int
    rejected_signals: int
    rejection_ratio_pct: float
    true_positive_blocks: int       # Blocked signals that would have been losing trades (R <= 0)
    false_positive_blocks: int      # Blocked signals that would have been winning trades (R > 0)
    true_positive_approvals: int    # Approved signals that resulted in winning trades (R > 0)
    false_negative_approvals: int   # Approved signals that resulted in losing trades (R <= 0)
    block_precision_pct: float      # TP_blocks / (TP_blocks + FP_blocks)
    net_r_realized: float
    net_r_sacrificed: float         # Difference vs Ungoverned Net R
    loss_r_prevented: float         # Absolute losses saved by blocking losing trades
    max_drawdown_pct: float
    mdd_reduction_pct: float
    var_95_r: float
    cvar_95_tail_loss_r: float
    defense_efficiency_ratio: float # mdd_reduction_pct / max(0.01, net_r_sacrificed)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "total_signals_evaluated": self.total_signals_evaluated,
            "approved_trades": self.approved_trades,
            "rejected_signals": self.rejected_signals,
            "rejection_ratio_pct": self.rejection_ratio_pct,
            "true_positive_blocks": self.true_positive_blocks,
            "false_positive_blocks": self.false_positive_blocks,
            "true_positive_approvals": self.true_positive_approvals,
            "false_negative_approvals": self.false_negative_approvals,
            "block_precision_pct": self.block_precision_pct,
            "net_r_realized": self.net_r_realized,
            "net_r_sacrificed": self.net_r_sacrificed,
            "loss_r_prevented": self.loss_r_prevented,
            "max_drawdown_pct": self.max_drawdown_pct,
            "mdd_reduction_pct": self.mdd_reduction_pct,
            "var_95_r": self.var_95_r,
            "cvar_95_tail_loss_r": self.cvar_95_tail_loss_r,
            "defense_efficiency_ratio": self.defense_efficiency_ratio,
            "meta": self.meta,
        }


@dataclass
class HistoricalCrisisEpisode:
    """Real market stress episode specification for historical regime coverage auditing."""
    episode_id: str
    name: str
    start_ts: int
    end_ts: int
    regime_climate: str
    primary_stress: str
    description: str


class ReactivationStage(str, Enum):
    """Deterministic stages for exiting crisis defense and returning to active trading."""
    CRISIS_FLAT = "CRISIS_FLAT"                       # Active disorder or shock; 100% FLAT (0.0x)
    STABILIZATION_PROBE = "STABILIZATION_PROBE"       # Volatility/spreads normalizing; Tier 1 Probe (0.25x)
    STRUCTURAL_TRANSITION = "STRUCTURAL_TRANSITION"   # MTF higher low / zone reclaimed; Tier 2 Confirm (0.50x)
    FULL_RECOVERY_ACTIVE = "FULL_RECOVERY_ACTIVE"     # Multi-TF trend continuation confirmed; Full (1.0x)
    FALSE_RECOVERY_ABORT = "FALSE_RECOVERY_ABORT"     # Bounce fails into new low; Fast abort back to FLAT (0.0x)


@dataclass
class RecoveryConfirmationAudit:
    """Detailed audit of recovery confirmation checks across all 5 dimensions."""
    timestamp_ms: int
    symbol: str
    stage: ReactivationStage
    is_volatility_normalized: bool
    is_liquidity_restored: bool
    is_structure_aligned: bool
    is_cross_market_calm: bool
    is_positioning_safe: bool
    approved_risk_factor: float
    reason: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_ms": self.timestamp_ms,
            "symbol": self.symbol,
            "stage": self.stage.value,
            "is_volatility_normalized": self.is_volatility_normalized,
            "is_liquidity_restored": self.is_liquidity_restored,
            "is_structure_aligned": self.is_structure_aligned,
            "is_cross_market_calm": self.is_cross_market_calm,
            "is_positioning_safe": self.is_positioning_safe,
            "approved_risk_factor": self.approved_risk_factor,
            "reason": self.reason,
            "meta": self.meta,
        }


@dataclass
class ReactivationPolicyComparison:
    """Comparative performance metrics for a reactivation policy across post-crisis periods."""
    policy_id: str
    name: str
    total_recovery_trades: int
    net_r: float
    expectancy_r: float
    win_rate: float
    profit_factor: float
    false_recovery_traps_hit: int
    false_recovery_loss_r: float
    post_crisis_trend_captured_pct: float
    max_drawdown_pct: float
    reactivation_efficiency_ratio: float  # Net R / (1.0 + False Recovery Loss R)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "total_recovery_trades": self.total_recovery_trades,
            "net_r": self.net_r,
            "expectancy_r": self.expectancy_r,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "false_recovery_traps_hit": self.false_recovery_traps_hit,
            "false_recovery_loss_r": self.false_recovery_loss_r,
            "post_crisis_trend_captured_pct": self.post_crisis_trend_captured_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "reactivation_efficiency_ratio": self.reactivation_efficiency_ratio,
            "meta": self.meta,
        }


