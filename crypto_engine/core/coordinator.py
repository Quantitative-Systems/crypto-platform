"""Crypto Engine — Unified Multi-Horizon Master Coordinator.

Combines all filter-passed proven trading theories:
1. Canonical 3 Primitives (Market Structure, KeyZones, Dealing Range Phases)
2. Invariant Top-Down Cauchy Transmission across 5 Sets
3. Dual-Phase Dealing Range Baton (Pullback Riding + Continuation Riding)
4. Tri-Strategy Fractal Confluence (HTF Scalp + MTF Momentum + LTF Swing = 1 Trade)
5. Candle-Relative Scale Invariance (Style defined by candle geometry)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from market_model.cascading_fractal_coordinator import (
    CascadingFractalCoordinator,
    CascadingSignalCandidate,
    MacroPhaseBaton,
)
from market_model.contracts import StructuralBreakType, TrendDirection
from crypto_engine.core.invariants import InstitutionalRiskInvariants


class MasterFractalCoordinator(CascadingFractalCoordinator):
    """Unified Master Coordinator combining all verified institutional alpha models."""

    def __init__(
        self,
        min_target_r: float = InstitutionalRiskInvariants.MIN_TARGET_R,
        risk_per_trade_pct: float = InstitutionalRiskInvariants.RISK_PER_TRADE_PCT,
        account_equity_usd: float = 100_000.0,
        enable_tri_strategy_confluence: bool = True,
    ):
        super().__init__(
            min_target_r=min_target_r,
            risk_per_trade_pct=risk_per_trade_pct,
            account_equity_usd=account_equity_usd,
        )
        self.enable_tri_strategy_confluence = enable_tri_strategy_confluence

    def scan_master_signals(
        self,
        symbol: str,
        target_set: str,
        all_data: Dict[str, Dict[str, np.ndarray]],
        only_latest_bar: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Dict[int, float]]:
        """Scans signals evaluating standard cascading + tri-strategy confluence."""
        # 1. Base cascading signals
        cands, trailing_map = self.scan_cascading_candidates(
            symbol=symbol,
            target_set=target_set,
            all_data=all_data,
            only_latest_bar=only_latest_bar,
        )

        if not self.enable_tri_strategy_confluence or not cands:
            return cands, trailing_map

        # Tag high-conviction tri-strategy candidates
        cfg = self.TIMEFRAME_SETS[target_set]
        htf_tf = cfg["htf"]
        mtf_tf = cfg["mtf"]

        if htf_tf in all_data and mtf_tf in all_data:
            htf_state = getattr(self, "_last_htf_state", None)
            mtf_state = getattr(self, "_last_mtf_state", None)
            if htf_state and mtf_state:
                for cand in cands:
                    # Confluence check: active HTF zone + MTF trend alignment
                    has_htf_zone = len(htf_state.zones.order_blocks) > 0 or len(htf_state.zones.fair_value_gaps) > 0
                    has_mtf_align = (
                        (cand["direction"] == 1 and mtf_state.structure.external_trend == TrendDirection.BULLISH) or
                        (cand["direction"] == -1 and mtf_state.structure.external_trend == TrendDirection.BEARISH)
                    )
                    if has_htf_zone and has_mtf_align:
                        cand["is_tri_strategy_composite"] = True
                        cand["confluence_tier"] = "TIER_1_SUPER_CONFLUENCE"

        return cands, trailing_map
