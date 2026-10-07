"""
Tests for Execution Intelligence & Capacity Engine.
"""

from platform_core.alpha_genome import (
    AlphaFamily,
    AlphaGenome,
    EconomicPerformance,
    MicrostructureProfile,
)
from capital_intelligence.execution_capacity_engine import (
    ExecutionCapacityEngine,
    CapacityCurve,
)


def test_market_impact_and_capacity_curve():
    engine = ExecutionCapacityEngine(average_daily_volume_usd=100_000_000.0, daily_volatility=0.05)

    # Order size impact test
    impact_small = engine.calculate_market_impact_bps(order_size_usd=10_000.0)
    impact_large = engine.calculate_market_impact_bps(order_size_usd=1_000_000.0)
    assert impact_large > impact_small
    assert impact_small > 0.0

    # Capacity curve test
    genome = AlphaGenome(
        alpha_id="CAP-TEST-01",
        family=AlphaFamily.DIRECTIONAL,
        version="v1.0",
        asset_universe=["SOL/USDT"],
        venues=["BINANCE"],
        instruments=["PERPETUAL"],
        timeframe="4h",
        expected_holding_period_hours=24.0,
        economic_rationale="Capacity test.",
        features=["feat1"],
        entry_mechanism="entry",
        exit_mechanism="exit",
        performance=EconomicPerformance(gross_edge_r=0.45, hurdle_rate_r=0.20),
        microstructure=MicrostructureProfile(market_impact_parameter=0.15)
    )

    curve = engine.generate_capacity_curve(genome, aum_tiers=[10_000.0, 100_000.0, 1_000_000.0, 10_000_000.0])
    assert isinstance(curve, CapacityCurve)
    assert curve.alpha_id == genome.alpha_id
    assert len(curve.curve_points) == 4
    # Viability check: small AUM should be viable, large AUM may decay
    assert curve.curve_points[0].is_economically_viable is True
    assert curve.max_scalable_aum_usd >= 10_000.0
