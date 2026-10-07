"""Phase L: Independent Robustness & Statistical Stress Validation Contracts.

Defines schemas and data classes for rigorously attacking the frozen candidate:
L1 - Cost Stress (1x to 5x friction degradation)
L2 - Parameter Perturbation (Fragility & Plateau Stability Index)
L3 - Asset Transfer (Leave-one-asset-out cross-validation)
L4 - Timeframe Transfer (Alternate MTF triplet sets)
L5 - Monte Carlo Resampling (Sequence risk, ruin probability, recovery time)
L6 - Crisis Blind Test (Pre-defined unseen crisis & stress episodes)
L7 - Reactivation Isolation Test (Resolving System 2 vs System 3 incremental value)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


@dataclass
class CostStressResult:
    """Evaluation of strategy performance under friction degradation."""
    multiplier: float
    effective_friction_per_trade_r: float
    trade_count: int
    net_r: float
    expectancy_r: float
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    is_positive_expectancy: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "multiplier": self.multiplier,
            "effective_friction_per_trade_r": self.effective_friction_per_trade_r,
            "trade_count": self.trade_count,
            "net_r": self.net_r,
            "expectancy_r": self.expectancy_r,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "max_drawdown_pct": self.max_drawdown_pct,
            "is_positive_expectancy": self.is_positive_expectancy,
        }


@dataclass
class ParameterPerturbationResult:
    """Fragility test around a single frozen system threshold."""
    parameter_name: str
    baseline_value: float
    tested_values: List[float]
    expectancies_r: List[float]
    net_rs: List[float]
    max_drawdowns_pct: List[float]
    plateau_stability_index: float  # PSI: 0.0 (erratic spike) to 1.0 (resilient plateau)
    is_fragile: bool
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "baseline_value": self.baseline_value,
            "tested_values": self.tested_values,
            "expectancies_r": self.expectancies_r,
            "net_rs": self.net_rs,
            "max_drawdowns_pct": self.max_drawdowns_pct,
            "plateau_stability_index": self.plateau_stability_index,
            "is_fragile": self.is_fragile,
            "summary": self.summary,
        }


@dataclass
class AssetTransferResult:
    """Leave-one-asset-out transferability evaluation."""
    trained_on: str
    tested_on: str
    trade_count: int
    net_r: float
    expectancy_r: float
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    is_profitable: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trained_on": self.trained_on,
            "tested_on": self.tested_on,
            "trade_count": self.trade_count,
            "net_r": self.net_r,
            "expectancy_r": self.expectancy_r,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "max_drawdown_pct": self.max_drawdown_pct,
            "is_profitable": self.is_profitable,
        }


@dataclass
class TimeframeTransferResult:
    """Multi-timeframe triplet structural transfer evaluation."""
    set_name: str
    htf: str
    mtf: str
    ltf: str
    trade_count: int
    net_r: float
    expectancy_r: float
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    is_viable: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "set_name": self.set_name,
            "htf": self.htf,
            "mtf": self.mtf,
            "ltf": self.ltf,
            "trade_count": self.trade_count,
            "net_r": self.net_r,
            "expectancy_r": self.expectancy_r,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "max_drawdown_pct": self.max_drawdown_pct,
            "is_viable": self.is_viable,
        }


@dataclass
class MonteCarloResampleResult:
    """Comprehensive trade-sequence resampling statistics."""
    iterations: int
    original_trade_count: int
    original_net_r: float
    p05_net_r: float
    p50_net_r: float
    p95_net_r: float
    original_max_dd_r: float
    p95_max_dd_r: float
    ruin_probability: float  # Prob of Max DD exceeding 25R
    cvar_95_r: float
    longest_losing_streak_p95: int
    avg_recovery_trades: float
    dropout_positive_rate: float  # 20% random dropout positive expectancy rate
    is_resilient: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iterations": self.iterations,
            "original_trade_count": self.original_trade_count,
            "original_net_r": self.original_net_r,
            "p05_net_r": self.p05_net_r,
            "p50_net_r": self.p50_net_r,
            "p95_net_r": self.p95_net_r,
            "original_max_dd_r": self.original_max_dd_r,
            "p95_max_dd_r": self.p95_max_dd_r,
            "ruin_probability": self.ruin_probability,
            "cvar_95_r": self.cvar_95_r,
            "longest_losing_streak_p95": self.longest_losing_streak_p95,
            "avg_recovery_trades": self.avg_recovery_trades,
            "dropout_positive_rate": self.dropout_positive_rate,
            "is_resilient": self.is_resilient,
        }


@dataclass
class CrisisBlindEpisodeResult:
    """Evaluation of risk defense in pre-defined historical crisis windows."""
    episode_id: str
    episode_name: str
    date_range: str
    crisis_type: str
    baseline_trades: int
    baseline_net_r: float
    baseline_max_dd_pct: float
    governed_trades: int
    governed_net_r: float
    governed_max_dd_pct: float
    drawdown_reduction_pct: float
    defense_verdict: str  # PROTECTED, NEUTRAL, EXPOSED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "episode_name": self.episode_name,
            "date_range": self.date_range,
            "crisis_type": self.crisis_type,
            "baseline_trades": self.baseline_trades,
            "baseline_net_r": self.baseline_net_r,
            "baseline_max_dd_pct": self.baseline_max_dd_pct,
            "governed_trades": self.governed_trades,
            "governed_net_r": self.governed_net_r,
            "governed_max_dd_pct": self.governed_max_dd_pct,
            "drawdown_reduction_pct": self.drawdown_reduction_pct,
            "defense_verdict": self.defense_verdict,
        }


@dataclass
class ReactivationIsolationResult:
    """Direct comparison of Static Governor vs Staged Reactivation."""
    episode_id: str
    episode_name: str
    static_governed_trades: int
    static_governed_net_r: float
    static_governed_max_dd_pct: float
    staged_governed_trades: int
    staged_governed_net_r: float
    staged_governed_max_dd_pct: float
    incremental_r_delta: float
    incremental_dd_delta: float
    stages_activated_count: int
    isolation_verdict: str  # INCREMENTAL_VALUE, EQUIVALENT, UNDERPERFORMED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "episode_name": self.episode_name,
            "static_governed_trades": self.static_governed_trades,
            "static_governed_net_r": self.static_governed_net_r,
            "static_governed_max_dd_pct": self.static_governed_max_dd_pct,
            "staged_governed_trades": self.staged_governed_trades,
            "staged_governed_net_r": self.staged_governed_net_r,
            "staged_governed_max_dd_pct": self.staged_governed_max_dd_pct,
            "incremental_r_delta": self.incremental_r_delta,
            "incremental_dd_delta": self.incremental_dd_delta,
            "stages_activated_count": self.stages_activated_count,
            "isolation_verdict": self.isolation_verdict,
        }


@dataclass
class MasterPhaseLReport:
    """Master record of all 7 independent robustness & statistical stress validations."""
    timestamp_utc: str
    phase: str = "PHASE_L_INDEPENDENT_ROBUSTNESS_STRESS"
    cost_stress_breakeven_multiplier: float = 0.0
    parameter_plateau_passed: bool = True
    asset_transfer_pass_rate: float = 0.0
    timeframe_transfer_pass_rate: float = 0.0
    monte_carlo_resilient: bool = True
    crisis_blind_protection_rate: float = 0.0
    reactivation_incremental_finding: str = ""
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "phase": self.phase,
            "cost_stress_breakeven_multiplier": self.cost_stress_breakeven_multiplier,
            "parameter_plateau_passed": self.parameter_plateau_passed,
            "asset_transfer_pass_rate": self.asset_transfer_pass_rate,
            "timeframe_transfer_pass_rate": self.timeframe_transfer_pass_rate,
            "monte_carlo_resilient": self.monte_carlo_resilient,
            "crisis_blind_protection_rate": self.crisis_blind_protection_rate,
            "reactivation_incremental_finding": self.reactivation_incremental_finding,
            "summary": self.summary,
        }
