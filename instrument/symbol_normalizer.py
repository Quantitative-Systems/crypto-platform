"""Symbol Normalization and Parsing.

Translates disparate vendor/venue symbol formats into the platform's
canonical representation:
    {BASE}/{QUOTE} (e.g. BTC/USDT, BTC/USD, ETH/EUR, BTC/XAU, SOL/USD)

Handles:
- Slash separated: BTC/USDT, ETH/EUR
- Dash separated: BTC-USD, ETH-USDT
- Underscore separated: BTC_USDT, SOL_USD
- Flat concatenated: BTCUSDT, ETHUSD, SOLUSDT, BTCXAU
- Legacy exchange quirks: XBTUSD -> BTC/USD, XXBTZUSD -> BTC/USD
"""
from __future__ import annotations

import re
from typing import Tuple

from instrument.asset_class import KNOWN_COMMODITIES, KNOWN_CRYPTO_ASSETS, KNOWN_FIAT_CURRENCIES, KNOWN_STABLECOINS


# Special alias mappings
_SYMBOL_ALIASES = {
    "XBT": "BTC",
    "XXBT": "BTC",
    "XETH": "ETH",
    "ZUSD": "USD",
    "ZEUR": "EUR",
    "ZGBP": "GBP",
    "ZJPY": "JPY",
}

# Ordered candidate quotes for greedy suffix stripping on concatenated strings
_CANDIDATE_QUOTES = sorted(
    list(KNOWN_STABLECOINS | KNOWN_FIAT_CURRENCIES | KNOWN_COMMODITIES | {"BTC", "ETH"}),
    key=lambda s: len(s),
    reverse=True
)


class SymbolNormalizer:
    """Normalizes exchange-specific symbols into canonical BASE/QUOTE pairs."""

    @staticmethod
    def normalize(symbol_raw: str) -> Tuple[str, str, str]:
        """Normalizes symbol string.

        Returns:
            (canonical_symbol, base_asset, quote_asset)
            e.g. ('BTC/XAU', 'BTC', 'XAU')
        """
        raw = symbol_raw.strip().upper()

        # 1. Delimiter based splitting (/, -, _)
        for delim in ["/", "-", "_"]:
            if delim in raw:
                parts = raw.split(delim)
                if len(parts) == 2:
                    base = _SYMBOL_ALIASES.get(parts[0], parts[0])
                    quote = _SYMBOL_ALIASES.get(parts[1], parts[1])
                    return f"{base}/{quote}", base, quote

        # 2. Check known exact legacy matches (e.g. XBTUSD)
        if raw == "XBTUSD":
            return "BTC/USD", "BTC", "USD"
        if raw.startswith("XXBT") and raw.endswith("ZUSD"):
            return "BTC/USD", "BTC", "USD"

        # 3. Concatenated format (e.g. BTCUSDT, ETHUSD, BTCXAU)
        for quote_cand in _CANDIDATE_QUOTES:
            if raw.endswith(quote_cand) and len(raw) > len(quote_cand):
                base_part = raw[:-len(quote_cand)]
                base = _SYMBOL_ALIASES.get(base_part, base_part)
                quote = _SYMBOL_ALIASES.get(quote_cand, quote_cand)
                return f"{base}/{quote}", base, quote

        # Fallback if no known quote found: assume 3 or 4-letter standard quote
        if len(raw) >= 6:
            base = raw[:-3]
            quote = raw[-3:]
            return f"{base}/{quote}", base, quote

        return raw, raw, "USD"
