"""
Product 04 — Research Laboratory: Causal Multi-Timeframe Replayer
Coordinates the end-to-end execution of P01 (Market Intelligence), P02 (Strategy Lifecycle),
and P03 (Risk Firewall) in a strict, zero-lookahead, point-in-time chronological simulation.
"""

from typing import List, Dict, Any, Optional
from market_intelligence.primitives import Candle
from market_intelligence.coordinator import LanguageCoordinator
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from strategy_engine.contracts.strategy_state import CandidateState, PositionState
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from research.replayer.timeframe_aligner import TimeframeAligner, TimeframeSet
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
        enable_mtf_trailing: bool = True
    ):
        self.timeframe_set: TimeframeSet = TimeframeAligner.get_set(timeframe_set_id)
        self.initial_balance = initial_balance
        self.enable_mtf_trailing = enable_mtf_trailing
        
        self.language_coordinator = LanguageCoordinator(buffer_size=300)
        self.strategy_coordinator = StrategyCoordinator()
        self.execution_simulator = ExecutionSimulator(
            maker_fee_rate=maker_fee_rate,
            taker_fee_rate=taker_fee_rate,
            slippage_bps=slippage_bps
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
                # 3. Compute deterministic Market Intelligence state (P01)
                htf_state = self.language_coordinator.run(htf_slice, symbol=symbol, timeframe=self.timeframe_set.htf)
                mtf_state = self.language_coordinator.run(mtf_slice, symbol=symbol, timeframe=self.timeframe_set.mtf)
                ltf_state = self.language_coordinator.run(ltf_slice, symbol=symbol, timeframe=self.timeframe_set.ltf)

                # 4. Evaluate Strategy Lifecycle Engine (P02)
                trade_plans = self.strategy_coordinator.evaluate(htf_state, mtf_state, ltf_state)

                # 5. Process emitted trade plans through Risk Firewall (P03)
                for plan in trade_plans:
                    # Case A: New Entry Proposal
                    if plan.status == CandidateState.ENTERED.value:
                        account_state = AccountState(
                            current_equity=self.ledger.current_equity,
                            starting_equity=self.ledger.initial_equity,
                            peak_equity=self.ledger.peak_equity,
                            current_daily_drawdown=0.0,
                            current_weekly_drawdown=0.0,
                            open_positions_count=len(self.ledger.get_active_trades()),
                            active_symbols=[t.symbol for t in self.ledger.get_active_trades()]
                        )

                        risk_result = RiskCoordinator.evaluate(plan, account_state)

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

            except Exception as e:
                # Isolate unexpected calculation exceptions to avoid aborting the entire replay stream
                continue

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
            "equity_curve": self.ledger.equity_curve
        }
