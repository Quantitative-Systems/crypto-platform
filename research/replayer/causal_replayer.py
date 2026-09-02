"""
Product 04 — Research Laboratory: Causal Multi-Timeframe Replayer
Coordinates the end-to-end execution of P01 (Market Intelligence), P02 (Strategy Lifecycle),
and P03 (Risk Firewall) in a strict, zero-lookahead, point-in-time chronological simulation.
"""

from typing import List, Dict, Any, Optional
from market_intelligence.primitives import Candle
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.classifiers.regime_filter import RegimeFilter
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from strategy_engine.contracts.strategy_state import CandidateState, PositionState
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.contracts.risk_config import RiskConfig
from research.replayer.timeframe_aligner import (
    TimeframeAligner, TimeframeSet, TIMEFRAME_DURATIONS_MS, TIMEFRAME_DURATIONS_SEC
)
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.simulation.execution_simulator import ExecutionSimulator
from research.metrics.metrics_engine import MetricsEngine
from research.metrics.exit_attribution import ExitAttributionEngine
from research.analytics.failure_analyzer import FailureAnalyzer


class CausalReplayer:
    """
    Replays multi-timeframe candle streams causally without lookahead.
    """

    def __init__(
        self,
        timeframe_set_id: str = "SET_4",
        initial_balance: float = 10000.0,
        maker_fee_rate: float = 0.0000,
        taker_fee_rate: float = 0.0005,
        slippage_bps: float = 5.0,
        enable_mtf_trailing: bool = True,
        enable_profit_lock: bool = False,
        lockin_r: float = 1.0,
        giveback_r: float = 0.75,
        enable_regime_filter: bool = False,
        cache_htf_mtf: bool = True,
        risk_config: Optional[RiskConfig] = None,
        htf_context_filter: Optional[str] = None,
        hypothesis: Optional[Any] = None
    ):
        self.timeframe_set: TimeframeSet = TimeframeAligner.get_set(timeframe_set_id)
        self.initial_balance = initial_balance
        self.enable_mtf_trailing = enable_mtf_trailing
        self.enable_profit_lock = enable_profit_lock
        self.lockin_r = lockin_r
        self.giveback_r = giveback_r
        self.enable_regime_filter = enable_regime_filter
        self.risk_config = risk_config
        # RESEARCH ENGINE PERFORMANCE FLAG (no trading-logic impact):
        # When True, the point-in-time HTF/MTF incremental state is cached and only
        # recomputed when a NEW higher/middle timeframe candle becomes causally
        # visible (i.e. closes). This preserves identical canonical decisions while
        # removing the redundant full-window P01 rebuild on every LTF tick.
        # When False, the replayer reproduces the original recompute-every-tick path
        # and is used as the reference for equivalence auditing.
        self.cache_htf_mtf = cache_htf_mtf

        # Incremental P01 state caches (keyed by the last visible candle timestamp).
        self._htf_cache: Dict[str, Any] = {"key": None, "state": None}
        self._mtf_cache: Dict[str, Any] = {"key": None, "state": None}

        # P01 invocation counters for performance benchmarking / auditability.
        self._htf_runs: int = 0
        self._mtf_runs: int = 0
        self._ltf_runs: int = 0

        self.language_coordinator = LanguageCoordinator(buffer_size=300)
        self.regime_filter = RegimeFilter(enable_filter=True) if self.enable_regime_filter else None
        self.strategy_coordinator = StrategyCoordinator(
            enable_mtf_trailing=self.enable_mtf_trailing,
            enable_profit_lock=self.enable_profit_lock,
            lockin_r=self.lockin_r,
            giveback_r=self.giveback_r,
            regime_filter=self.regime_filter,
            htf_context_filter=htf_context_filter,
            hypothesis=hypothesis
        )
        self.execution_simulator = ExecutionSimulator(
            maker_fee_rate=maker_fee_rate,
            taker_fee_rate=taker_fee_rate,
            slippage_bps=slippage_bps,
            enable_profit_lock=self.enable_profit_lock,
            lockin_r=self.lockin_r,
            giveback_r=self.giveback_r
        )
        self.ledger = TradeLedger(initial_equity=initial_balance)

    def run(
        self,
        symbol: str,
        htf_candles: List[Candle],
        mtf_candles: List[Candle],
        ltf_candles: List[Candle],
        min_lookback_bars: int = 15
    ) -> Dict[str, Any]:
        """
        Runs the chronological event loop across historical candle data.
        """
        if len(ltf_candles) < min_lookback_bars:
            metrics = MetricsEngine.calculate_metrics([], self.ledger)
            return {
                "metrics": metrics,
                "exit_attribution": ExitAttributionEngine.analyze([]),
                "failure_modes": FailureAnalyzer.classify_failure_modes([]),
                "closed_trades": [],
                "equity_curve": self.ledger.equity_curve
            }

        # Reset incremental caches at the start of a fresh replay stream.
        self._htf_cache = {"key": None, "state": None}
        self._mtf_cache = {"key": None, "state": None}
        
        rejected_candidates = []

        # Step chronologically forward through LTF candles
        for i in range(min_lookback_bars, len(ltf_candles)):
            current_bar = ltf_candles[i]
            decision_timestamp = current_bar.timestamp

            # 1. Process forward candle against existing orders (fills, stops, targets)
            self.execution_simulator.process_candle(current_bar, self.ledger)

            # 2. Extract point-in-time visible candle slices for all 3 horizons
            ltf_slice = ltf_candles[max(0, i - 150):i + 1]
            mtf_slice = TimeframeAligner.filter_visible_candles(
                mtf_candles, decision_timestamp, self.timeframe_set.mtf, buffer_size=100
            )
            htf_slice = TimeframeAligner.filter_visible_candles(
                htf_candles, decision_timestamp, self.timeframe_set.htf, buffer_size=80
            )

            # Require minimum historical depth on all 3 horizons before evaluating strategy
            if len(htf_slice) < 5 or len(mtf_slice) < 5 or len(ltf_slice) < 5:
                continue

            try:
                # 3. Compute deterministic Market Intelligence state (P01).
                #    HTF/MTF state is only rebuilt when a NEW higher-timeframe candle
                #    becomes causally visible (its closing timestamp enters the window).
                #    Within a window the higher-timeframe state is unchanged, so the
                #    cached payload is reused -> identical decisions, fewer rebuilds.
                if self.cache_htf_mtf:
                    htf_key = htf_slice[-1].timestamp if htf_slice else None
                    if self._htf_cache["key"] != htf_key:
                        htf_state = self.language_coordinator.run(htf_slice, symbol=symbol, timeframe=self.timeframe_set.htf)
                        self._htf_cache = {"key": htf_key, "state": htf_state}
                        self._htf_runs += 1
                    else:
                        htf_state = self._htf_cache["state"]
                else:
                    htf_state = self.language_coordinator.run(htf_slice, symbol=symbol, timeframe=self.timeframe_set.htf)
                    self._htf_runs += 1

                if self.cache_htf_mtf:
                    mtf_key = mtf_slice[-1].timestamp if mtf_slice else None
                    if self._mtf_cache["key"] != mtf_key:
                        mtf_state = self.language_coordinator.run(mtf_slice, symbol=symbol, timeframe=self.timeframe_set.mtf)
                        self._mtf_cache = {"key": mtf_key, "state": mtf_state}
                        self._mtf_runs += 1
                    else:
                        mtf_state = self._mtf_cache["state"]
                else:
                    mtf_state = self.language_coordinator.run(mtf_slice, symbol=symbol, timeframe=self.timeframe_set.mtf)
                    self._mtf_runs += 1

                # LTF always recomputes: each LTF tick closes a new bar (the strategy tick).
                ltf_state = self.language_coordinator.run(ltf_slice, symbol=symbol, timeframe=self.timeframe_set.ltf)
                self._ltf_runs += 1

                # 4. Evaluate Strategy Lifecycle Engine (P02)
                trade_plans = self.strategy_coordinator.evaluate(htf_state, mtf_state, ltf_state)

                # Synchronize MTF Structural Trailing Stop with Ledger
                if self.enable_mtf_trailing:
                    for t_id, active_plan in self.strategy_coordinator.active_manager.active_trades.items():
                        self.ledger.update_trailing_stop(t_id, active_plan.stop_invalidation_price)

                # 5. Process emitted trade plans through Risk Firewall (P03)
                for plan in trade_plans:
                    # Case A: New Entry Proposal
                    if plan.status == CandidateState.ENTERED.value:
                        account_state = AccountState(
                            current_equity=self.ledger.current_equity,
                            peak_equity=self.ledger.peak_equity,
                            daily_pnl=0.0,
                            weekly_pnl=0.0,
                            open_position_count=len(self.ledger.get_active_trades()),
                            active_assets={t.symbol: 1.0 for t in self.ledger.get_active_trades()}
                        )

                        risk_result = RiskCoordinator.evaluate(plan, account_state, config=self.risk_config)

                        if isinstance(risk_result, RiskApprovedPlan):
                            simulated_trade = SimulatedTrade(
                                trade_id=plan.trade_plan_id,
                                hypothesis_id=plan.hypothesis_id,
                                symbol=symbol,
                                timeframe_set=self.timeframe_set.set_id,
                                directional_permission=plan.directional_permission,
                                setup_timestamp=plan.setup_timestamp,
                                entry_price=plan.entry_price,
                                initial_stop_price=plan.stop_invalidation_price,
                                current_stop_price=plan.stop_invalidation_price,
                                target_price=plan.target_price,
                                position_units=risk_result.position_units,
                                dollar_risk=risk_result.dollar_risk,
                                raw_rr=plan.raw_rr,
                                status="PENDING_ENTRY",
                                metadata={"structural_provenance": plan.structural_provenance}
                            )
                            self.ledger.record_pending_trade(simulated_trade)

                    # Case B: Active Trade Trailing Stop / Exit Management
                    elif plan.position_status == PositionState.MTF_TRAIL_EXIT.value:
                        if self.enable_mtf_trailing:
                            self.execution_simulator.execute_structural_exit(
                                trade_id=plan.trade_plan_id,
                                current_market_price=ltf_state.current_price,
                                timestamp=decision_timestamp,
                                exit_reason="MTF_STRUCTURAL_TRAIL",
                                ledger=self.ledger
                            )
                    # Case C: SL/TP exits are executed by ExecutionSimulator inside the
                    # per-candle loop (adverse-first). The ActiveTradeManager may still
                    # emit TP_EXIT / LTF_SL_EXIT *plans* for trades already closed by the
                    # simulator in the same bar or on later bars (ghost plans). Those are
                    # NOT rejections and MUST NOT pollute the counterfactual funnel.
                    # Only genuinely rejected candidates (status == REJECTED) count.
                    else:
                        if plan.status == CandidateState.REJECTED.value:
                            rejected_candidates.append(plan)

            except Exception as e:
                # Isolate unexpected calculation exceptions to avoid aborting the entire replay stream
                import traceback
                traceback.print_exc()
                continue

        # Calculate suspended intervals count in the LTF stream
        is_sec = (ltf_candles[0].timestamp < 100_000_000_000) if ltf_candles else True
        durations = TIMEFRAME_DURATIONS_SEC if is_sec else TIMEFRAME_DURATIONS_MS
        expected_ltf_interval = durations.get(self.timeframe_set.ltf.upper(), 3600 if is_sec else 3600000)
        suspended_intervals_count = 0
        for idx in range(1, len(ltf_candles)):
            gap = ltf_candles[idx].timestamp - ltf_candles[idx-1].timestamp
            if gap > expected_ltf_interval:
                suspended_intervals_count += 1

        # Post-replay analytics
        closed_trades = self.ledger.closed_trades
        metrics = MetricsEngine.calculate_metrics(closed_trades, self.ledger)
        exit_attribution = ExitAttributionEngine.analyze(closed_trades)
        failure_modes = FailureAnalyzer.classify_failure_modes(closed_trades)

        return {
            "metrics": metrics,
            "exit_attribution": exit_attribution,
            "failure_modes": failure_modes,
            "closed_trades": [t.to_dict() for t in closed_trades],
            "equity_curve": self.ledger.equity_curve,
            "rejected_candidates": [p.__dict__ for p in rejected_candidates],
            "suspended_intervals_count": suspended_intervals_count,
            "replayed_candles_count": max(0, len(ltf_candles) - min_lookback_bars),
            "date_range": {
                "start": ltf_candles[0].timestamp if ltf_candles else 0,
                "end": ltf_candles[-1].timestamp if ltf_candles else 0
            },
            "engine_runs": {
                "htf": self._htf_runs,
                "mtf": self._mtf_runs,
                "ltf": self._ltf_runs,
                "ltf_ticks": max(0, len(ltf_candles) - min_lookback_bars)
            }
        }
