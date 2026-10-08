"""STRATA — Strategy Library & Catalog Architecture.

Indexes and governs strategies across all three domains:
- Domain A: KING (Protected core)
- Domain B: STRATA BUILT-IN (Validated crypto library)
- Domain C: USER STRATEGIES (Tenant-isolated, formalized in Strategy Lab)

Also catalogs status: RESEARCH, QUALIFIED, QUARANTINED.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from strategy.lab.strategy_specification import StrategyDomain, StrategySpecification
from strategy.lifecycle.strategy_lifecycle import (
    LifecycleStage,
    StrategyEvidence,
    StrategyVerdict,
)

logger = logging.getLogger(__name__)


@dataclass
class StrategyCatalogEntry:
    strategy_id: str
    name: str
    description: str
    domain: StrategyDomain
    status: str  # QUALIFIED, RESEARCH, QUARANTINED, DEPLOYABLE, etc.
    assets: List[str]
    timeframes: List[str]
    evidence: StrategyEvidence
    category: str = "SWING"  # TRADING, INVESTING, POSITION, SWING, INTRADAY, SCALPING, HEDGING, ARBITRAGE, RESEARCH
    lifecycle_state: str = "PAPER"  # RESEARCH, BACKTESTED, OOS VALIDATED, FORWARD TESTING, PAPER, DEMO, QUALIFIED
    entry_logic: str = "Market structure shift + confirmed pullback"
    stop_logic: str = "Structural invalidation point"
    target_logic: str = ">= 4.0R minimum target floor"
    risk_per_trade_pct: float = 1.0
    is_featured: bool = False
    version: str = "1.0.0"
    tenant_id: str = "system"
    lineage_parent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain.value,
            "status": self.status,
            "category": self.category,
            "lifecycle_state": self.lifecycle_state,
            "entry_logic": self.entry_logic,
            "stop_logic": self.stop_logic,
            "target_logic": self.target_logic,
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "is_featured": self.is_featured,
            "assets": self.assets,
            "timeframes": self.timeframes,
            "evidence": self.evidence.to_dict(),
            "version": self.version,
            "tenant_id": self.tenant_id,
            "lineage_parent": self.lineage_parent,
        }


class StrategyLibraryManager:
    """Manages the centralized and tenant-partitioned strategy library."""

    def __init__(self):
        self._entries: Dict[str, StrategyCatalogEntry] = {}
        self._seed_canonical_strategies()

    def _seed_canonical_strategies(self) -> None:
        """Seeds Domain A (KING) and Domain B (BUILT-IN) strategies."""
        # 1. DOMAIN A: KING ENGINE
        king_evidence = StrategyEvidence(
            current_stage=LifecycleStage.FORWARD,
            verdict=StrategyVerdict.QUALIFIED,
            total_trades=9608,
            net_r=5554.0,
            expectancy_r=0.888,
            profit_factor=4.918,
            win_rate=0.672,
            max_drawdown_r=10.89,
            tail_risk_cvar=1.20,
            friction_multiplier_survival=5.0,
            oos_expectancy_r=0.745,
            parameter_stability_score=0.96,
            evidence_notes=[
                "Protected STRATA King Engine (Phase Q.2 / Phase R).",
                "7-Timeframe continuous ladder (1M to 3M) across 5 overlapping sets.",
                "Minimum 4.0R target floor strictly enforced.",
            ],
        )
        self.register_entry(
            StrategyCatalogEntry(
                strategy_id="STRATA_KING_ENGINE",
                name="STRATA King Engine",
                description="Protected Q.2 / Phase R Unified Fractal Market Model Core",
                domain=StrategyDomain.DOMAIN_A_KING,
                status="PROTECTED_CORE",
                category="POSITION",
                lifecycle_state="QUALIFIED",
                entry_logic="Causal 7-timeframe fractal alignment + Q.2 confidence >= 0.50",
                stop_logic="Opposing HTF/MTF fractal structure invalidation",
                target_logic=">= 4.0R strict mathematical destination floor",
                risk_per_trade_pct=1.0,
                is_featured=True,
                assets=["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
                timeframes=["1M", "1w", "1d", "4h", "1h", "15m", "3m"],
                evidence=king_evidence,
                version="1.0.0-canonical",
                tenant_id="system",
            )
        )

        # 2. DOMAIN B: BUILT-IN STRATEGIES
        built_ins = [
            (
                "STRATA_TREND_PULLBACK",
                "STRATA Multi-TF Trend Pullback",
                "Captures discount/premium equilibrium pullbacks in aligned market trends with 4R target floor.",
                "SWING",
                "PAPER",
                "PAPER_ELIGIBLE",
                True,
                ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                ["1w", "1d", "4h"],
                StrategyEvidence(
                    current_stage=LifecycleStage.PAPER,
                    verdict=StrategyVerdict.PAPER_ELIGIBLE,
                    total_trades=320,
                    net_r=142.0,
                    expectancy_r=0.443,
                    profit_factor=2.45,
                    win_rate=0.51,
                    max_drawdown_r=14.2,
                    friction_multiplier_survival=3.0,
                    evidence_notes=["Passed walk-forward cross validation on BTC and ETH."],
                ),
            ),
            (
                "STRATA_MOMENTUM_BREAKOUT",
                "STRATA Liquidity Sweep Breakout",
                "Trades expansion moves following liquidity pool sweeps and MSS confirmation.",
                "INTRADAY",
                "PAPER",
                "PAPER_ELIGIBLE",
                True,
                ["BTCUSDT", "SOLUSDT"],
                ["4h", "1h", "15m"],
                StrategyEvidence(
                    current_stage=LifecycleStage.PAPER,
                    verdict=StrategyVerdict.PAPER_ELIGIBLE,
                    total_trades=210,
                    net_r=88.5,
                    expectancy_r=0.421,
                    profit_factor=2.18,
                    win_rate=0.48,
                    max_drawdown_r=16.8,
                    friction_multiplier_survival=2.5,
                    evidence_notes=["High volatility expansion capture model."],
                ),
            ),
            (
                "STRATA_REGIME_ADAPTIVE",
                "STRATA Volatility Regime Adaptive",
                "Dynamically toggles between continuation and range modes based on realized volatility.",
                "TRADING",
                "FORWARD TESTING",
                "FORWARD_VALIDATION_ELIGIBLE",
                True,
                ["BTCUSDT", "ETHUSDT"],
                ["1d", "4h"],
                StrategyEvidence(
                    current_stage=LifecycleStage.FORWARD,
                    verdict=StrategyVerdict.FORWARD_VALIDATION_ELIGIBLE,
                    total_trades=180,
                    net_r=92.0,
                    expectancy_r=0.511,
                    profit_factor=2.65,
                    win_rate=0.54,
                    max_drawdown_r=11.5,
                    friction_multiplier_survival=3.2,
                    evidence_notes=["Regime-switching filter prevents whipsaws during consolidation."],
                ),
            ),
            (
                "STRATA_MICRO_SCALP",
                "STRATA LTF Micro Confirmation Scalper",
                "Executes on 3m/15m lower-timeframe order flow sweeps following 1h bias confirmation.",
                "SCALPING",
                "RESEARCH",
                "NOT_READY",
                False,
                ["BTCUSDT", "ETHUSDT"],
                ["1h", "15m", "3m"],
                StrategyEvidence(
                    current_stage=LifecycleStage.RESEARCH,
                    verdict=StrategyVerdict.NOT_READY,
                    total_trades=540,
                    net_r=128.0,
                    expectancy_r=0.237,
                    profit_factor=1.82,
                    win_rate=0.58,
                    max_drawdown_r=22.1,
                    friction_multiplier_survival=1.8,
                    evidence_notes=["High execution sensitivity; requires sub-50ms latency."],
                ),
            ),
            (
                "STRATA_BASIS_ARBITRAGE",
                "STRATA Spot-Perp Cash and Carry Basis",
                "Captures structural perpetual funding rate anomalies between spot index and futures.",
                "ARBITRAGE",
                "DEMO",
                "PAPER_ELIGIBLE",
                False,
                ["BTCUSDT", "ETHUSDT"],
                ["1d", "8h"],
                StrategyEvidence(
                    current_stage=LifecycleStage.PAPER,
                    verdict=StrategyVerdict.PAPER_ELIGIBLE,
                    total_trades=84,
                    net_r=62.0,
                    expectancy_r=0.738,
                    profit_factor=4.10,
                    win_rate=0.88,
                    max_drawdown_r=4.2,
                    friction_multiplier_survival=4.5,
                    evidence_notes=["Delta-neutral market structure model."],
                ),
            ),
            (
                "STRATA_CROSS_HEDGE",
                "STRATA Macro Beta Correlation Hedger",
                "Maintains systemic downside capital protection via inverse dynamic positioning.",
                "HEDGING",
                "RESEARCH",
                "NOT_READY",
                False,
                ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                ["1w", "1d"],
                StrategyEvidence(
                    current_stage=LifecycleStage.RESEARCH,
                    verdict=StrategyVerdict.NOT_READY,
                    total_trades=42,
                    net_r=18.0,
                    expectancy_r=0.428,
                    profit_factor=2.05,
                    win_rate=0.52,
                    max_drawdown_r=8.5,
                    friction_multiplier_survival=2.2,
                    evidence_notes=["Tail risk defensive dampener."],
                ),
            ),
            (
                "STRATA_MACRO_ACCUMULATION",
                "STRATA HTF Value Accumulation",
                "Long-term structural accumulation targeting macro cycle expansions.",
                "INVESTING",
                "BACKTESTED",
                "FORWARD_VALIDATION_ELIGIBLE",
                False,
                ["BTCUSDT", "ETHUSDT"],
                ["1M", "1w", "1d"],
                StrategyEvidence(
                    current_stage=LifecycleStage.OOS,
                    verdict=StrategyVerdict.FORWARD_VALIDATION_ELIGIBLE,
                    total_trades=68,
                    net_r=245.0,
                    expectancy_r=3.60,
                    profit_factor=5.20,
                    win_rate=0.62,
                    max_drawdown_r=18.5,
                    friction_multiplier_survival=5.0,
                    evidence_notes=["Macro cycle multi-year hold model."],
                ),
            ),
        ]

        for s_id, name, desc, cat, lstate, status, feat, assets, tfs, ev in built_ins:
            self.register_entry(
                StrategyCatalogEntry(
                    strategy_id=s_id,
                    name=name,
                    description=desc,
                    domain=StrategyDomain.DOMAIN_B_BUILT_IN,
                    status=status,
                    category=cat,
                    lifecycle_state=lstate,
                    is_featured=feat,
                    assets=assets,
                    timeframes=tfs,
                    evidence=ev,
                    version="1.0.0",
                    tenant_id="system",
                )
            )

    def register_entry(self, entry: StrategyCatalogEntry) -> None:
        self._entries[entry.strategy_id] = entry

    def get_entry(self, strategy_id: str) -> Optional[StrategyCatalogEntry]:
        return self._entries.get(strategy_id)

    def list_entries(
        self,
        domain: Optional[StrategyDomain] = None,
        tenant_id: Optional[str] = None,
    ) -> List[StrategyCatalogEntry]:
        """Lists entries filtered by domain and tenant visibility."""
        results = []
        for e in self._entries.values():
            # Domain filter
            if domain and e.domain != domain:
                continue

            # Tenant visibility: system entries are public to all, user entries are private to tenant
            if e.tenant_id == "system" or (tenant_id and e.tenant_id == tenant_id):
                results.append(e)

        return results
