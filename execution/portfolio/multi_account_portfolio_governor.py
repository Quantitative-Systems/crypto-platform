"""STRATA — Phase 5: Multi-Account Portfolio Risk Governor & Sub-Account Engine.

Implements institutional multi-account management and aggregate risk safety:
1. Sub-Account Isolation:
   - Dedicated allocation per sub-account (e.g. Macro Trend, Tactical Swing, Intraday Momentum).
   - Independent equity accounting, local position tracking, and style mandate enforcement.
2. Global Aggregate Risk Invariants:
   - Total Cross-Account Portfolio Heat strictly capped at 3.0% (max 3 concurrent 1.0% risk positions).
   - Global 3.0% Daily Drawdown Circuit Breaker: If aggregate portfolio drawdown exceeds 3.0% in 24 hours,
     all new candidate entries are frozen across all sub-accounts (Fail-Closed).
3. Causal Multi-Style Routing:
   - Dispatches certified style candidates to designated isolated sub-accounts based on horizon.
4. Real-Time Factor & Risk Headroom Inspection:
   - Provides instant visibility into occupied risk budget, available headroom, and circuit breaker states.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("MultiAccountPortfolioGovernor")


@dataclass
class SubAccountState:
    account_id: str
    account_name: str
    mandate_styles: List[str]             # e.g. ["INVESTING", "POSITIONAL"]
    initial_balance_usd: float
    current_equity_usd: float
    peak_equity_usd: float
    active_risk_heat_pct: float = 0.0     # Sum of active position risks in this account
    max_account_risk_heat_pct: float = 0.02 # 2.0% max for this sub-account
    open_positions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    closed_trades_count: int = 0
    realized_pnl_usd: float = 0.0
    realized_r_total: float = 0.0
    is_halted: bool = False
    halt_reason: Optional[str] = None

    @property
    def current_drawdown_pct(self) -> float:
        if self.peak_equity_usd <= 0:
            return 0.0
        return max(0.0, ((self.peak_equity_usd - self.current_equity_usd) / self.peak_equity_usd) * 100.0)


@dataclass
class GlobalPortfolioStatus:
    total_equity_usd: float
    total_peak_equity_usd: float
    aggregate_drawdown_pct: float
    aggregate_risk_heat_pct: float
    available_risk_headroom_pct: float
    total_active_positions: int
    max_allowed_positions: int
    is_global_circuit_breaker_active: bool
    circuit_breaker_reason: Optional[str] = None
    sub_account_summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class MultiAccountPortfolioGovernor:
    """Institutional multi-sub-account risk coordinator and global circuit breaker."""

    def __init__(
        self,
        global_max_heat_pct: float = 0.03,         # 3.0% strict ceiling across entire portfolio
        global_daily_drawdown_limit_pct: float = 3.0, # 3.0% daily circuit breaker
        max_total_positions: int = 3,               # Max 3 concurrent positions overall
        live_capital_authorized: float = 0.00,      # Strictly $0.00 (fail-closed)
    ):
        self.global_max_heat_pct = global_max_heat_pct
        self.global_daily_drawdown_limit_pct = global_daily_drawdown_limit_pct
        self.max_total_positions = max_total_positions
        self.live_capital_authorized = live_capital_authorized

        # Sub-accounts
        self.sub_accounts: Dict[str, SubAccountState] = {}
        self.is_circuit_breaker_tripped: bool = False
        self.circuit_breaker_tripped_at: Optional[int] = None
        self.circuit_breaker_reason: Optional[str] = None

        # Daily baseline tracking for 24h drawdown calculation
        self.daily_baseline_equity_usd: float = 0.0
        self.last_daily_reset_ts: int = 0

        # Safety assertion
        if self.live_capital_authorized > 0.0:
            raise RuntimeError("CRITICAL INVARIANT VIOLATION: Live capital authorization must remain at $0.00!")

    def register_sub_account(
        self,
        account_id: str,
        account_name: str,
        mandate_styles: List[str],
        allocated_capital_usd: float,
        max_heat_pct: float = 0.02,
    ) -> SubAccountState:
        """Initializes and registers an isolated sub-account."""
        if account_id in self.sub_accounts:
            raise ValueError(f"Sub-account {account_id} is already registered.")

        acc = SubAccountState(
            account_id=account_id,
            account_name=account_name,
            mandate_styles=mandate_styles,
            initial_balance_usd=allocated_capital_usd,
            current_equity_usd=allocated_capital_usd,
            peak_equity_usd=allocated_capital_usd,
            max_account_risk_heat_pct=max_heat_pct,
        )
        self.sub_accounts[account_id] = acc
        self._recalculate_global_baselines()
        return acc

    def _recalculate_global_baselines(self):
        tot = sum(a.current_equity_usd for a in self.sub_accounts.values())
        if self.daily_baseline_equity_usd == 0.0:
            self.daily_baseline_equity_usd = tot

    @property
    def total_aggregate_equity(self) -> float:
        return sum(a.current_equity_usd for a in self.sub_accounts.values())

    @property
    def total_aggregate_heat_pct(self) -> float:
        return sum(a.active_risk_heat_pct for a in self.sub_accounts.values())

    @property
    def total_active_positions(self) -> int:
        return sum(len(a.open_positions) for a in self.sub_accounts.values())

    def check_daily_drawdown_breaker(self, current_time_ms: int) -> bool:
        """Evaluates whether the 3.0% daily drawdown circuit breaker has been breached."""
        # 24h reset logic
        if self.last_daily_reset_ts == 0 or (current_time_ms - self.last_daily_reset_ts) >= 86400 * 1000:
            self.daily_baseline_equity_usd = self.total_aggregate_equity
            self.last_daily_reset_ts = current_time_ms

        baseline = self.daily_baseline_equity_usd
        current = self.total_aggregate_equity

        if baseline <= 0:
            return False

        daily_dd_pct = max(0.0, ((baseline - current) / baseline) * 100.0)

        if daily_dd_pct >= self.global_daily_drawdown_limit_pct:
            self.is_circuit_breaker_tripped = True
            self.circuit_breaker_tripped_at = current_time_ms
            self.circuit_breaker_reason = (
                f"GLOBAL_CIRCUIT_BREAKER: 24h drawdown reached {daily_dd_pct:.2f}% "
                f"(limit: {self.global_daily_drawdown_limit_pct:.2f}%). All trading frozen."
            )
            logger.warning(self.circuit_breaker_reason)
            return True

        return False

    def request_position_allocation(
        self,
        candidate_signal: Dict[str, Any],
        current_time_ms: int,
    ) -> Tuple[bool, str, Optional[str]]:
        """Evaluates candidate trade against multi-account invariants and circuit breakers.
        
        Returns:
            (is_approved, reason, assigned_account_id)
        """
        # Invariant 0: Global Circuit Breaker Check
        if self.is_circuit_breaker_tripped or self.check_daily_drawdown_breaker(current_time_ms):
            return False, f"SUPPRESSED_BY_GLOBAL_CIRCUIT_BREAKER: {self.circuit_breaker_reason}", None

        # Invariant 1: Global Position Count Limit
        if self.total_active_positions >= self.max_total_positions:
            return False, f"SUPPRESSED_PORTFOLIO_CAP: Maximum {self.max_total_positions} concurrent positions reached.", None

        # Invariant 2: Global Heat Capacity Limit
        req_risk_pct = candidate_signal.get("risk_pct", 0.01)
        if self.total_aggregate_heat_pct + req_risk_pct > self.global_max_heat_pct + 1e-6:
            return False, f"SUPPRESSED_HEAT_CAP: Total heat would exceed {self.global_max_heat_pct*100:.1f}%.", None

        # Invariant 3: Route to matching Sub-Account by style mandate
        candidate_style = candidate_signal.get("style", "SWING")
        target_account: Optional[SubAccountState] = None

        for acc in self.sub_accounts.values():
            if candidate_style in acc.mandate_styles:
                target_account = acc
                break

        if target_account is None:
            # Fallback to any account with matching set or default
            target_account = next(iter(self.sub_accounts.values()), None)

        if target_account is None:
            return False, "REJECTED_NO_SUB_ACCOUNT: No matching sub-account available.", None

        # Invariant 4: Sub-Account Specific Checks
        if target_account.is_halted:
            return False, f"REJECTED_ACCOUNT_HALTED: Sub-account {target_account.account_name} is halted ({target_account.halt_reason}).", None

        if target_account.active_risk_heat_pct + req_risk_pct > target_account.max_account_risk_heat_pct + 1e-6:
            return False, f"REJECTED_SUB_ACCOUNT_HEAT: Sub-account {target_account.account_name} heat exhausted.", None

        return True, "ALLOCATION_APPROVED", target_account.account_id

    def register_position_opened(
        self,
        account_id: str,
        trade_id: str,
        trade_payload: Dict[str, Any],
    ):
        """Records an approved position opening in the target sub-account."""
        acc = self.sub_accounts.get(account_id)
        if not acc:
            raise KeyError(f"Unknown sub-account {account_id}")

        risk_pct = trade_payload.get("risk_pct", 0.01)
        acc.open_positions[trade_id] = trade_payload
        acc.active_risk_heat_pct += risk_pct

    def register_position_closed(
        self,
        account_id: str,
        trade_id: str,
        realized_r: float,
        timestamp_ms: int,
    ):
        """Records position exit, updates sub-account equity, and checks circuit breakers."""
        acc = self.sub_accounts.get(account_id)
        if not acc:
            raise KeyError(f"Unknown sub-account {account_id}")

        trade = acc.open_positions.pop(trade_id, None)
        risk_pct = trade.get("risk_pct", 0.01) if trade else 0.01
        acc.active_risk_heat_pct = max(0.0, acc.active_risk_heat_pct - risk_pct)

        # Update PnL and R
        pnl_usd = realized_r * (acc.initial_balance_usd * risk_pct)
        acc.current_equity_usd += pnl_usd
        acc.peak_equity_usd = max(acc.peak_equity_usd, acc.current_equity_usd)
        acc.realized_pnl_usd += pnl_usd
        acc.realized_r_total += realized_r
        acc.closed_trades_count += 1

        # Evaluate sub-account local health
        if acc.current_drawdown_pct >= 8.0:
            acc.is_halted = True
            acc.halt_reason = f"SUB_ACCOUNT_DRAWDOWN_LIMIT: Reached {acc.current_drawdown_pct:.2f}% drawdown."
            logger.warning("Sub-account %s halted: %s", acc.account_name, acc.halt_reason)

        # Re-evaluate global circuit breaker
        self.check_daily_drawdown_breaker(timestamp_ms)

    def get_portfolio_status(self) -> GlobalPortfolioStatus:
        """Returns consolidated institutional status across all sub-accounts."""
        tot_eq = self.total_aggregate_equity
        tot_peak = sum(a.peak_equity_usd for a in self.sub_accounts.values())
        agg_dd = max(0.0, ((tot_peak - tot_eq) / tot_peak * 100.0)) if tot_peak > 0 else 0.0
        tot_heat = self.total_aggregate_heat_pct
        headroom = max(0.0, self.global_max_heat_pct - tot_heat)

        summaries = {
            acc_id: {
                "name": acc.account_name,
                "equity_usd": round(acc.current_equity_usd, 2),
                "peak_usd": round(acc.peak_equity_usd, 2),
                "drawdown_pct": round(acc.current_drawdown_pct, 2),
                "active_heat_pct": round(acc.active_risk_heat_pct * 100.0, 2),
                "open_positions": len(acc.open_positions),
                "closed_trades": acc.closed_trades_count,
                "realized_r": round(acc.realized_r_total, 2),
                "is_halted": acc.is_halted,
            }
            for acc_id, acc in self.sub_accounts.items()
        }

        return GlobalPortfolioStatus(
            total_equity_usd=round(tot_eq, 2),
            total_peak_equity_usd=round(tot_peak, 2),
            aggregate_drawdown_pct=round(agg_dd, 2),
            aggregate_risk_heat_pct=round(tot_heat * 100.0, 2),
            available_risk_headroom_pct=round(headroom * 100.0, 2),
            total_active_positions=self.total_active_positions,
            max_allowed_positions=self.max_total_positions,
            is_global_circuit_breaker_active=self.is_circuit_breaker_tripped,
            circuit_breaker_reason=self.circuit_breaker_reason,
            sub_account_summaries=summaries,
        )


def build_default_strata_multi_account_portfolio() -> MultiAccountPortfolioGovernor:
    """Configures the canonical STRATA 3-sub-account institutional portfolio."""
    gov = MultiAccountPortfolioGovernor(
        global_max_heat_pct=0.03,            # 3.0% aggregate heat
        global_daily_drawdown_limit_pct=3.0, # 3.0% daily circuit breaker
        max_total_positions=3,
        live_capital_authorized=0.00,
    )

    # 1. Macro Trend Sub-Account (Set 1: Investing, Positional)
    gov.register_sub_account(
        account_id="ACC_MACRO_TREND",
        account_name="STRATA Macro Trend Fund",
        mandate_styles=["INVESTING", "POSITIONAL"],
        allocated_capital_usd=500_000.0,
        max_heat_pct=0.02,
    )

    # 2. Tactical Swing Sub-Account (Set 2: Positional, Swing)
    gov.register_sub_account(
        account_id="ACC_TACTICAL_SWING",
        account_name="STRATA Tactical Swing Fund",
        mandate_styles=["SWING"],
        allocated_capital_usd=300_000.0,
        max_heat_pct=0.02,
    )

    # 3. Momentum React Sub-Account (Set 1: Intraday, Scalp)
    gov.register_sub_account(
        account_id="ACC_MOMENTUM_REACT",
        account_name="STRATA Momentum Reaction Fund",
        mandate_styles=["INTRADAY", "SCALP"],
        allocated_capital_usd=200_000.0,
        max_heat_pct=0.01,
    )

    return gov
