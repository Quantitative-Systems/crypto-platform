# Product 03: Risk & Capital Firewall

The Risk Firewall operates completely downstream of the Strategy Engine. It possesses no awareness of market phases, structural swings, or trading hypotheses. Its sole function is to mathematically protect capital and enforce invariant exposure limits.

## The Approval Pipeline

When a trade is proposed by the Strategy Engine (via `TradePlanPayload`), it must clear all sequential circuits in the Risk Firewall before it can become an execution-ready `RiskApprovedPlan`.

### 1. Inviolable Capital Shield (Position Sizing)
The risk firewall forces an absolute ceiling on the amount of capital exposed in a single trade.
- **Maximum Intended Risk**: `1.0%` of active account equity.
- **Calculation**: Position size is mathematically derived from the exact geometric distance between the strategy's requested Entry Price and the structural Stop-Loss Price.
- **Circuit**: Rejects setups mathematically (`REJECT_INVALID_STOP`) if the stop-loss is placed precisely at the entry.

### 2. Structural Reward-to-Risk (R:R) Limiter
As a redundant secondary guardrail, the firewall verifies the structural geometry of the trade payload.
- **Minimum Acceptable R:R**: `4.0R`
- **Maximum Acceptable R:R**: Uncapped
- **Circuit**: Any proposed trade arriving with a raw structural calculation below the `4.0R` threshold is blocked with `REJECT_RR_BELOW_FLOOR`.

### 3. Drawdown Circuit Breakers
The portfolio is protected by strict dynamic drawdown floors.
- **Daily Drawdown Limit**: `-3.0%`
- **Weekly Drawdown Limit**: `-6.0%`
- **Systemic (Peak-to-Trough) Limit**: `-10.0%`
- **Circuit**: Any violation halts new position authorizations instantly until the temporal epoch resets or manual intervention occurs.

### 4. Exposure & Correlation Controls
- **Maximum Simultaneous Open Positions**: `5`
- Limits sequential or clustered entries to prevent unintentional systemic leverage buildup.

## The Rejection Telemetry Funnel
A critical principle of the platform is that rejected setups are *never* silently discarded. Every trade blocked by the firewall emits a precise `RiskRejectionPayload` with encoded reason telemetry (e.g., `REJECT_SYSTEMIC_CIRCUIT_BREAKER`). This preserves the complete research funnel, allowing researchers to quantify how frequently structural strategy setups conflict with capital protection mandates.
