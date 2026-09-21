"""
Integration Tests for Relative Value Research Pipeline.
Tests end-to-end execution of RelativeValueEngine over certified cached historical data.
"""

import pytest
from market_data.binance_fetcher import BinanceFetcher
from research.discovery_lab.relative_value_config import RelativeValueConfig
from research.discovery_lab.relative_value_engine import (
    RelativeValueEngine,
    RelativeValueResearchReport,
)


def test_relative_value_research_btc_eth_1d():
    btc_candles = BinanceFetcher.fetch_real_candles("BTC/USDT", "1d", limit=1000)
    eth_candles = BinanceFetcher.fetch_real_candles("ETH/USDT", "1d", limit=1000)

    assert len(btc_candles) > 500
    assert len(eth_candles) > 500

    engine = RelativeValueEngine()
    report: RelativeValueResearchReport = engine.evaluate_pair(
        symbol_a="BTC/USDT",
        symbol_b="ETH/USDT",
        pair_name="BTC/ETH",
        candles_a=btc_candles,
        candles_b=eth_candles,
        timeframe="1d",
    )

    assert report.pair_name == "BTC/ETH"
    assert report.total_aligned_bars > 500
    assert report.cointegration.hedge_ratio_beta > 0.0
    assert report.cointegration.half_life_bars > 0.0
    assert report.full_sample.partition_name == "FULL_SAMPLE"
    assert report.dev_sample.partition_name == "DEV_SAMPLE"
    assert report.val_sample.partition_name == "VAL_SAMPLE"
    assert report.oos_sample.partition_name == "OOS_SAMPLE"
    assert report.research_verdict in (
        "QUALIFIED_RESEARCH_CANDIDATE",
        "FALSIFIED_NO_COINTEGRATION",
        "FRAGILE_SLOW_MEAN_REVERSION",
        "FRAGILE_OOS_DEGRADED",
        "FRAGILE_MARGINAL_EDGE",
    )
