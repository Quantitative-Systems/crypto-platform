"""Cross-Market State Engine: Multi-Asset Context, Lead-Lag, and Divergence.

Monitors macro assets (DXY, 10Y Yields, SPX, NDX, Gold, Oil, VIX) alongside crypto-native
flows (ETF net inflows, stablecoin supply changes) to evaluate cross-asset transmission.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class CrossMarketSnapshot:
    """Multi-asset environment snapshot at timestamp t."""
    timestamp_ms: int
    dxy_level: float = 104.0
    dxy_change_pct_24h: float = 0.0
    ust_10y_yield: float = 4.25
    ust_10y_change_bps_24h: float = 0.0
    spx_level: float = 5500.0
    spx_change_pct_24h: float = 0.0
    ndx_level: float = 19500.0
    ndx_change_pct_24h: float = 0.0
    vix_level: float = 16.5
    gold_level: float = 2400.0
    oil_level: float = 78.0
    etf_net_inflow_usd_24h: float = 0.0
    stablecoin_supply_change_pct_7d: float = 0.0
    
    # Statistical relationships
    btc_spx_correlation_30d: float = 0.45
    btc_dxy_correlation_30d: float = -0.55
    btc_gold_correlation_30d: float = 0.20
    btc_eth_correlation_30d: float = 0.88
    
    # Relative Strength & Divergence
    relative_strength_rank: Dict[str, float] = field(default_factory=dict) # e.g. {"SOL": 1.2, "BTC": 1.0, "ETH": 0.85}
    active_divergence: Optional[str] = None # e.g. "BULLISH_CRYPTO_EQUITIES_DIVERGENCE"
    macro_transmission_bias: str = "NEUTRAL" # "BULLISH_RISK_ON", "BEARISH_LIQUIDITY_CONTRACTION", "NEUTRAL"
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_ms": self.timestamp_ms,
            "dxy_level": self.dxy_level,
            "dxy_change_pct_24h": self.dxy_change_pct_24h,
            "ust_10y_yield": self.ust_10y_yield,
            "ust_10y_change_bps_24h": self.ust_10y_change_bps_24h,
            "spx_level": self.spx_level,
            "spx_change_pct_24h": self.spx_change_pct_24h,
            "ndx_level": self.ndx_level,
            "ndx_change_pct_24h": self.ndx_change_pct_24h,
            "vix_level": self.vix_level,
            "gold_level": self.gold_level,
            "oil_level": self.oil_level,
            "etf_net_inflow_usd_24h": self.etf_net_inflow_usd_24h,
            "stablecoin_supply_change_pct_7d": self.stablecoin_supply_change_pct_7d,
            "btc_spx_correlation_30d": self.btc_spx_correlation_30d,
            "btc_dxy_correlation_30d": self.btc_dxy_correlation_30d,
            "btc_eth_correlation_30d": self.btc_eth_correlation_30d,
            "relative_strength_rank": self.relative_strength_rank,
            "active_divergence": self.active_divergence,
            "macro_transmission_bias": self.macro_transmission_bias,
            "meta": self.meta,
        }


class CrossMarketStateEngine:
    """Calculates cross-asset metrics, correlations, and macro transmission bias."""

    def __init__(self, correlation_window_bars: int = 30):
        self.correlation_window_bars = correlation_window_bars

    def evaluate_cross_market(
        self,
        timestamp_ms: int,
        macro_quotes: Optional[Dict[str, Any]] = None,
        crypto_returns: Optional[Dict[str, np.ndarray]] = None,
        macro_returns: Optional[Dict[str, np.ndarray]] = None,
    ) -> CrossMarketSnapshot:
        """Construct full cross-market snapshot with rolling statistics."""
        quotes = macro_quotes or {}
        
        dxy = quotes.get("dxy", 104.0)
        dxy_chg = quotes.get("dxy_change_24h", 0.0)
        ust10y = quotes.get("ust_10y", 4.25)
        ust10y_bps = quotes.get("ust_10y_change_bps_24h", 0.0)
        spx = quotes.get("spx", 5500.0)
        spx_chg = quotes.get("spx_change_24h", 0.0)
        ndx = quotes.get("ndx", 19500.0)
        ndx_chg = quotes.get("ndx_change_24h", 0.0)
        vix = quotes.get("vix", 16.5)
        gold = quotes.get("gold", 2400.0)
        oil = quotes.get("oil", 78.0)
        etf_flows = quotes.get("etf_net_inflow_usd_24h", 0.0)
        stablecoin_chg = quotes.get("stablecoin_supply_change_pct_7d", 0.0)

        # Compute rolling correlations if return series are supplied
        btc_spx_corr = self._calc_corr(
            crypto_returns.get("BTC") if crypto_returns else None,
            macro_returns.get("SPX") if macro_returns else None,
            default=0.45,
        )
        btc_dxy_corr = self._calc_corr(
            crypto_returns.get("BTC") if crypto_returns else None,
            macro_returns.get("DXY") if macro_returns else None,
            default=-0.55,
        )
        btc_eth_corr = self._calc_corr(
            crypto_returns.get("BTC") if crypto_returns else None,
            crypto_returns.get("ETH") if crypto_returns else None,
            default=0.88,
        )

        # Relative Strength calculation
        rs_ranks: Dict[str, float] = {}
        if crypto_returns:
            for sym, rets in crypto_returns.items():
                if len(rets) > 0:
                    rs_ranks[sym] = float(np.sum(rets[-self.correlation_window_bars:]))
            # Normalize around BTC = 1.0 if BTC exists
            btc_val = rs_ranks.get("BTC", 0.0)
            if abs(btc_val) > 1e-6:
                rs_ranks = {k: round(v / btc_val, 3) for k, v in rs_ranks.items()}

        # Evaluate Macro Transmission Bias
        macro_bias = "NEUTRAL"
        if dxy_chg < -0.3 and spx_chg > 0.5 and vix < 18.0 and etf_flows >= 0:
            macro_bias = "BULLISH_RISK_ON"
        elif dxy_chg > 0.5 and ust10y_bps > 5.0 and spx_chg < -0.5:
            macro_bias = "BEARISH_LIQUIDITY_CONTRACTION"

        # Divergence Detection
        active_div = None
        if spx_chg > 1.0 and quotes.get("btc_change_24h", 0.0) < -1.0:
            active_div = "BEARISH_CRYPTO_EQUITIES_DIVERGENCE"
        elif spx_chg < -1.0 and quotes.get("btc_change_24h", 0.0) > 1.0:
            active_div = "BULLISH_CRYPTO_EQUITIES_DIVERGENCE"

        return CrossMarketSnapshot(
            timestamp_ms=timestamp_ms,
            dxy_level=dxy,
            dxy_change_pct_24h=dxy_chg,
            ust_10y_yield=ust10y,
            ust_10y_change_bps_24h=ust10y_bps,
            spx_level=spx,
            spx_change_pct_24h=spx_chg,
            ndx_level=ndx,
            ndx_change_pct_24h=ndx_chg,
            vix_level=vix,
            gold_level=gold,
            oil_level=oil,
            etf_net_inflow_usd_24h=etf_flows,
            stablecoin_supply_change_pct_7d=stablecoin_chg,
            btc_spx_correlation_30d=btc_spx_corr,
            btc_dxy_correlation_30d=btc_dxy_corr,
            btc_eth_correlation_30d=btc_eth_corr,
            relative_strength_rank=rs_ranks,
            active_divergence=active_div,
            macro_transmission_bias=macro_bias,
        )

    def _calc_corr(
        self,
        s1: Optional[np.ndarray],
        s2: Optional[np.ndarray],
        default: float,
    ) -> float:
        if s1 is None or s2 is None:
            return default
        min_len = min(len(s1), len(s2), self.correlation_window_bars)
        if min_len < 10:
            return default
        a1 = s1[-min_len:]
        a2 = s2[-min_len:]
        std1 = np.std(a1)
        std2 = np.std(a2)
        if std1 < 1e-8 or std2 < 1e-8:
            return default
        corr = float(np.corrcoef(a1, a2)[0, 1])
        return default if np.isnan(corr) else corr
