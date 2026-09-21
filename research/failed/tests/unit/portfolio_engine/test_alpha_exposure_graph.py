"""
Tests for Alpha Exposure Graph & Independence Engine.
"""

from platform_core.alpha_genome import (
    AlphaFamily,
    AlphaGenome,
    EconomicPerformance,
)
from portfolio_engine.alpha_exposure_graph import (
    AlphaExposureGraphEngine,
    ExposureGraphReport,
)


def test_alpha_exposure_graph_analysis():
    engine = AlphaExposureGraphEngine()

    g1 = AlphaGenome(
        alpha_id="DIR-BTC-01",
        family=AlphaFamily.DIRECTIONAL,
        version="v1.0",
        asset_universe=["BTC/USDT"],
        venues=["BINANCE"],
        instruments=["PERPETUAL"],
        timeframe="4h",
        expected_holding_period_hours=24.0,
        economic_rationale="Trend BTC.",
        features=["f1"],
        entry_mechanism="e",
        exit_mechanism="x",
        performance=EconomicPerformance(net_edge_r=0.25)
    )

    g2 = AlphaGenome(
        alpha_id="DIR-ETH-01",
        family=AlphaFamily.DIRECTIONAL,
        version="v1.0",
        asset_universe=["ETH/USDT"],
        venues=["BINANCE"],
        instruments=["PERPETUAL"],
        timeframe="4h",
        expected_holding_period_hours=24.0,
        economic_rationale="Trend ETH.",
        features=["f1"],
        entry_mechanism="e",
        exit_mechanism="x",
        performance=EconomicPerformance(net_edge_r=0.22)
    )

    g3 = AlphaGenome(
        alpha_id="CARRY-SOL-01",
        family=AlphaFamily.CARRY,
        version="v1.0",
        asset_universe=["SOL/USDT"],
        venues=["BINANCE"],
        instruments=["SPOT", "PERPETUAL"],
        timeframe="8h",
        expected_holding_period_hours=120.0,
        economic_rationale="Basis carry.",
        features=["funding"],
        entry_mechanism="e",
        exit_mechanism="x",
        performance=EconomicPerformance(net_edge_r=0.30)
    )

    report = engine.analyze_population([g1, g2, g3])
    assert isinstance(report, ExposureGraphReport)
    assert report.total_nodes == 3
    assert report.distinct_economic_clusters >= 2
    assert len(report.nodes) == 3
    assert report.nodes[0].factor_exposure.btc_beta > 0.50
