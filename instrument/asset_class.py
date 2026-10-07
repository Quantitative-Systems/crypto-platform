"""Asset Class Taxonomy and Invariant Contracts.

Enforces the foundational platform rule:
The first leg (base asset) of any tradable instrument in this engine MUST be CRYPTO.
Non-crypto bases (e.g., EUR/USD, XAU/USD) belong to external non-crypto research domains.
"""
from __future__ import annotations

from enum import Enum
from typing import Set


class AssetClass(str, Enum):
    """Broad financial asset classification."""
    CRYPTO = "CRYPTO"            # Decentralized digital assets: BTC, ETH, SOL, AVAX, etc.
    FIAT = "FIAT"                # Sovereign central bank currencies: USD, EUR, GBP, JPY, CHF, etc.
    STABLECOIN = "STABLECOIN"    # Pegged digital currency: USDT, USDC, DAI, USDE, PYUSD, etc.
    COMMODITY = "COMMODITY"      # Physical assets: XAU (Gold), XAG (Silver), WTI, BRENT, etc.
    EQUITY = "EQUITY"            # Shares & Equities: AAPL, NVDA, COIN, MSTR, etc.
    INDEX = "INDEX"              # Macro market indices: SPX, NDX, DXY, VIX, etc.


KNOWN_CRYPTO_ASSETS: Set[str] = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "SUI",
    "DOT", "NEAR", "APT", "UNI", "LTC", "BCH", "XLM", "ICP", "AAVE", "RENDER",
    "FET", "TAO", "PEPE", "SHIB", "HBAR", "ATOM", "FIL", "ARB", "OP", "POL",
}

KNOWN_FIAT_CURRENCIES: Set[str] = {
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "CNY", "INR", "KRW",
}

KNOWN_STABLECOINS: Set[str] = {
    "USDT", "USDC", "DAI", "FDUSD", "TUSD", "USDD", "USDE", "PYUSD", "EURC",
}

KNOWN_COMMODITIES: Set[str] = {
    "XAU", "XAG", "OIL", "WTI", "BRENT", "NATGAS", "COPPER",
}


def classify_asset(symbol_token: str) -> AssetClass:
    """Deterministically classify an asset token into its asset class."""
    token = symbol_token.upper().strip()
    if token in KNOWN_CRYPTO_ASSETS:
        return AssetClass.CRYPTO
    if token in KNOWN_STABLECOINS:
        return AssetClass.STABLECOIN
    if token in KNOWN_FIAT_CURRENCIES:
        return AssetClass.FIAT
    if token in KNOWN_COMMODITIES:
        return AssetClass.COMMODITY
    # Default heuristic: if length > 4 and contains USD, likely stablecoin; else assume crypto if traded
    if token.endswith("USD") and token != "USD":
        return AssetClass.STABLECOIN
    return AssetClass.CRYPTO
