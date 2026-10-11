"""STRATA Digital Trading Platform — Five-Set Architecture & Parity Unit Tests.

Certifies:
1. Canonical 7-timeframe ladder (1M -> 1W -> 1D -> 4H -> 1H -> 15M -> 3M).
2. Canonical 5 overlapping sets (Set 1 to Set 5) with HTF/MTF/LTF roles.
3. Strict parity across shared timeframes for the same asset and closed-candle state.
4. Canonical production_eligible semantics: Sets 2-4 production cohort, Sets 1 & 5 zero-capital observation.
"""
import pytest
from market_data.market_service import MarketService, AssetMarketCard
from market_data.universe.crypto_universe import CryptoUniverseManager


def test_seven_timeframe_ladder_completeness():
    service = MarketService()
    for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        detail = service.get_asset_detail(symbol)
        assert detail is not None, f"Asset {symbol} must exist"
        timeframes = detail["timeframes"]
        canonical_ladder = ["1M", "1W", "1D", "4H", "1H", "15M", "3M"]
        for tf in canonical_ladder:
            assert tf in timeframes, f"Timeframe {tf} missing from {symbol}"
            tf_data = timeframes[tf]
            assert "structure" in tf_data
            assert "phase" in tf_data
            assert "key_level_support" in tf_data
            assert "key_level_resistance" in tf_data
            assert "premium_discount" in tf_data
            assert "closed_candles_count" in tf_data


def test_five_set_ladder_roles_and_eligibility():
    service = MarketService()
    ladder = service.get_five_set_ladder("BTCUSDT")
    assert ladder["symbol"] == "BTCUSDT"
    sets = ladder["sets"]
    assert len(sets) == 5, f"Must have exactly 5 sets, found {len(sets)}"

    # Set 1: Macro Context (Zero Capital)
    s1 = sets["SET_1"]
    assert s1["htf"]["timeframe"] == "1M"
    assert s1["mtf"]["timeframe"] == "1W"
    assert s1["ltf"]["timeframe"] == "1D"
    assert "Macro Context" in s1["role"]
    assert s1["production_eligible"] is False
    assert "$0.00 capital" in s1["purpose"]

    # Set 2: Higher-Timeframe Trading
    s2 = sets["SET_2"]
    assert s2["htf"]["timeframe"] == "1W"
    assert s2["mtf"]["timeframe"] == "1D"
    assert s2["ltf"]["timeframe"] == "4H"
    assert "Higher-Timeframe" in s2["role"]
    assert s2["production_eligible"] is True

    # Set 3: Daily/Swing Trading
    s3 = sets["SET_3"]
    assert s3["htf"]["timeframe"] == "1D"
    assert s3["mtf"]["timeframe"] == "4H"
    assert s3["ltf"]["timeframe"] == "1H"
    assert "Swing" in s3["role"] or "Daily" in s3["role"]
    assert s3["production_eligible"] is True

    # Set 4: Intraday Trading
    s4 = sets["SET_4"]
    assert s4["htf"]["timeframe"] == "4H"
    assert s4["mtf"]["timeframe"] == "1H"
    assert s4["ltf"]["timeframe"] == "15M"
    assert "Intraday" in s4["role"]
    assert s4["production_eligible"] is True

    # Set 5: Lower-Timeframe Observation (Zero Capital)
    s5 = sets["SET_5"]
    assert s5["htf"]["timeframe"] == "1H"
    assert s5["mtf"]["timeframe"] == "15M"
    assert s5["ltf"]["timeframe"] == "3M"
    assert "Lower-Timeframe" in s5["role"]
    assert s5["production_eligible"] is False
    assert "$0.00 capital" in s5["purpose"]


def test_shared_timeframe_parity_verification():
    service = MarketService()
    for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        audit = service.verify_five_set_parity(symbol)
        assert audit["verified"] is True, f"Parity audit failed for {symbol}: {audit}"
        assert audit["sets_count"] == 5
        assert audit["timeframes_count"] == 7

        checks = audit["checks"]
        assert checks["set1_mtf_vs_set2_htf_1W"] is True
        assert checks["set1_ltf_vs_set2_mtf_1D"] is True
        assert checks["set2_ltf_vs_set3_mtf_4H"] is True
        assert checks["set3_ltf_vs_set4_mtf_1H"] is True
        assert checks["set4_ltf_vs_set5_mtf_15M"] is True


def test_shared_timeframe_field_level_equivalence():
    service = MarketService()
    ladder = service.get_five_set_ladder("BTCUSDT")
    sets = ladder["sets"]

    # 1. 1W equivalence: Set 1 MTF == Set 2 HTF
    assert sets["SET_1"]["mtf"] == sets["SET_2"]["htf"]

    # 2. 1D equivalence: Set 1 LTF == Set 2 MTF == Set 3 HTF
    assert sets["SET_1"]["ltf"] == sets["SET_2"]["mtf"]
    assert sets["SET_2"]["mtf"] == sets["SET_3"]["htf"]

    # 3. 4H equivalence: Set 2 LTF == Set 3 MTF == Set 4 HTF
    assert sets["SET_2"]["ltf"] == sets["SET_3"]["mtf"]
    assert sets["SET_3"]["mtf"] == sets["SET_4"]["htf"]

    # 4. 1H equivalence: Set 3 LTF == Set 4 MTF == Set 5 HTF
    assert sets["SET_3"]["ltf"] == sets["SET_4"]["mtf"]
    assert sets["SET_4"]["mtf"] == sets["SET_5"]["htf"]

    # 5. 15M equivalence: Set 4 LTF == Set 5 MTF
    assert sets["SET_4"]["ltf"] == sets["SET_5"]["mtf"]


def test_production_eligibility_preservation():
    """Confirms production_eligible criteria in Phase R decision engine contract."""
    from execution.decision.phase_r_decision_engine import (
        is_production_eligible,
        ELIGIBLE_PRODUCTION_SETS,
    )

    # Sets 2, 3, 4 are production eligible when confidence >= 0.50
    assert ELIGIBLE_PRODUCTION_SETS == {"SET_2", "SET_3", "SET_4"}
    assert is_production_eligible("SET_2", 0.60) is True
    assert is_production_eligible("SET_3", 0.50) is True
    assert is_production_eligible("SET_4", 0.75) is True

    # Confidence below 0.50 is NOT production eligible
    assert is_production_eligible("SET_2", 0.49) is False

    # Sets 1 and 5 are NOT production eligible even at high confidence, but remain observable
    assert is_production_eligible("SET_1", 0.95) is False
    assert is_production_eligible("SET_5", 0.95) is False
