"""STRATA — Crypto-Only Universe Manager.

Strictly enforces that all trading, backtesting, and strategy evaluation occurs on
admitted cryptocurrency assets only.
Rejects any non-crypto assets (equities, index futures, forex, commodities).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AssetClass(str, Enum):
    CRYPTO_SPOT = "CRYPTO_SPOT"
    CRYPTO_PERPETUAL = "CRYPTO_PERPETUAL"


@dataclass(frozen=True)
class CryptoAssetProfile:
    symbol: str
    base_asset: str
    quote_asset: str
    asset_class: AssetClass
    min_notional_usd: float
    lot_step_size: float
    tick_size: float
    maker_fee_bps: float
    taker_fee_bps: float
    supports_funding: bool
    is_active: bool = True
    liquidity_score: float = 1.0


class NonCryptoAssetError(ValueError):
    """Raised when an attempt is made to evaluate or trade a non-crypto asset."""
    pass


class CryptoUniverseManager:
    """Authoritative crypto-only universe manager for STRATA."""

    ADMITTED_CRYPTO_ASSETS: Dict[str, CryptoAssetProfile] = {
        "BTCUSDT": CryptoAssetProfile(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            asset_class=AssetClass.CRYPTO_PERPETUAL,
            min_notional_usd=5.0,
            lot_step_size=0.001,
            tick_size=0.10,
            maker_fee_bps=2.0,
            taker_fee_bps=5.0,
            supports_funding=True,
            liquidity_score=1.0,
        ),
        "ETHUSDT": CryptoAssetProfile(
            symbol="ETHUSDT",
            base_asset="ETH",
            quote_asset="USDT",
            asset_class=AssetClass.CRYPTO_PERPETUAL,
            min_notional_usd=5.0,
            lot_step_size=0.01,
            tick_size=0.01,
            maker_fee_bps=2.0,
            taker_fee_bps=5.0,
            supports_funding=True,
            liquidity_score=0.95,
        ),
        "SOLUSDT": CryptoAssetProfile(
            symbol="SOLUSDT",
            base_asset="SOL",
            quote_asset="USDT",
            asset_class=AssetClass.CRYPTO_PERPETUAL,
            min_notional_usd=5.0,
            lot_step_size=0.1,
            tick_size=0.01,
            maker_fee_bps=2.0,
            taker_fee_bps=5.0,
            supports_funding=True,
            liquidity_score=0.90,
        ),
        "BNBUSDT": CryptoAssetProfile(
            symbol="BNBUSDT",
            base_asset="BNB",
            quote_asset="USDT",
            asset_class=AssetClass.CRYPTO_PERPETUAL,
            min_notional_usd=5.0,
            lot_step_size=0.01,
            tick_size=0.01,
            maker_fee_bps=2.0,
            taker_fee_bps=5.0,
            supports_funding=True,
            liquidity_score=0.88,
        ),
    }

    DISALLOWED_KEYWORDS: Set[str] = {
        "AAPL", "MSFT", "TSLA", "NVDA", "SPX", "SPY", "QQQ", "NDX",
        "NIFTY", "BANKNIFTY", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD",
        "GOLD", "CRUDE", "OIL", "DOW", "FTSE", "DAX",
    }

    @classmethod
    def validate_asset(cls, symbol: str) -> CryptoAssetProfile:
        """Validates that symbol is an approved crypto asset, rejecting all others."""
        sym = symbol.upper().replace("/", "").replace("-", "")

        # Explicit non-crypto check
        for dis in cls.DISALLOWED_KEYWORDS:
            if dis in sym:
                raise NonCryptoAssetError(
                    f"STRATA is strictly a CRYPTO trading platform. Non-crypto asset '{symbol}' is forbidden."
                )

        if sym not in cls.ADMITTED_CRYPTO_ASSETS:
            raise NonCryptoAssetError(
                f"Asset '{symbol}' is not currently admitted in the STRATA Crypto Universe. "
                f"Admitted assets: {list(cls.ADMITTED_CRYPTO_ASSETS.keys())}"
            )

        return cls.ADMITTED_CRYPTO_ASSETS[sym]

    @classmethod
    def list_admitted_assets(cls) -> List[CryptoAssetProfile]:
        return list(cls.ADMITTED_CRYPTO_ASSETS.values())

    @classmethod
    def is_admitted(cls, symbol: str) -> bool:
        try:
            cls.validate_asset(symbol)
            return True
        except NonCryptoAssetError:
            return False
