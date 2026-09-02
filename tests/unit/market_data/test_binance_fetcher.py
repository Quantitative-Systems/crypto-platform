"""
Unit tests for BinanceFetcher.get_ticker public ticker API contract.
"""

import io
import json
import urllib.error
from unittest.mock import patch, MagicMock
import pytest

from market_data.binance_fetcher import BinanceFetcher


def test_get_ticker_valid_response():
    """Test that a valid 200 OK ticker response correctly parses and returns the float price."""
    fake_body = json.dumps({"symbol": "BTCUSDT", "price": "62500.50"}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        price = BinanceFetcher.get_ticker("BTC/USDT")
        assert price == 62500.50
        assert isinstance(price, float)
        # Check URL requested
        req_arg = mock_urlopen.call_args[0][0]
        assert "symbol=BTCUSDT" in req_arg.full_url


def test_get_ticker_symbol_normalization():
    """Test that various symbol representations (BTCUSD, BTC/USDT) normalize to BTCUSDT."""
    fake_body = json.dumps({"symbol": "BTCUSDT", "price": "60000.00"}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        price = BinanceFetcher.get_ticker("BTCUSD")
        assert price == 60000.00
        req_arg = mock_urlopen.call_args[0][0]
        assert "symbol=BTCUSDT" in req_arg.full_url


def test_get_ticker_malformed_response_missing_price():
    """Test that a response without 'price' raises ValueError."""
    fake_body = json.dumps({"symbol": "BTCUSDT", "invalid_field": "123"}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(ValueError, match="Malformed Binance ticker response"):
            BinanceFetcher.get_ticker("BTC/USDT")


def test_get_ticker_malformed_response_non_dict():
    """Test that a non-dict JSON response raises ValueError."""
    fake_body = json.dumps(["invalid", "array"]).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(ValueError, match="Malformed Binance ticker response"):
            BinanceFetcher.get_ticker("BTC/USDT")


def test_get_ticker_http_error_status():
    """Test that a non-200 HTTP response raises RuntimeError."""
    mock_resp = MagicMock()
    mock_resp.status = 400
    mock_resp.read.return_value = b"{}"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Binance API returned HTTP status 400"):
            BinanceFetcher.get_ticker("BTC/USDT")


def test_get_ticker_network_timeout():
    """Test that network timeouts / URLError propagate explicitly rather than returning fallback."""
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection timed out")):
        with pytest.raises(urllib.error.URLError):
            BinanceFetcher.get_ticker("BTC/USDT")
