"""Crypto Engine — Certified Institutional Invariants.

Enforces physical and mathematical market laws:
1. Dynamic 1.0% Account Risk Sizing per trade.
2. Max 3.0% Concurrent Portfolio Heat across all active sets.
3. Minimum 1:4.0R Destination Target for core swings.
4. 1.5x ATR Volatility Stop Floor (protects micro sets 4 & 5 from fee drag).
5. Dynamic +1.5R Break-Even Ratchet (locks entry + 0.1R fee buffer).
6. Monotonic MTF Trailing Stop (locks profits behind confirmed swings).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class InstitutionalRiskInvariants:
    RISK_PER_TRADE_PCT: float = 0.01          # 1% equity risk per position
    MAX_PORTFOLIO_HEAT_PCT: float = 0.03      # 3% aggregate heat ceiling
    MIN_TARGET_R: float = 4.0                 # 1:4.0R reward-to-risk floor
    BREAK_EVEN_R_THRESHOLD: float = 1.5       # +1.5R triggers BE ratchet
    BREAK_EVEN_BUFFER_R: float = 0.1          # Entry + 0.1R buffer for fees
    ATR_VOLATILITY_STOP_MULTIPLIER: float = 1.5  # 1.5x ATR minimum stop floor
    TAKER_FEE_BPS: float = 5.0                # 5 bps institutional tier
    SLIPPAGE_BPS: float = 2.0                 # 2 bps modeled execution slippage
