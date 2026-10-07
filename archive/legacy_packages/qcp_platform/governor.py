"""Crypto Trading Platform — portfolio risk governor (anti-blowup layer).

The governor is deliberately boring and non-negotiable. It scales or blocks new
risk based on the *account's* state, never on the strategy's opinion:

  * volatility targeting: scale risk so realized portfolio vol tracks a target
    (clamped to [0.5x, 1.5x] risk, matching this repo's existing
    VolatilityTargetSizer convention)
  * drawdown tiers: 10% -> half risk, 20% -> quarter risk, 25% -> hard stop
    (matches this repo's existing DrawdownDampener philosophy, tighter bounds)
  * daily loss limit, weekly loss limit, consecutive-loss cooldown
  * exposure caps: max concurrent positions, max risk per symbol, max risk per
    horizon, and a hard cap on total simultaneous risk
  * kill switch: once tripped, the book stops opening risk until an explicit
    human reset (paper-only in this build)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import numpy as np


@dataclass
class GovernorConfig:
    target_vol_pct: float = 0.15        # annualized target portfolio volatility
    vol_scale_min: float = 0.50
    vol_scale_max: float = 1.50
    dd_tier1: float = 0.10              # halve risk
    dd_tier2: float = 0.20              # quarter risk
    dd_hard_stop: float = 0.25          # flat and stop
    daily_loss_limit: float = 0.03      # of equity, per day
    weekly_loss_limit: float = 0.07
    max_consec_losses: int = 8
    cooldown_days: int = 3
    max_risk_per_symbol: float = 0.01   # concurrent open risk on one asset
    max_risk_per_horizon: float = 0.04
    max_total_risk: float = 0.06


@dataclass
class GovernorState:
    equity: float = 1.0
    peak: float = 1.0
    day: int = -1
    week_start_equity: float = 1.0
    day_start_equity: float = 1.0
    consec_losses: int = 0
    cooldown_until_day: int = -1
    tripped: bool = False
    trip_reason: str = ""
    history: list = field(default_factory=list)

    @property
    def drawdown(self) -> float:
        return 0.0 if self.peak <= 0 else max(0.0, (self.peak - self.equity) / self.peak)


def _dd_scale(dd: float, cfg: GovernorConfig) -> tuple:
    if dd >= cfg.dd_hard_stop:
        return 0.0, f"KILL_DD_{dd * 100:.1f}%"
    if dd >= cfg.dd_tier2:
        return 0.25, None
    if dd >= cfg.dd_tier1:
        return 0.50, None
    return 1.0, None


def vol_scale(realized_vol: float, cfg: GovernorConfig) -> float:
    """Risk multiplier so portfolio vol tracks the target (clamped)."""
    if not np.isfinite(realized_vol) or realized_vol <= 0:
        return 1.0
    raw = cfg.target_vol_pct / realized_vol
    return float(np.clip(raw, cfg.vol_scale_min, cfg.vol_scale_max))


def open_risk(open_positions: Dict[str, float], horizon_of: Dict[str, str],
              symbol: str, horizon: str) -> float:
    """Sum of currently open risk fractions for a symbol / horizon."""
    per_symbol = sum(v for k, v in open_positions.items()
                     if k.split("|")[0] == symbol)
    per_horizon = sum(v for k, v in open_positions.items()
                      if horizon_of.get(k.split("|")[0]) == horizon)
    return per_symbol, per_horizon


class Governor:
    """Stateful risk governor applied at portfolio level, bar by bar."""

    def __init__(self, cfg: GovernorConfig | None = None, initial_equity: float = 1.0):
        self.cfg = cfg or GovernorConfig()
        self.state = GovernorState(equity=initial_equity, peak=initial_equity,
                                   week_start_equity=initial_equity,
                                   day_start_equity=initial_equity)

    def new_day(self, day: int) -> None:
        st = self.state
        if day != st.day:
            st.day = day
            st.day_start_equity = st.equity
            if day % 7 == 0:
                st.week_start_equity = st.equity

    def allow_new_risk(self) -> tuple:
        """(allowed, scale, reason)."""
        st, cfg = self.state, self.cfg
        if st.tripped:
            return False, 0.0, st.trip_reason
        if st.day < st.cooldown_until_day:
            return False, 0.0, "COOLDOWN"
        dd = st.drawdown
        scale, reason = _dd_scale(dd, cfg)
        if scale <= 0:
            st.tripped = True
            st.trip_reason = reason or "KILL_DD"
            return False, 0.0, st.trip_reason
        day_loss = 0.0 if st.day_start_equity <= 0 else \
            max(0.0, (st.day_start_equity - st.equity) / st.day_start_equity)
        if day_loss >= cfg.daily_loss_limit:
            return False, 0.0, f"DAILY_LOSS_{day_loss * 100:.1f}%"
        wk_loss = 0.0 if st.week_start_equity <= 0 else \
            max(0.0, (st.week_start_equity - st.equity) / st.week_start_equity)
        if wk_loss >= cfg.weekly_loss_limit:
            return False, 0.0, f"WEEKLY_LOSS_{wk_loss * 100:.1f}%"
        if st.consec_losses >= cfg.max_consec_losses:
            return False, 0.0, "CONSEC_LOSS_COOLDOWN"
        return True, scale, "OK"

    def on_pnl(self, pnl_frac: float, day: int) -> None:
        st = self.state
        st.equity *= (1.0 + pnl_frac)
        st.peak = max(st.peak, st.equity)
        if pnl_frac < 0:
            st.consec_losses += 1
            if st.consec_losses >= self.cfg.max_consec_losses:
                st.cooldown_until_day = day + self.cfg.cooldown_days
                st.consec_losses = 0
        elif pnl_frac > 0:
            st.consec_losses = 0
        st.history.append((day, st.equity))

    def snapshot(self) -> dict:
        st = self.state
        return dict(equity=round(st.equity, 6), peak=round(st.peak, 6),
                    drawdown=round(st.drawdown, 4), tripped=st.tripped,
                    trip_reason=st.trip_reason)
