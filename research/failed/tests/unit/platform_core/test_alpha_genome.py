"""
Tests for Universal Alpha Genome contract and serialization.
"""

from platform_core.alpha_genome import (
    AlphaFamily,
    AlphaGenome,
    AlphaLifecycleState,
    EconomicPerformance,
    MicrostructureProfile,
)


def test_alpha_genome_creation_and_evidence_hash():
    genome = AlphaGenome(
        alpha_id="TEST-ALPHA-01",
        family=AlphaFamily.DIRECTIONAL,
        version="v1.0",
        asset_universe=["SOL/USDT"],
        venues=["BINANCE"],
        instruments=["SPOT", "PERPETUAL"],
        timeframe="4h",
        expected_holding_period_hours=24.0,
        economic_rationale="Test momentum breakout.",
        features=["ema_20", "atr_14"],
        entry_mechanism="Bar-close confirmed breakout; execute next open.",
        exit_mechanism="Trailing stop at 2.0x ATR.",
        microstructure=MicrostructureProfile(),
        performance=EconomicPerformance(gross_edge_r=0.40, net_edge_r=0.25)
    )

    h1 = genome.compute_evidence_hash()
    assert isinstance(h1, str)
    assert len(h1) == 64

    # Determinism
    h2 = genome.compute_evidence_hash()
    assert h1 == h2


def test_alpha_genome_to_from_dict():
    genome = AlphaGenome(
        alpha_id="TEST-ALPHA-02",
        family=AlphaFamily.RELATIVE_VALUE,
        version="v2.0",
        asset_universe=["ETH/USDT", "BTC/USDT"],
        venues=["BINANCE", "OKX"],
        instruments=["PERPETUAL"],
        timeframe="1h",
        expected_holding_period_hours=48.0,
        economic_rationale="Cointegration spread mean reversion.",
        features=["z_score"],
        entry_mechanism="Z-score > 2.0.",
        exit_mechanism="Z-score reversion.",
        lifecycle_state=AlphaLifecycleState.DEV
    )

    d = genome.to_dict()
    assert d["family"] == "RELATIVE_VALUE"
    assert d["lifecycle_state"] == "DEV"

    restored = AlphaGenome.from_dict(d)
    assert restored.alpha_id == genome.alpha_id
    assert restored.family == AlphaFamily.RELATIVE_VALUE
    assert restored.lifecycle_state == AlphaLifecycleState.DEV
    assert restored.evidence_hash == genome.evidence_hash
