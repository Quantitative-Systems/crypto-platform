"""Quote Currency Definitions and Financial Properties.

Classifies the second leg of any instrument:
- FIAT: Sovereign currencies (USD, EUR, GBP, JPY) requiring FX cross-rates.
- STABLECOIN: USD or EUR pegged tokens (USDT, USDC, FDUSD) with 1:1 or near 1:1 peg.
- COMMODITY: Real assets (XAU, XAG) requiring ounce-to-USD translation.
- CRYPTO: Crypto-to-crypto quote pairs (e.g., SOL/BTC, ETH/BTC).
- OTHER_SUPPORTED_ASSET: Synthetic or basket assets.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from instrument.asset_class import AssetClass, classify_asset


class QuoteSettlementType(str, Enum):
    """Settlement mechanics for the quote currency."""
    DIRECT_USD = "DIRECT_USD"          # Quote is USD directly
    STABLECOIN_USD = "STABLECOIN_USD"  # Quote is USD pegged stablecoin (USDT, USDC)
    FIAT_FX = "FIAT_FX"                # Quote is foreign fiat (EUR, GBP, JPY)
    COMMODITY_XAU = "COMMODITY_XAU"    # Quote is commodity unit (troy ounce gold)
    CRYPTO_BASE = "CRYPTO_BASE"        # Quote is another crypto asset (BTC, ETH)
    OTHER = "OTHER"


@dataclass(frozen=True)
class QuoteCurrencyInfo:
    """Metadata describing economic and settlement characteristics of quote currency."""
    symbol: str
    asset_class: AssetClass
    settlement_type: QuoteSettlementType
    is_usd_pegged: bool
    requires_fx_conversion: bool
    description: str


_REGISTERED_QUOTES: Dict[str, QuoteCurrencyInfo] = {
    "USD": QuoteCurrencyInfo(
        symbol="USD",
        asset_class=AssetClass.FIAT,
        settlement_type=QuoteSettlementType.DIRECT_USD,
        is_usd_pegged=True,
        requires_fx_conversion=False,
        description="US Dollar (Federal Reserve fiat sovereign currency)"
    ),
    "USDT": QuoteCurrencyInfo(
        symbol="USDT",
        asset_class=AssetClass.STABLECOIN,
        settlement_type=QuoteSettlementType.STABLECOIN_USD,
        is_usd_pegged=True,
        requires_fx_conversion=False,
        description="Tether USD (fiat-backed stablecoin)"
    ),
    "USDC": QuoteCurrencyInfo(
        symbol="USDC",
        asset_class=AssetClass.STABLECOIN,
        settlement_type=QuoteSettlementType.STABLECOIN_USD,
        is_usd_pegged=True,
        requires_fx_conversion=False,
        description="USD Coin (Circle audited stablecoin)"
    ),
    "EUR": QuoteCurrencyInfo(
        symbol="EUR",
        asset_class=AssetClass.FIAT,
        settlement_type=QuoteSettlementType.FIAT_FX,
        is_usd_pegged=False,
        requires_fx_conversion=True,
        description="Euro (European Central Bank sovereign fiat)"
    ),
    "GBP": QuoteCurrencyInfo(
        symbol="GBP",
        asset_class=AssetClass.FIAT,
        settlement_type=QuoteSettlementType.FIAT_FX,
        is_usd_pegged=False,
        requires_fx_conversion=True,
        description="British Pound Sterling (Bank of England sovereign fiat)"
    ),
    "JPY": QuoteCurrencyInfo(
        symbol="JPY",
        asset_class=AssetClass.FIAT,
        settlement_type=QuoteSettlementType.FIAT_FX,
        is_usd_pegged=False,
        requires_fx_conversion=True,
        description="Japanese Yen (Bank of Japan sovereign fiat)"
    ),
    "XAU": QuoteCurrencyInfo(
        symbol="XAU",
        asset_class=AssetClass.COMMODITY,
        settlement_type=QuoteSettlementType.COMMODITY_XAU,
        is_usd_pegged=False,
        requires_fx_conversion=True,
        description="Gold (One Troy Ounce Fine Gold, XAU/USD cross required)"
    ),
    "BTC": QuoteCurrencyInfo(
        symbol="BTC",
        asset_class=AssetClass.CRYPTO,
        settlement_type=QuoteSettlementType.CRYPTO_BASE,
        is_usd_pegged=False,
        requires_fx_conversion=True,
        description="Bitcoin (Crypto-quoted instrument, BTC/USD cross required)"
    ),
}


def get_quote_info(quote_symbol: str) -> QuoteCurrencyInfo:
    """Retrieve or dynamically infer quote currency properties."""
    token = quote_symbol.upper().strip()
    if token in _REGISTERED_QUOTES:
        return _REGISTERED_QUOTES[token]

    asset_cls = classify_asset(token)
    if asset_cls == AssetClass.STABLECOIN:
        settlement = QuoteSettlementType.STABLECOIN_USD
        usd_pegged = True
        fx_req = False
    elif asset_cls == AssetClass.FIAT:
        settlement = QuoteSettlementType.FIAT_FX
        usd_pegged = False
        fx_req = True
    elif asset_cls == AssetClass.COMMODITY:
        settlement = QuoteSettlementType.COMMODITY_XAU
        usd_pegged = False
        fx_req = True
    elif asset_cls == AssetClass.CRYPTO:
        settlement = QuoteSettlementType.CRYPTO_BASE
        usd_pegged = False
        fx_req = True
    else:
        settlement = QuoteSettlementType.OTHER
        usd_pegged = False
        fx_req = True

    return QuoteCurrencyInfo(
        symbol=token,
        asset_class=asset_cls,
        settlement_type=settlement,
        is_usd_pegged=usd_pegged,
        requires_fx_conversion=fx_req,
        description=f"Auto-classified quote asset {token} ({asset_cls.value})"
    )
