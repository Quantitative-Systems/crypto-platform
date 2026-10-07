"""Parameter Stability & Performance Plateau Detection Engine.

Quantifies whether a strategy candidate represents a broad, robust performance plateau
or an overfitted, isolated single-parameter spike.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np


@dataclass
class StabilityReport:
    """Evaluation of parameter neighborhood stability."""
    parameter_name: str
    optimal_parameter_value: float
    optimal_expectancy_r: float
    neighborhood_mean_expectancy_r: float
    neighborhood_min_expectancy_r: float
    neighborhood_std_expectancy_r: float
    plateau_stability_index: float  # PSI: 0.0 (erratic spike) to 1.0 (flat resilient plateau)
    is_stable_plateau: bool
    details: Dict[str, Any]


class ParameterStabilityAnalyzer:
    """Analyzes performance sensitivity across parameter variations."""

    def evaluate_1d_stability(
        self,
        parameter_name: str,
        param_values: List[float],
        expectancy_r_values: List[float],
        plateau_threshold_psi: float = 0.65,
    ) -> StabilityReport:
        """Evaluate stability across a single parameter vector (e.g. Lookback, Threshold)."""
        params = np.array(param_values, dtype=np.float64)
        exp_r = np.array(expectancy_r_values, dtype=np.float64)

        if len(params) < 3:
            return StabilityReport(
                parameter_name=parameter_name,
                optimal_parameter_value=float(params[0]) if len(params) > 0 else 0.0,
                optimal_expectancy_r=float(exp_r[0]) if len(exp_r) > 0 else 0.0,
                neighborhood_mean_expectancy_r=0.0,
                neighborhood_min_expectancy_r=0.0,
                neighborhood_std_expectancy_r=0.0,
                plateau_stability_index=0.0,
                is_stable_plateau=False,
                details={"reason": "INSUFFICIENT_PARAMETER_SAMPLES"},
            )

        best_idx = int(np.argmax(exp_r))
        opt_param = float(params[best_idx])
        opt_exp = float(exp_r[best_idx])

        # Define neighborhood: immediate adjacent indices (left, optimal, right)
        start_idx = max(0, best_idx - 1)
        end_idx = min(len(params), best_idx + 2)
        neighborhood_exp = exp_r[start_idx:end_idx]

        mean_exp = float(np.mean(neighborhood_exp))
        min_exp = float(np.min(neighborhood_exp))
        std_exp = float(np.std(neighborhood_exp))

        # Plateau Stability Index (PSI):
        # Measures how close the neighborhood minimum is to the optimal peak,
        # penalizing sharp drop-offs.
        if opt_exp > 0:
            ratio = max(0.0, min_exp / opt_exp)
            # Penalize variance
            cv = std_exp / (mean_exp + 1e-6)
            psi = float(np.clip(ratio * (1.0 / (1.0 + cv)), 0.0, 1.0))
        else:
            psi = 0.0

        is_stable = (psi >= plateau_threshold_psi) and (min_exp > 0)

        return StabilityReport(
            parameter_name=parameter_name,
            optimal_parameter_value=opt_param,
            optimal_expectancy_r=round(opt_exp, 4),
            neighborhood_mean_expectancy_r=round(mean_exp, 4),
            neighborhood_min_expectancy_r=round(min_exp, 4),
            neighborhood_std_expectancy_r=round(std_exp, 4),
            plateau_stability_index=round(psi, 3),
            is_stable_plateau=bool(is_stable),
            details={
                "all_parameters": list(params),
                "all_expectancies": list(exp_r),
                "neighborhood_indices": list(range(start_idx, end_idx)),
            },
        )
