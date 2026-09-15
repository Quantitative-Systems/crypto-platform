"""
Quantitative Crypto Platform (QCP) — Relative Value & Statistical Arbitrage Engine.

Implements rigorous cross-asset relative value discovery, cointegration testing,
and causal spread mean-reversion trading for:
- BTC/ETH, SOL/ETH, SOL/BTC (priced in USDT)
- Timeframes: 1D, 4H

Econometric Infrastructure:
- Causal Rolling OLS Hedge Ratio (Zero Lookahead)
- Engle-Granger Two-Step Cointegration Test with ADF Statistics
- Johansen Cointegration Eigenvalue & Trace Test
- Ornstein-Uhlenbeck Half-Life Mean Reversion Estimation
- Decomposed Multi-Leg Execution Friction (Taker fees + Spread crossing)
"""

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from market_intelligence.primitives import Candle
from research.discovery_lab.relative_value_config import (
    RelativeValueConfig,
    DecomposedFrictionModel,
)


@dataclass
class CointegrationMetrics:
    hedge_ratio_beta: float
    intercept_alpha: float
    adf_t_statistic: float
    engle_granger_p_value: float
    is_engle_granger_cointegrated: bool
    johansen_eigenvalue: float
    johansen_trace_statistic: float
    is_johansen_cointegrated: bool
    half_life_bars: float
    mean_reverting: bool


@dataclass
class RelativeValueTrade:
    trade_id: str
    pair: str
    asset_a: str
    asset_b: str
    direction: str                     # "LONG_A_SHORT_B" or "SHORT_A_LONG_B"
    entry_timestamp: int
    entry_price_a: float
    entry_price_b: float
    entry_z_score: float
    entry_hedge_ratio: float
    exit_timestamp: int
    exit_price_a: float
    exit_price_b: float
    exit_z_score: float
    holding_bars: int
    gross_spread_return_pct: float
    total_friction_pct: float
    net_spread_return_pct: float
    net_r: float
    exit_reason: str                   # "MEAN_REVERSION", "SPREAD_DIVERGENCE_SL", "TIME_EXPIRY"


@dataclass
class RelativeValuePartitionResult:
    partition_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_net_r: float
    mean_expectancy_r: float
    profit_factor_r: float
    max_drawdown_r: float
    max_consecutive_losses: int
    avg_holding_bars: float
    total_friction_drag_r: float
    trades: List[RelativeValueTrade] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "partition_name": self.partition_name,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate_pct": round(self.win_rate_pct, 2),
            "total_net_r": round(self.total_net_r, 2),
            "mean_expectancy_r": round(self.mean_expectancy_r, 4),
            "profit_factor_r": round(self.profit_factor_r, 4),
            "max_drawdown_r": round(self.max_drawdown_r, 2),
            "max_consecutive_losses": self.max_consecutive_losses,
            "avg_holding_bars": round(self.avg_holding_bars, 1),
            "total_friction_drag_r": round(self.total_friction_drag_r, 2),
        }


@dataclass
class RelativeValueResearchReport:
    pair_name: str
    symbol_a: str
    symbol_b: str
    timeframe: str
    total_aligned_bars: int
    start_timestamp: int
    end_timestamp: int
    cointegration: CointegrationMetrics
    full_sample: RelativeValuePartitionResult
    dev_sample: RelativeValuePartitionResult
    val_sample: RelativeValuePartitionResult
    oos_sample: RelativeValuePartitionResult
    research_verdict: str
    verdict_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair_name": self.pair_name,
            "symbol_a": self.symbol_a,
            "symbol_b": self.symbol_b,
            "timeframe": self.timeframe,
            "total_aligned_bars": self.total_aligned_bars,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "cointegration": asdict(self.cointegration),
            "full_sample": self.full_sample.to_dict(),
            "dev_sample": self.dev_sample.to_dict(),
            "val_sample": self.val_sample.to_dict(),
            "oos_sample": self.oos_sample.to_dict(),
            "research_verdict": self.research_verdict,
            "verdict_reasons": self.verdict_reasons,
        }


class RelativeValueEngine:
    """
    Econometrically rigorous Statistical Arbitrage & Relative Value Engine.
    """

    def __init__(self, config: Optional[RelativeValueConfig] = None):
        self.config = config or RelativeValueConfig()

    @staticmethod
    def align_candle_series(
        candles_a: List[Candle],
        candles_b: List[Candle],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Causally aligns two candle series strictly by matching timestamps.
        Returns: (timestamps, prices_a, prices_b)
        """
        dict_b = {c.timestamp: c.close for c in candles_b}
        ts_list, p_a_list, p_b_list = [], [], []

        for ca in candles_a:
            if ca.timestamp in dict_b:
                ts_list.append(ca.timestamp)
                p_a_list.append(float(ca.close))
                p_b_list.append(float(dict_b[ca.timestamp]))

        return (
            np.array(ts_list, dtype=np.int64),
            np.array(p_a_list, dtype=np.float64),
            np.array(p_b_list, dtype=np.float64),
        )

    @staticmethod
    def calculate_ols(y: np.ndarray, x: np.ndarray) -> Tuple[float, float, np.ndarray]:
        """
        Computes standard OLS: y = alpha + beta * x + eps.
        Returns: (beta, alpha, residuals)
        """
        n = len(y)
        if n < 3:
            return 1.0, 0.0, np.zeros_like(y)

        x_mean = np.mean(x)
        y_mean = np.mean(y)
        var_x = np.sum((x - x_mean) ** 2)
        if var_x < 1e-12:
            return 1.0, 0.0, y - x

        cov_xy = np.sum((x - x_mean) * (y - y_mean))
        beta = float(cov_xy / var_x)
        alpha = float(y_mean - beta * x_mean)
        residuals = y - (alpha + beta * x)
        return beta, alpha, residuals

    @classmethod
    def calculate_half_life(cls, spread: np.ndarray) -> float:
        """
        Estimates the mean-reversion half-life of a spread using an Ornstein-Uhlenbeck / AR(1) process:
        delta_spread_t = gamma * spread_{t-1} + const + eps_t
        kappa = -gamma
        half_life = ln(2) / kappa
        Returns positive half-life in bars, or float('inf') if non-mean-reverting.
        """
        n = len(spread)
        if n < 10:
            return float("inf")

        y_diff = np.diff(spread)
        x_lag = spread[:-1]
        
        gamma, const, _ = cls.calculate_ols(y_diff, x_lag)
        kappa = -gamma

        if kappa <= 1e-6:
            return float("inf")  # Non-mean-reverting or explosive

        half_life = math.log(2.0) / kappa
        return float(half_life)

    @classmethod
    def calculate_engle_granger(cls, log_a: np.ndarray, log_b: np.ndarray) -> Tuple[float, float, float, float, bool]:
        """
        Performs Engle-Granger Two-Step Cointegration Test:
        Step 1: OLS regression log_a = alpha + beta * log_b + eps
        Step 2: ADF test on residuals eps_t: delta_eps_t = gamma * eps_{t-1} + delta * delta_eps_{t-1} + e_t
        Returns: (beta, alpha, adf_stat, p_value, is_cointegrated)
        """
        n = len(log_a)
        if n < 30:
            return 1.0, 0.0, 0.0, 1.0, False

        beta, alpha, residuals = cls.calculate_ols(log_a, log_b)

        # ADF regression on residuals: delta_res_t = gamma * res_{t-1} + delta * delta_res_{t-1} + e_t
        delta_res = np.diff(residuals)
        res_lag = residuals[1:-1]
        delta_res_lag = delta_res[:-1]
        delta_res_curr = delta_res[1:]

        m = len(delta_res_curr)
        if m < 15:
            return beta, alpha, 0.0, 1.0, False

        # Matrix formulation: Y = X * B + E
        # X columns: [res_lag, delta_res_lag]
        X = np.column_stack([res_lag, delta_res_lag])
        Y = delta_res_curr

        try:
            B, residuals_sum, rank, s = np.linalg.lstsq(X, Y, rcond=None)
            gamma = B[0]
            
            # Compute standard error of gamma
            e = Y - X @ B
            sigma2 = np.sum(e ** 2) / max(1, m - 2)
            inv_XT_X = np.linalg.inv(X.T @ X)
            se_gamma = math.sqrt(max(1e-12, sigma2 * inv_XT_X[0, 0]))
            
            adf_stat = float(gamma / se_gamma)
        except Exception:
            return beta, alpha, 0.0, 1.0, False

        # MacKinnon (2010) response surface cointegration critical values for N=2 without trend:
        # 1%: -3.90, 5%: -3.34, 10%: -3.05
        # Approximate p-value using logistic transformation around critical surface
        if adf_stat <= -3.90:
            p_val = 0.01 * math.exp(adf_stat + 3.90)
        elif adf_stat <= -3.34:
            p_val = 0.01 + 0.04 * (adf_stat - (-3.90)) / ((-3.34) - (-3.90))
        elif adf_stat <= -3.05:
            p_val = 0.05 + 0.05 * (adf_stat - (-3.34)) / ((-3.05) - (-3.34))
        else:
            p_val = min(1.0, 0.10 + 0.30 * (adf_stat - (-3.05)))

        p_val = max(0.0001, min(1.0, p_val))
        is_cointegrated = bool(adf_stat < -3.34 and p_val < 0.05)

        return beta, alpha, round(adf_stat, 4), round(p_val, 4), is_cointegrated

    @classmethod
    def calculate_johansen(cls, log_a: np.ndarray, log_b: np.ndarray) -> Tuple[float, float, bool]:
        """
        Bivariate Johansen Cointegration Test via canonical correlation / eigenvalue decomposition.
        Tests cointegration rank r = 0 vs r >= 1.
        Returns: (eigenvalue, trace_statistic, is_cointegrated)
        """
        n = len(log_a)
        if n < 40:
            return 0.0, 0.0, False

        Y = np.column_stack([log_a, log_b])
        dY = np.diff(Y, axis=0)
        Y_lag = Y[:-1, :]

        T = len(dY)
        if T < 20:
            return 0.0, 0.0, False

        try:
            # Concentrated moment matrices
            S00 = (dY.T @ dY) / T
            S01 = (dY.T @ Y_lag) / T
            S10 = S01.T
            S11 = (Y_lag.T @ Y_lag) / T

            inv_S00 = np.linalg.inv(S00)
            inv_S11 = np.linalg.inv(S11)

            # Solve eigenvalue problem: inv(S11) @ S10 @ inv(S00) @ S01
            M = inv_S11 @ S10 @ inv_S00 @ S01
            eigenvalues = np.linalg.eigvals(M)
            eigenvalues = np.sort(np.real(eigenvalues))[::-1]
            eigenvalues = np.clip(eigenvalues, 0.0, 0.999999)

            lambda_max = float(eigenvalues[0])
            # Trace statistic for r = 0: -T * sum(ln(1 - lambda_i))
            trace_stat = float(-T * np.sum(np.log(1.0 - eigenvalues)))
            
            # Osterwald-Lenum (1992) critical value for bivariate system at 5% significance level = 15.41
            is_coint = bool(trace_stat > 15.41)
            return round(lambda_max, 6), round(trace_stat, 4), is_coint
        except Exception:
            return 0.0, 0.0, False

    def compute_causal_rolling_spread(
        self,
        log_a: np.ndarray,
        log_b: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Computes point-in-time causal rolling hedge ratio, spread, and z-score.
        Uses strictly past window [i-lookback : i] to compute parameters applied at bar i.
        Returns: (betas, alphas, spreads, z_scores)
        """
        n = len(log_a)
        w = self.config.rolling_lookback_window

        betas = np.full(n, np.nan)
        alphas = np.full(n, np.nan)
        spreads = np.full(n, np.nan)
        z_scores = np.full(n, np.nan)

        if n < w + 5:
            return betas, alphas, spreads, z_scores

        rolling_spread_vals = []

        for i in range(w, n):
            # Causal window strictly in the past
            win_y = log_a[i - w:i]
            win_x = log_b[i - w:i]

            b, a, _ = self.calculate_ols(win_y, win_x)
            betas[i] = b
            alphas[i] = a

            # Evaluate point-in-time spread at current bar i using causally estimated beta
            curr_spread = float(log_a[i] - (a + b * log_b[i]))
            spreads[i] = curr_spread

            # Calculate rolling mean and std of the causally constructed spread over the trailing window
            # Window of historical spreads reconstructed using causal beta
            win_spreads = win_y - (a + b * win_x)
            s_mean = float(np.mean(win_spreads))
            s_std = float(np.std(win_spreads, ddof=1))

            if s_std > 1e-6:
                z_scores[i] = (curr_spread - s_mean) / s_std

        return betas, alphas, spreads, z_scores

    def simulate_pair_trading(
        self,
        pair_name: str,
        symbol_a: str,
        symbol_b: str,
        ts: np.ndarray,
        p_a: np.ndarray,
        p_b: np.ndarray,
        betas: np.ndarray,
        spreads: np.ndarray,
        z_scores: np.ndarray,
        start_ts: int = 0,
        end_ts: int = 9999999999,
        friction: Optional[DecomposedFrictionModel] = None,
        latency_bars: int = 0,
    ) -> RelativeValuePartitionResult:
        """
        Simulates causal execution of relative-value trades with adverse-first logic.
        """
        f_model = friction or self.config.friction
        w = self.config.rolling_lookback_window
        n = len(ts)

        trades: List[RelativeValueTrade] = []
        in_pos = False
        pos_dir = ""
        entry_idx = 0
        entry_p_a = 0.0
        entry_p_b = 0.0
        entry_z = 0.0
        entry_beta = 1.0

        for i in range(w + 1, n):
            t = int(ts[i])
            if t < start_ts or t > end_ts:
                continue

            # Signal decided on previous bar close (causal point-in-time)
            sig_idx = i - 1 - latency_bars
            if sig_idx < w:
                continue

            z_sig = z_scores[sig_idx]
            if np.isnan(z_sig):
                continue

            curr_p_a = p_a[i]
            curr_p_b = p_b[i]

            if not in_pos:
                # LONG A / SHORT B: Spread is deeply undervalued (z <= -entry_threshold)
                if z_sig <= -self.config.entry_z_threshold:
                    in_pos = True
                    pos_dir = "LONG_A_SHORT_B"
                    entry_idx = i
                    entry_p_a = curr_p_a
                    entry_p_b = curr_p_b
                    entry_z = z_sig
                    entry_beta = betas[i] if not np.isnan(betas[i]) else 1.0
                # SHORT A / LONG B: Spread is deeply overvalued (z >= entry_threshold)
                elif z_sig >= self.config.entry_z_threshold:
                    in_pos = True
                    pos_dir = "SHORT_A_LONG_B"
                    entry_idx = i
                    entry_p_a = curr_p_a
                    entry_p_b = curr_p_b
                    entry_z = z_sig
                    entry_beta = betas[i] if not np.isnan(betas[i]) else 1.0
            else:
                bars_held = i - entry_idx
                exit_signal = False
                reason = ""

                # Return on spread components: R_spread = R_A - beta * R_B
                ret_a = (curr_p_a - entry_p_a) / entry_p_a
                ret_b = (curr_p_b - entry_p_b) / entry_p_b
                
                # Market neutral hedged return
                gross_return = ret_a - (entry_beta * ret_b)
                if pos_dir == "SHORT_A_LONG_B":
                    gross_return = -gross_return

                # Check Exit Conditions:
                # 1. Mean Reversion Target
                if pos_dir == "LONG_A_SHORT_B" and z_sig >= -self.config.exit_z_threshold:
                    exit_signal = True
                    reason = "MEAN_REVERSION"
                elif pos_dir == "SHORT_A_LONG_B" and z_sig <= self.config.exit_z_threshold:
                    exit_signal = True
                    reason = "MEAN_REVERSION"
                # 2. Invalidation Stop Loss (Divergence beyond stop threshold)
                elif pos_dir == "LONG_A_SHORT_B" and z_sig <= -self.config.stop_loss_z:
                    exit_signal = True
                    reason = "SPREAD_DIVERGENCE_SL"
                elif pos_dir == "SHORT_A_LONG_B" and z_sig >= self.config.stop_loss_z:
                    exit_signal = True
                    reason = "SPREAD_DIVERGENCE_SL"
                # 3. Maximum Holding Period Expiry
                elif bars_held >= self.config.max_holding_bars:
                    exit_signal = True
                    reason = "TIME_EXPIRY"

                if exit_signal:
                    # Deduct decomposed friction across both legs
                    tot_friction = f_model.total_pair_roundtrip_pct
                    net_return = gross_return - tot_friction

                    # Standardize into R units: normalized against 5% spread risk unit
                    r_unit = self.config.risk_unit_spread_pct
                    pnl_r = net_return / r_unit

                    trade = RelativeValueTrade(
                        trade_id=f"RV_{pair_name}_{ts[entry_idx]}_{t}",
                        pair=pair_name,
                        asset_a=symbol_a,
                        asset_b=symbol_b,
                        direction=pos_dir,
                        entry_timestamp=int(ts[entry_idx]),
                        entry_price_a=entry_p_a,
                        entry_price_b=entry_p_b,
                        entry_z_score=round(entry_z, 3),
                        entry_hedge_ratio=round(entry_beta, 4),
                        exit_timestamp=t,
                        exit_price_a=curr_p_a,
                        exit_price_b=curr_p_b,
                        exit_z_score=round(z_sig, 3),
                        holding_bars=bars_held,
                        gross_spread_return_pct=round(gross_return * 100.0, 3),
                        total_friction_pct=round(tot_friction * 100.0, 3),
                        net_spread_return_pct=round(net_return * 100.0, 3),
                        net_r=round(pnl_r, 4),
                        exit_reason=reason,
                    )
                    trades.append(trade)
                    in_pos = False

        # Calculate Partition Performance Metrics
        n_trades = len(trades)
        if n_trades == 0:
            return RelativeValuePartitionResult(
                partition_name="",
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate_pct=0.0,
                total_net_r=0.0,
                mean_expectancy_r=0.0,
                profit_factor_r=0.0,
                max_drawdown_r=0.0,
                max_consecutive_losses=0,
                avg_holding_bars=0.0,
                total_friction_drag_r=0.0,
                trades=[],
            )

        wins = [t.net_r for t in trades if t.net_r > 0]
        losses = [t.net_r for t in trades if t.net_r <= 0]
        sum_wins = sum(wins)
        sum_losses = abs(sum(losses))
        pf = (sum_wins / sum_losses) if sum_losses > 1e-6 else 99.0
        tot_r = sum(t.net_r for t in trades)
        mean_r = tot_r / n_trades

        # Drawdown in R
        peak_r = 0.0
        cum_r = 0.0
        max_dd_r = 0.0
        for t in trades:
            cum_r += t.net_r
            if cum_r > peak_r:
                peak_r = cum_r
            dd = peak_r - cum_r
            if dd > max_dd_r:
                max_dd_r = dd

        # Consecutive Losses
        curr_l = 0
        max_l = 0
        for t in trades:
            if t.net_r <= 0:
                curr_l += 1
                if curr_l > max_l:
                    max_l = curr_l
            else:
                curr_l = 0

        avg_bars = float(np.mean([t.holding_bars for t in trades]))
        f_drag_r = (f_model.total_pair_roundtrip_pct / self.config.risk_unit_spread_pct) * n_trades

        return RelativeValuePartitionResult(
            partition_name="",
            total_trades=n_trades,
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate_pct=(len(wins) / n_trades) * 100.0,
            total_net_r=tot_r,
            mean_expectancy_r=mean_r,
            profit_factor_r=pf,
            max_drawdown_r=max_dd_r,
            max_consecutive_losses=max_l,
            avg_holding_bars=avg_bars,
            total_friction_drag_r=f_drag_r,
            trades=trades,
        )

    def evaluate_pair(
        self,
        symbol_a: str,
        symbol_b: str,
        pair_name: str,
        candles_a: List[Candle],
        candles_b: List[Candle],
        timeframe: str,
    ) -> RelativeValueResearchReport:
        """
        Executes end-to-end econometric evaluation, cointegration testing, and partitioned trading backtest.
        """
        ts, p_a, p_b = self.align_candle_series(candles_a, candles_b)
        n = len(ts)

        if n < self.config.min_cointegration_obs:
            empty_part = RelativeValuePartitionResult("", 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, [])
            return RelativeValueResearchReport(
                pair_name=pair_name,
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                timeframe=timeframe,
                total_aligned_bars=n,
                start_timestamp=0,
                end_timestamp=0,
                cointegration=CointegrationMetrics(1.0, 0.0, 0.0, 1.0, False, 0.0, 0.0, False, float("inf"), False),
                full_sample=empty_part,
                dev_sample=empty_part,
                val_sample=empty_part,
                oos_sample=empty_part,
                research_verdict="INSUFFICIENT_DATA",
                verdict_reasons=[f"Aligned bars {n} < minimum required {self.config.min_cointegration_obs}."],
            )

        log_a = np.log(p_a)
        log_b = np.log(p_b)

        # 1. Cointegration & Econometric Forensics
        beta, alpha, adf_stat, p_val, is_eg = self.calculate_engle_granger(log_a, log_b)
        eig, trace_stat, is_joh = self.calculate_johansen(log_a, log_b)
        
        # Static residual for half-life check
        static_spread = log_a - (alpha + beta * log_b)
        half_life = self.calculate_half_life(static_spread)
        is_mean_rev = bool(half_life < self.config.max_half_life_bars and half_life > 0.5)

        coint_metrics = CointegrationMetrics(
            hedge_ratio_beta=round(beta, 4),
            intercept_alpha=round(alpha, 4),
            adf_t_statistic=adf_stat,
            engle_granger_p_value=p_val,
            is_engle_granger_cointegrated=is_eg,
            johansen_eigenvalue=eig,
            johansen_trace_statistic=trace_stat,
            is_johansen_cointegrated=is_joh,
            half_life_bars=round(half_life, 2) if not math.isinf(half_life) else 999.0,
            mean_reverting=is_mean_rev,
        )

        # 2. Causal Rolling Spread Generation
        betas, alphas, spreads, z_scores = self.compute_causal_rolling_spread(log_a, log_b)

        # 3. Simulate Partitions
        full_res = self.simulate_pair_trading(
            pair_name, symbol_a, symbol_b, ts, p_a, p_b, betas, spreads, z_scores,
            start_ts=self.config.dev_start_ts, end_ts=self.config.oos_end_ts,
        )
        full_res.partition_name = "FULL_SAMPLE"

        dev_res = self.simulate_pair_trading(
            pair_name, symbol_a, symbol_b, ts, p_a, p_b, betas, spreads, z_scores,
            start_ts=self.config.dev_start_ts, end_ts=self.config.dev_end_ts,
        )
        dev_res.partition_name = "DEV_SAMPLE"

        val_res = self.simulate_pair_trading(
            pair_name, symbol_a, symbol_b, ts, p_a, p_b, betas, spreads, z_scores,
            start_ts=self.config.val_start_ts, end_ts=self.config.val_end_ts,
        )
        val_res.partition_name = "VAL_SAMPLE"

        oos_res = self.simulate_pair_trading(
            pair_name, symbol_a, symbol_b, ts, p_a, p_b, betas, spreads, z_scores,
            start_ts=self.config.oos_start_ts, end_ts=self.config.oos_end_ts,
        )
        oos_res.partition_name = "OOS_SAMPLE"

        # 4. Research Classification Verdict
        reasons = []
        if not is_eg and not is_joh:
            verdict = "FALSIFIED_NO_COINTEGRATION"
            reasons.append(f"Fails cointegration tests: Engle-Granger p={p_val:.4f} (ADF={adf_stat:.2f}), Johansen Trace={trace_stat:.2f}.")
        elif not is_mean_rev:
            verdict = "FRAGILE_SLOW_MEAN_REVERSION"
            reasons.append(f"Spread half-life ({half_life:.1f} bars) exceeds threshold ({self.config.max_half_life_bars} bars).")
        elif oos_res.total_net_r <= 0.0:
            verdict = "FRAGILE_OOS_DEGRADED"
            reasons.append(f"OOS Net R is non-positive ({oos_res.total_net_r:.2f}R).")
        elif oos_res.mean_expectancy_r < 0.10:
            verdict = "FRAGILE_MARGINAL_EDGE"
            reasons.append(f"OOS Expectancy ({oos_res.mean_expectancy_r:.4f}R) is below hurdle (+0.10R).")
        else:
            verdict = "QUALIFIED_RESEARCH_CANDIDATE"
            reasons.append(f"Cointegrated (EG={is_eg}, Johansen={is_joh}), mean-reverting (t_1/2={half_life:.1f} bars).")
            reasons.append(f"Positive OOS performance: +{oos_res.total_net_r:.2f}R across {oos_res.total_trades} trades.")

        return RelativeValueResearchReport(
            pair_name=pair_name,
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            timeframe=timeframe,
            total_aligned_bars=n,
            start_timestamp=int(ts[0]),
            end_timestamp=int(ts[-1]),
            cointegration=coint_metrics,
            full_sample=full_res,
            dev_sample=dev_res,
            val_sample=val_res,
            oos_sample=oos_res,
            research_verdict=verdict,
            verdict_reasons=reasons,
        )
