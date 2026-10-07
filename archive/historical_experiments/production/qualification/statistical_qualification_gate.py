"""
Quantitative Crypto Platform (QCP) — Statistical Qualification Gatekeeper.

Codifies the formal 3-tier lifecycle hierarchy:
1. QUALIFIED_ROBUST: Survived historical multi-year adversarial battery.
2. FORWARD_HEALTHY: Active forward observation showing non-degraded telemetry.
3. PRODUCTION_QUALIFIED: Passed rigorous statistical confidence intervals (min 100 trades,
   min 60 days, 95% bootstrap CI lower bound > +0.15R, DD <= 1.25x historical, friction <= 3 bps).

ENFORCES: Real capital remains strictly locked. SOL Set 2 is explicitly prevented
from being marked PRODUCTION_QUALIFIED until forward statistical hurdles are satisfied.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import json
import logging

logger = logging.getLogger(__name__)


class StrategyLifecycleTier(str, Enum):
    HISTORICAL_ROBUST = "HISTORICAL_ROBUST"
    FORWARD_HEALTHY = "FORWARD_HEALTHY"
    PRODUCTION_QUALIFIED = "PRODUCTION_QUALIFIED"
    DEGRADED_OR_DISQUALIFIED = "DEGRADED_OR_DISQUALIFIED"


@dataclass
class QualificationHurdles:
    min_forward_trades: int = 100
    min_forward_days: float = 60.0
    bootstrap_iterations: int = 2000
    confidence_level_pct: float = 95.0
    min_expectancy_ci_lower_bound_r: float = 0.15   # 95% CI lower bound must exceed +0.15R
    max_forward_drawdown_pct: float = 5.91           # 1.25x historical 4.73% max DD
    max_friction_error_bps: float = 3.0             # Model error limit
    max_consecutive_losses: int = 8
    min_win_rate_pct: float = 55.0


@dataclass
class BootstrapExpectancyResult:
    mean_expectancy_r: float
    ci_lower_bound_r: float
    ci_upper_bound_r: float
    confidence_level_pct: float
    bootstrap_samples: int


@dataclass
class StatisticalAuditVerdict:
    strategy_id: str
    symbol: str
    current_tier: StrategyLifecycleTier
    is_production_qualified: bool
    is_capital_firewall_locked: bool
    live_execution_permitted: bool
    
    # Evidence Stats
    historical_trades_count: int
    forward_trades_count: int
    forward_elapsed_days: float
    forward_win_rate_pct: float
    forward_max_drawdown_pct: float
    forward_consecutive_losses: int
    observed_friction_error_bps: float
    
    # Statistical Rigor
    bootstrap_expectancy: Optional[BootstrapExpectancyResult]
    
    # Gate checklist
    gate_checks: Dict[str, bool]
    verdict_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "current_tier": self.current_tier.value,
            "is_production_qualified": self.is_production_qualified,
            "is_capital_firewall_locked": self.is_capital_firewall_locked,
            "live_execution_permitted": self.live_execution_permitted,
            "evidence": {
                "historical_trades_count": self.historical_trades_count,
                "forward_trades_count": self.forward_trades_count,
                "forward_elapsed_days": round(self.forward_elapsed_days, 2),
                "forward_win_rate_pct": round(self.forward_win_rate_pct, 2),
                "forward_max_drawdown_pct": round(self.forward_max_drawdown_pct, 2),
                "forward_consecutive_losses": self.forward_consecutive_losses,
                "observed_friction_error_bps": round(self.observed_friction_error_bps, 2),
            },
            "bootstrap_expectancy": asdict(self.bootstrap_expectancy) if self.bootstrap_expectancy else None,
            "gate_checks": self.gate_checks,
            "verdict_reasons": self.verdict_reasons,
        }


class StatisticalQualificationGatekeeper:
    """
    Independent gatekeeper enforcing strict statistical hurdles before any
    strategy promotion to production capital.
    """

    def __init__(self, hurdles: Optional[QualificationHurdles] = None):
        self.hurdles = hurdles or QualificationHurdles()

    def calculate_bootstrap_ci(
        self,
        r_returns: List[float],
        n_bootstrap: int = 2000,
        alpha_pct: float = 5.0,
    ) -> BootstrapExpectancyResult:
        """
        Computes non-parametric bootstrap confidence interval for mean R expectancy.
        """
        if not r_returns:
            return BootstrapExpectancyResult(
                mean_expectancy_r=0.0,
                ci_lower_bound_r=0.0,
                ci_upper_bound_r=0.0,
                confidence_level_pct=100.0 - alpha_pct,
                bootstrap_samples=0,
            )

        arr = np.array(r_returns, dtype=np.float64)
        n = len(arr)
        rng = np.random.default_rng(seed=42)  # Seeded for reproducible quantitative audits
        
        # Resample with replacement
        boot_indices = rng.integers(0, n, size=(n_bootstrap, n))
        boot_means = np.mean(arr[boot_indices], axis=1)

        lower_p = alpha_pct / 2.0
        upper_p = 100.0 - (alpha_pct / 2.0)
        ci_lower = float(np.percentile(boot_means, lower_p))
        ci_upper = float(np.percentile(boot_means, upper_p))
        mean_exp = float(np.mean(arr))

        return BootstrapExpectancyResult(
            mean_expectancy_r=round(mean_exp, 4),
            ci_lower_bound_r=round(ci_lower, 4),
            ci_upper_bound_r=round(ci_upper, 4),
            confidence_level_pct=100.0 - alpha_pct,
            bootstrap_samples=n_bootstrap,
        )

    def evaluate_strategy(
        self,
        strategy_id: str,
        symbol: str,
        historical_trades_count: int,
        forward_r_returns: List[float],
        forward_elapsed_days: float,
        forward_max_drawdown_pct: float,
        forward_consecutive_losses: int,
        observed_friction_error_bps: float,
    ) -> StatisticalAuditVerdict:
        """
        Evaluates candidate against multi-dimensional statistical gates.
        """
        n_fwd = len(forward_r_returns)
        wins = sum(1 for r in forward_r_returns if r > 0)
        win_rate = (wins / n_fwd * 100.0) if n_fwd > 0 else 0.0

        bootstrap_res = None
        if n_fwd >= 10:
            bootstrap_res = self.calculate_bootstrap_ci(
                forward_r_returns,
                n_bootstrap=self.hurdles.bootstrap_iterations,
                alpha_pct=100.0 - self.hurdles.confidence_level_pct,
            )

        # Gate Checks
        gate_checks = {
            "gate_01_min_forward_trades": n_fwd >= self.hurdles.min_forward_trades,
            "gate_02_min_forward_days": forward_elapsed_days >= self.hurdles.min_forward_days,
            "gate_03_bootstrap_ci_lower_bound": (
                bootstrap_res is not None and
                bootstrap_res.ci_lower_bound_r >= self.hurdles.min_expectancy_ci_lower_bound_r
            ),
            "gate_04_max_drawdown_under_ceiling": forward_max_drawdown_pct <= self.hurdles.max_forward_drawdown_pct,
            "gate_05_friction_error_under_ceiling": observed_friction_error_bps <= self.hurdles.max_friction_error_bps,
            "gate_06_consecutive_losses_under_ceiling": forward_consecutive_losses <= self.hurdles.max_consecutive_losses,
            "gate_07_win_rate_above_floor": (win_rate >= self.hurdles.min_win_rate_pct) if n_fwd >= 10 else True,
        }

        reasons = []
        all_passed = all(gate_checks.values())

        # Determine Tier
        if all_passed and n_fwd >= self.hurdles.min_forward_trades and forward_elapsed_days >= self.hurdles.min_forward_days:
            tier = StrategyLifecycleTier.PRODUCTION_QUALIFIED
            is_prod = True
            live_allowed = True
            is_firewall_locked = False
            reasons.append("All statistical, time, drawdown, and friction hurdles satisfied.")
        else:
            is_prod = False
            live_allowed = False
            is_firewall_locked = True  # Strict capital lockdown
            
            # Check whether it is forward healthy or degraded
            if forward_max_drawdown_pct > self.hurdles.max_forward_drawdown_pct:
                tier = StrategyLifecycleTier.DEGRADED_OR_DISQUALIFIED
                reasons.append(f"Forward drawdown {forward_max_drawdown_pct:.2f}% exceeds ceiling {self.hurdles.max_forward_drawdown_pct:.2f}%.")
            elif observed_friction_error_bps > self.hurdles.max_friction_error_bps:
                tier = StrategyLifecycleTier.DEGRADED_OR_DISQUALIFIED
                reasons.append(f"Friction error {observed_friction_error_bps:.2f} bps exceeds model threshold {self.hurdles.max_friction_error_bps:.2f} bps.")
            elif n_fwd < self.hurdles.min_forward_trades:
                tier = StrategyLifecycleTier.FORWARD_HEALTHY
                reasons.append(f"Insufficient forward sample: {n_fwd}/{self.hurdles.min_forward_trades} trades observed.")
                reasons.append(f"Observation window: {forward_elapsed_days:.1f}/{self.hurdles.min_forward_days:.1f} days elapsed.")
                reasons.append("Retained in FORWARD_HEALTHY tier. REAL CAPITAL STRICTLY LOCKED.")
            else:
                tier = StrategyLifecycleTier.FORWARD_HEALTHY
                reasons.append("Statistical validation in progress.")

        return StatisticalAuditVerdict(
            strategy_id=strategy_id,
            symbol=symbol,
            current_tier=tier,
            is_production_qualified=is_prod,
            is_capital_firewall_locked=is_firewall_locked,
            live_execution_permitted=live_allowed,
            historical_trades_count=historical_trades_count,
            forward_trades_count=n_fwd,
            forward_elapsed_days=forward_elapsed_days,
            forward_win_rate_pct=win_rate,
            forward_max_drawdown_pct=forward_max_drawdown_pct,
            forward_consecutive_losses=forward_consecutive_losses,
            observed_friction_error_bps=observed_friction_error_bps,
            bootstrap_expectancy=bootstrap_res,
            gate_checks=gate_checks,
            verdict_reasons=reasons,
        )
