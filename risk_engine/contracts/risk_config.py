"""
Product 03 — Risk Engine: Risk Configuration & Research Mode Contract
Enables explicit research configuration capability without modifying production defaults.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    """
    Configuration parameters for the Risk Firewall.
    Default settings represent strict production safety limits.
    """
    max_risk_fraction: float = 0.01          # <= 1.0% risk per trade
    min_rr_floor: float = 4.0               # >= 4.0 R:R threshold
    enable_circuit_breakers: bool = True    # 3% daily, 6% weekly, 10% systemic circuit breakers
    enable_exposure_limits: bool = True     # Max open positions and portfolio exposure limits
    enable_news_filter: bool = True         # Scheduled high-impact news lockout overlay
