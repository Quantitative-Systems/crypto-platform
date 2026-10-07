import re

with open("research/strategy_grammar.py", "r") as f:
    content = f.read()

# Add to HTFBias
content = content.replace(
    "    NEUTRAL = \"NEUTRAL\"",
    "    NEUTRAL = \"NEUTRAL\"\n    MARKET_STRUCTURE = \"MARKET_STRUCTURE\"\n    MACD_MOMENTUM = \"MACD_MOMENTUM\"\n    MEAN_REVERSION_STRETCH = \"MEAN_REVERSION_STRETCH\""
)

# Add to COMPATIBLE_REGIMES
content = content.replace(
    "    HTFBias.NEUTRAL: list(RegimeState)",
    "    HTFBias.NEUTRAL: list(RegimeState),\n    HTFBias.MARKET_STRUCTURE: [RegimeState.TRENDING_UP, RegimeState.TRENDING_DOWN],\n    HTFBias.MACD_MOMENTUM: [RegimeState.TRENDING_UP, RegimeState.TRENDING_DOWN, RegimeState.HIGH_VOLATILITY],\n    HTFBias.MEAN_REVERSION_STRETCH: [RegimeState.RANGING, RegimeState.HIGH_VOLATILITY]"
)

# Add to MTFSetup
content = content.replace(
    "    NO_SETUP = \"NO_SETUP\"",
    "    NO_SETUP = \"NO_SETUP\"\n    LIQUIDITY_SWEEP = \"LIQUIDITY_SWEEP\"\n    ORDER_BLOCK_TAP = \"ORDER_BLOCK_TAP\"\n    BOLLINGER_SQUEEZE = \"BOLLINGER_SQUEEZE\""
)

# Add to LTFEntry
content = content.replace(
    "    RSI_CONFIRMATION = \"RSI_CONFIRMATION\"",
    "    RSI_CONFIRMATION = \"RSI_CONFIRMATION\"\n    PIN_BAR_REJECTION = \"PIN_BAR_REJECTION\"\n    INSIDE_BAR_BREAKOUT = \"INSIDE_BAR_BREAKOUT\"\n    ENGULFING_CONFIRMATION = \"ENGULFING_CONFIRMATION\""
)

with open("research/strategy_grammar.py", "w") as f:
    f.write(content)
