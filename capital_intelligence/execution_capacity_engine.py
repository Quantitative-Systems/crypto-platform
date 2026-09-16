"""
QCP Execution Intelligence & Capacity Engine.
Institutional microstructure cost modeling and capital capacity curve generation:
- Almgren-Chriss square-root market impact
- Spread, dynamic slippage, taker/maker fee schedule
- Borrow financing & funding drag
- Capital capacity curves across AUM tiers ($10k to $10M)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from platform_core.alpha_genome import AlphaGenome


@dataclass
class CapacityPoint:
    aum_usd: float
    order_size_usd: float
    expected_market_impact_bps: float
    expected_friction_total_bps: float
    net_edge_r: float
    is_economically_viable: bool


@dataclass
class CapacityCurve:
    alpha_id: str
    max_scalable_aum_usd: float
    curve_points: List[CapacityPoint]
    turnover_annual: float
    impact_parameter_lambda: float

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["curve_points"] = [asdict(p) for p in self.curve_points]
        return d


class ExecutionCapacityEngine:
    """
    Computes realistic execution drag and capacity bounds for alpha strategies.
    """

    def __init__(self, average_daily_volume_usd: float = 250_000_000.0, daily_volatility: float = 0.04):
        self.adv_usd = average_daily_volume_usd
        self.daily_vol = daily_volatility

    def calculate_market_impact_bps(
        self,
        order_size_usd: float,
        impact_parameter: float = 0.15
    ) -> float:
        """
        Calculates square-root market impact (Almgren-Chriss / Kyle model):
        Impact = eta * sigma * sqrt(OrderSize / ADV)
        """
        participation_ratio = max(1e-8, order_size_usd / self.adv_usd)
        impact_fraction = impact_parameter * self.daily_vol * np.sqrt(participation_ratio)
        return float(impact_fraction * 10000.0)

    def evaluate_net_edge_at_aum(
        self,
        genome: AlphaGenome,
        aum_usd: float,
        position_risk_fraction: float = 0.01
    ) -> Tuple[float, float, float]:
        """
        Computes (net_edge_r, total_friction_bps, impact_bps) at given AUM.
        """
        # Estimated position size in USD
        order_size = aum_usd * position_risk_fraction * (1.0 / 0.03)  # assuming 3% stop distance
        impact_bps = self.calculate_market_impact_bps(order_size, genome.microstructure.market_impact_parameter)

        # Baseline frictions
        spread_bps = genome.microstructure.spread_cost_bps
        slip_bps = genome.microstructure.slippage_cost_bps
        fee_bps = genome.microstructure.taker_fee_bps * 2.0  # roundtrip
        borrow_bps = (genome.microstructure.borrow_rate_apr / 365.0) * (genome.expected_holding_period_hours / 24.0) * 100.0

        total_friction_bps = spread_bps + slip_bps + fee_bps + borrow_bps + impact_bps

        # Convert friction bps into R drag (assuming 300 bps stop distance = 1.0R)
        stop_distance_bps = 300.0
        friction_drag_r = total_friction_bps / stop_distance_bps

        net_edge = genome.performance.gross_edge_r - friction_drag_r
        return net_edge, total_friction_bps, impact_bps

    def generate_capacity_curve(
        self,
        genome: AlphaGenome,
        aum_tiers: Optional[List[float]] = None
    ) -> CapacityCurve:
        """
        Generates empirical capacity curve across capital tiers.
        """
        tiers = aum_tiers or [10_000.0, 50_000.0, 250_000.0, 1_000_000.0, 5_000_000.0, 10_000_000.0]
        points: List[CapacityPoint] = []
        max_viable_aum = 0.0

        for aum in tiers:
            net_edge, friction_bps, impact_bps = self.evaluate_net_edge_at_aum(genome, aum)
            is_viable = net_edge >= genome.performance.hurdle_rate_r
            if is_viable:
                max_viable_aum = max(max_viable_aum, aum)

            points.append(CapacityPoint(
                aum_usd=aum,
                order_size_usd=round(aum * 0.33, 2),
                expected_market_impact_bps=round(impact_bps, 2),
                expected_friction_total_bps=round(friction_bps, 2),
                net_edge_r=round(net_edge, 4),
                is_economically_viable=is_viable
            ))

        turnover = (365.0 * 24.0 / max(1.0, genome.expected_holding_period_hours))

        return CapacityCurve(
            alpha_id=genome.alpha_id,
            max_scalable_aum_usd=max_viable_aum,
            curve_points=points,
            turnover_annual=round(turnover, 1),
            impact_parameter_lambda=genome.microstructure.market_impact_parameter
        )
