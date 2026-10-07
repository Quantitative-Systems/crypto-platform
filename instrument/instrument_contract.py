"""Instrument Contract and Crypto-Base Invariant Enforcement.

Enforces the foundational platform architectural rule:
    BASE_ASSET_CLASS == AssetClass.CRYPTO

The first leg MUST be crypto (e.g., BTC, ETH, SOL).
The second leg can be ANY supported asset/currency/instrument:
- FIAT: USD, EUR, GBP, JPY
- STABLECOIN: USDT, USDC, DAI
- COMMODITY: XAU (Gold)
- CRYPTO: BTC, ETH (crypto-crypto pairs)

Any instrument with a non-crypto base (e.g. EUR/USD, GBP/USD, XAU/USD, USD/JPY)
is strictly INELIGIBLE for this trading engine and rejected with:
    reason: "BASE_NOT_CRYPTO"
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from instrument.asset_class import AssetClass, classify_asset
from instrument.liquidity_profile import LiquidityProfile
from instrument.quote_currency import QuoteCurrencyInfo, get_quote_info
from instrument.symbol_normalizer import SymbolNormalizer
from instrument.trading_constraints import TradingConstraints


@dataclass(frozen=True)
class CryptoBaseInstrument:
    """Canonical instrument contract for the crypto-first trading engine."""
    symbol: str                               # e.g., 'BTC/XAU', 'BTC/USD', 'ETH/EUR'
    base_asset: str                           # e.g., 'BTC'
    base_class: AssetClass                    # Must be AssetClass.CRYPTO for eligibility
    quote_asset: str                          # e.g., 'XAU', 'USD', 'EUR', 'USDT'
    quote_class: AssetClass                   # COMMODITY, FIAT, STABLECOIN, etc.
    engine_eligible: bool                     # True iff base_class == AssetClass.CRYPTO
    reason: Optional[str] = None              # Reason if ineligible (e.g., "BASE_NOT_CRYPTO")
    trading_constraints: TradingConstraints = field(default_factory=TradingConstraints)
    liquidity_profile: LiquidityProfile = field(default_factory=LiquidityProfile)
    quote_info: Optional[QuoteCurrencyInfo] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert instrument contract to standard JSON-serializable dictionary."""
        d: Dict[str, Any] = {
            "symbol": self.symbol,
            "base_asset": self.base_asset,
            "base_class": self.base_class.value,
            "quote_asset": self.quote_asset,
            "quote_class": self.quote_class.value,
            "engine_eligible": self.engine_eligible,
        }
        if not self.engine_eligible and self.reason:
            d["reason"] = self.reason
        return d


def build_instrument(
    symbol_raw: str,
    constraints: Optional[TradingConstraints] = None,
    liquidity: Optional[LiquidityProfile] = None,
) -> CryptoBaseInstrument:
    """Build and validate a CryptoBaseInstrument from an input symbol."""
    canonical, base, quote = SymbolNormalizer.normalize(symbol_raw)
    base_class = classify_asset(base)
    quote_class = classify_asset(quote)
    quote_info = get_quote_info(quote)

    # Foundational invariant check: Base leg MUST be CRYPTO
    if base_class != AssetClass.CRYPTO:
        return CryptoBaseInstrument(
            symbol=canonical,
            base_asset=base,
            base_class=base_class,
            quote_asset=quote,
            quote_class=quote_class,
            engine_eligible=False,
            reason="BASE_NOT_CRYPTO",
            trading_constraints=constraints or TradingConstraints(),
            liquidity_profile=liquidity or LiquidityProfile(),
            quote_info=quote_info,
        )

    return CryptoBaseInstrument(
        symbol=canonical,
        base_asset=base,
        base_class=base_class,
        quote_asset=quote,
        quote_class=quote_class,
        engine_eligible=True,
        reason=None,
        trading_constraints=constraints or TradingConstraints(),
        liquidity_profile=liquidity or LiquidityProfile(),
        quote_info=quote_info,
    )
