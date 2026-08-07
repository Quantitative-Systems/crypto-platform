"""
Product 01: Crypto Platform - Decoupled Asset Universe Configuration
Defines primary asset universes away from strategy and execution logic.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class AssetConfig:
    symbol: str
    base_asset: str
    quote_asset: str
    maker_fee_pct: float = 0.00075  # 0.075%
    taker_fee_pct: float = 0.00075  # 0.075%
    min_qty: float = 0.0001


class AssetRegistry:
    PRIMARY_CRYPTO_MAJORS: List[AssetConfig] = [
        AssetConfig(symbol="BTC/USDT", base_asset="BTC", quote_asset="USDT"),
        AssetConfig(symbol="ETH/USDT", base_asset="ETH", quote_asset="USDT"),
        AssetConfig(symbol="SOL/USDT", base_asset="SOL", quote_asset="USDT"),
    ]

    @staticmethod
    def get_asset(symbol: str) -> AssetConfig:
        for asset in AssetRegistry.PRIMARY_CRYPTO_MAJORS:
            if asset.symbol == symbol:
                return asset
        return AssetConfig(symbol=symbol, base_asset=symbol.split("/")[0], quote_asset="USDT")