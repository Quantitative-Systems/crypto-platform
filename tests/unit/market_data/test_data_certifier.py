import pytest
from market_intelligence.primitives import Candle
from market_data.data_certifier import DataCertifier

def create_candle(ts: int, p: float) -> Candle:
    return Candle(timestamp=ts, open=p, high=p+1, low=p-1, close=p, volume=100)

def test_certify_dataset_valid():
    candles = [
        create_candle(3600, 100),
        create_candle(7200, 101),
        create_candle(10800, 102)
    ]
    assert DataCertifier.certify_dataset(candles, "1H", "BTCUSDT") == True

def test_certify_dataset_duplicate_timestamp():
    candles = [
        create_candle(3600, 100),
        create_candle(3600, 101),
    ]
    with pytest.raises(ValueError, match="Non-chronological or duplicate timestamp"):
        DataCertifier.certify_dataset(candles, "1H", "BTCUSDT")

def test_certify_dataset_gap():
    candles = [
        create_candle(3600, 100),
        create_candle(18000, 101), # Missing 3 bars
    ]
    with pytest.raises(ValueError, match="Gap detected"):
        DataCertifier.certify_dataset(candles, "1H", "BTCUSDT")

def test_certify_overlap_valid():
    htf = [create_candle(1000 * 3600, 100), create_candle(1024 * 3600, 101)] # 1D
    mtf = [create_candle(1000 * 3600, 100), create_candle(1004 * 3600, 101)] # 4H
    ltf = [create_candle(3500 * 3600, 100)] # 1H starts much later
    assert DataCertifier.certify_overlap(htf, mtf, ltf, min_lookback_bars=100) == True

def test_certify_overlap_invalid():
    # LTF starts at 2000 hours, HTF starts at 1500 hours.
    # HTF is 1D (24h). 100 bars = 2400 hours.
    # We need HTF to start at least 2400 hours before LTF.
    # But it starts 500 hours before LTF, so it's too late!
    htf = [create_candle(1500 * 3600, 100), create_candle(1524 * 3600, 101)] 
    mtf = [create_candle(1500 * 3600, 100), create_candle(1504 * 3600, 101)]
    ltf = [create_candle(2000 * 3600, 100)]
    
    with pytest.raises(ValueError, match="HTF dataset starts too late"):
        DataCertifier.certify_overlap(htf, mtf, ltf, min_lookback_bars=100)
