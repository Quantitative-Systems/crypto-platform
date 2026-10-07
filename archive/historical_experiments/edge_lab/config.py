"""QCP Edge Lab config — 10 assets x 6 sets, chronological splits, risk gates.

Why this exists:
- Current canonical stack is over-filtered (6R/4R firewalls) and under-powered
  on SET_5/SET_6 (1m/5m history is ~10-35 days). Forcing "profitable everywhere"
  would require fabricating edge. This module instead provides a *falsifiable*
  search surface with honest DEV/VAL/OOS separation and cost-aware gates.
"""
from __future__ import annotations

ASSETS_10 = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "LINK/USDT", "LTC/USDT",
]

# Canonical 6-set ladder -> cache timeframe labels
SETS_6 = {
    "SET_1": {"htf": "1M", "mtf": "1w", "ltf": "1d", "style": "Investing / Macro"},
    "SET_2": {"htf": "1w", "mtf": "1d", "ltf": "4h", "style": "Position Trading"},
    "SET_3": {"htf": "1d", "mtf": "4h", "ltf": "1h", "style": "Swing Trading"},
    "SET_4": {"htf": "4h", "mtf": "1h", "ltf": "15m", "style": "Intraday"},
    "SET_5": {"htf": "1h", "mtf": "15m", "ltf": "5m", "style": "Short-Term Intraday"},
    "SET_6": {"htf": "15m", "mtf": "5m", "ltf": "1m", "style": "Scalping"},
}

# Chronological split fractions applied PER-STREAM on its own overlap window.
# This is future-proof: as 1m/5m history grows, splits automatically widen.
SPLIT_DEV = 0.60
SPLIT_VAL = 0.20
# remainder 0.20 -> OOS

# Realistic trading assumptions (do NOT weaken to manufacture edge)
RISK_PCT = 0.01
TAKER_FEE_PCT = 0.00075   # 7.5 bps Binance VIP0 taker
MAKER_FEE_PCT = 0.00020   # 2 bps maker (only used if limit-fill variant enabled)
SLIPPAGE_PCT = 0.00030    # 3 bps adverse slippage on market fills
SPREAD_PCT = 0.00010      # 1 bp spread drag
# Entries are market (taker + slippage + half-spread); exits market.

# Search space for target multiples — realistic 1.5R..3.0R, NOT 4R/6R.
# Rationale: 4R/6R firewalls reject >98% of setups and leave N<30 (see
# STRUCTURAL_REGIME_RESEARCH_REPORT: 5246 rejections -> 77 trades).
TARGET_R_GRID = [1.5, 2.0, 2.5, 3.0]
ATR_STOP_GRID = [1.5, 2.0, 2.5, 3.0]

# Institutional promotion gates (research-only; live capital stays $0)
MIN_TRADES_DEV = 30
MIN_TRADES_VAL = 20
MIN_TRADES_OOS = 20
MIN_EXPECTANCY_R = 0.05      # net expectancy per trade after ALL costs
MIN_PROFIT_FACTOR = 1.10
MAX_DD_R = 30.0
COST_SHOCK_MULT = 1.5        # edge must survive +50% fees+slippage
WFR_MIN = 0.50               # OOS/DEV expectancy retention (relaxed from 0.70 for discovery; 0.70 required for promotion)
