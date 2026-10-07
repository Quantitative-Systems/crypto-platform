# Formal Research Hypothesis Registry
## Institutional Single-Variable Scientific Experiments

**Last Updated**: `2026-09-08T03:43:47.848349+00:00`  
**Governing Standard**: Anti-Curve-Fitting / Single Structural Modification  
**Control Baseline**: `HTF_TREND_CONTINUATION_V1` ($N=128$, $-76.77\text{R}$, $E[R]=-0.5998\text{R}$)  

---

| Hypothesis ID | Parent | Affected Component | Structural Modification | Pre-Registered Parameter | Status |
|---|---|---|---|---|:---:|
| **HTF_TREND_CONTINUATION_V1** | `NONE_ROOT_CONTROL` | `SystemRoot` | None (Frozen negative control benchmark). | `min_rr=4.0`, `risk_fraction=0.01` | `REJECTED_RESEARCH_ONLY` |
| **H1.1_EARLIER_MTF_ENTRY** | `HTF_TREND_CONTINUATION_V1` | `StrategyCoordinator / LTFTriggerEngine` | Trigger entry on immediate MTF confirmation bar close, eliminating secondary delayed LTF consolidation lag. | `mtf_entry_trigger=IMMEDIATE_MTF_CONFIRMATION`, `max_ltf_lag_bars=0` | `REGISTERED_QUEUED` |
| **H1.2_MTF_STRUCTURAL_SL_ANCHOR** | `HTF_TREND_CONTINUATION_V1` | `RiskEngine / PositionSizer` | Anchor initial structural stop loss to confirmed MTF Swing Extreme instead of micro LTF wick. | `sl_anchor_timeframe=MTF`, `buffer_atr_mult=0.1` | `REGISTERED_QUEUED` |
| **H1.3_DYNAMIC_STRUCTURAL_TARGET** | `HTF_TREND_CONTINUATION_V1` | `HTFDestinationEngine / TradePlan` | Set structural profit target to nearest opposing MTF swing pivot (min 1.5R) rather than rigid 4.0R macro extreme. | `target_mode=NEAREST_OPPOSING_MTF_SWING`, `min_rr_floor=1.5` | `REGISTERED_QUEUED` |
| **H1.4_DYNAMIC_PROFIT_LOCK_0_75R** | `HTF_TREND_CONTINUATION_V1` | `ExecutionSimulator / TradeManagement` | Activate break-even stop ratchet at +0.75R MFE with +0.05R buffer for fees. | `profit_lock_trigger_r=0.75`, `profit_lock_stop_r=0.05` | `REGISTERED_QUEUED` |
| **H1.5_HTF_KEYZONE_FRESHNESS_7D** | `HTF_TREND_CONTINUATION_V1` | `KeyZoneEngine / CandidateTracker` | Quarantine candidate qualification to HTF KeyZones where (interaction_time - creation_time) <= 7 days. | `max_keyzone_age_days=7.0` | `REGISTERED_QUEUED` |
| **H1.6_VOLATILITY_EXPANSION_QUALIFICATION** | `HTF_TREND_CONTINUATION_V1` | `MarketIntelligenceCoordinator` | Require MTF ATR_14 > SMA_50(ATR_14) at entry qualification. | `volatility_metric=ATR_14`, `volatility_threshold=SMA_50_ATR` | `REGISTERED_QUEUED` |
| **H1.7_FAST_MTF_RETEST_24H** | `HTF_TREND_CONTINUATION_V1` | `MTFAlignmentEngine / CandidateTracker` | Reject setups where MTF retest occurs > 24 hours after MTF alignment event. | `max_retest_delay_hours=24.0` | `REGISTERED_QUEUED` |

---

### HTF_TREND_CONTINUATION_V1
- **Parent Hypothesis**: `NONE_ROOT_CONTROL`
- **Status**: **`REJECTED_RESEARCH_ONLY`**
- **Economic / Microstructure Rationale**: Canonical institutional trend-following baseline trading in direction of HTF structure.
- **Single Structural Modification**: None (Frozen negative control benchmark).
- **Affected Subsystem**: `SystemRoot`
- **Pre-Registered Parameters**: `{'min_rr': 4.0, 'risk_fraction': 0.01}`
- **Expected Failure Mode**: Extreme target unreachability, stale zone decay, and micro-stop noise liquidation.
- **Acceptance Thresholds**: `{'expectancy_r': '> 0.0R', 'profit_factor': '> 1.0'}`
- **Rejection Thresholds**: `{'expectancy_r': '<= 0.0R'}`
- **Partition Scopes**:
  - Development: `2021-01-01 to 2022-12-31` (`BTC/USDT, ETH/USDT, SOL/USDT`)
  - Validation: `2023-01-01 to 2023-12-31` (FROZEN)
  - Out-of-Sample: `2024-01-01 to 2026-06-30` (UNTOUCHED)
- **Empirical Verdict**: **`REJECTED_RESEARCH_ONLY`** — Empirical control result: N=128, E[R]=-0.5998R, Net Realized Return=-76.77R, PF=0.38, 95% CI=[-0.7137R, -0.4683R].

### H1.1_EARLIER_MTF_ENTRY
- **Parent Hypothesis**: `HTF_TREND_CONTINUATION_V1`
- **Status**: **`REGISTERED_QUEUED`**
- **Economic / Microstructure Rationale**: Forensic Phase 1 demonstrated that trades delayed > 1h lose -0.8699R (59.5% of losses). Entering on immediate close of the MTF realignment/retest bar captures initial impulse momentum before local exhaustion.
- **Single Structural Modification**: Trigger entry on immediate MTF confirmation bar close, eliminating secondary delayed LTF consolidation lag.
- **Affected Subsystem**: `StrategyCoordinator / LTFTriggerEngine`
- **Pre-Registered Parameters**: `{'mtf_entry_trigger': 'IMMEDIATE_MTF_CONFIRMATION', 'max_ltf_lag_bars': 0}`
- **Expected Failure Mode**: Potential increase in false breakouts without secondary micro-sweep confirmation.
- **Acceptance Thresholds**: `{'dev_expectancy_r': '> 0.0R', 'profit_factor': '> 1.0', 'cost_stress_1_5x_e_r': '> 0.0R'}`
- **Rejection Thresholds**: `{'dev_expectancy_r': '<= -0.20R', 'win_rate_pct': '< 25.0%'}`
- **Partition Scopes**:
  - Development: `2021-01-01 to 2022-12-31` (`BTC/USDT, ETH/USDT, SOL/USDT`)
  - Validation: `2023-01-01 to 2023-12-31` (FROZEN)
  - Out-of-Sample: `2024-01-01 to 2026-06-30` (UNTOUCHED)

### H1.2_MTF_STRUCTURAL_SL_ANCHOR
- **Parent Hypothesis**: `HTF_TREND_CONTINUATION_V1`
- **Status**: **`REGISTERED_QUEUED`**
- **Economic / Microstructure Rationale**: Forensic Phase 1 revealed that 41.8% of losses stem from sub-0.5% micro-stops swept by high-frequency spread/noise. Anchoring stop to confirmed MTF swing extreme places invalidation outside noise bands, while position sizing inversely scales to hold dollar risk constant at 1%.
- **Single Structural Modification**: Anchor initial structural stop loss to confirmed MTF Swing Extreme instead of micro LTF wick.
- **Affected Subsystem**: `RiskEngine / PositionSizer`
- **Pre-Registered Parameters**: `{'sl_anchor_timeframe': 'MTF', 'buffer_atr_mult': 0.1}`
- **Expected Failure Mode**: Wider stops reduce trade reward-to-risk ratio, requiring higher win rate to maintain profitability.
- **Acceptance Thresholds**: `{'dev_expectancy_r': '> 0.0R', 'win_rate_pct': '> 35.0%', 'profit_factor': '> 1.0'}`
- **Rejection Thresholds**: `{'dev_net_r': '< -36.70R', 'dev_expectancy_r': '< -0.40R'}`
- **Partition Scopes**:
  - Development: `2021-01-01 to 2022-12-31` (`BTC/USDT, ETH/USDT, SOL/USDT`)
  - Validation: `2023-01-01 to 2023-12-31` (FROZEN)
  - Out-of-Sample: `2024-01-01 to 2026-06-30` (UNTOUCHED)

### H1.3_DYNAMIC_STRUCTURAL_TARGET
- **Parent Hypothesis**: `HTF_TREND_CONTINUATION_V1`
- **Status**: **`REGISTERED_QUEUED`**
- **Economic / Microstructure Rationale**: Forensic Phase 1 proved that 52.4% of loss velocity was target unreachability drag: 0/128 trades reached fixed 4.0R, but 44.5% reached +0.5R to +2.58R before reversing. Anchoring target dynamically to nearest opposing MTF liquidity pool (min 1.5R) monetizes real market moves.
- **Single Structural Modification**: Set structural profit target to nearest opposing MTF swing pivot (min 1.5R) rather than rigid 4.0R macro extreme.
- **Affected Subsystem**: `HTFDestinationEngine / TradePlan`
- **Pre-Registered Parameters**: `{'target_mode': 'NEAREST_OPPOSING_MTF_SWING', 'min_rr_floor': 1.5}`
- **Expected Failure Mode**: Reduced payoff ratio per winning trade may fail to outpace round-trip fees if win rate does not increase.
- **Acceptance Thresholds**: `{'dev_expectancy_r': '> 0.0R', 'target_reach_rate_pct': '> 20.0%', 'profit_factor': '> 1.10'}`
- **Rejection Thresholds**: `{'dev_expectancy_r': '<= 0.0R', 'profit_factor': '< 1.0'}`
- **Partition Scopes**:
  - Development: `2021-01-01 to 2022-12-31` (`BTC/USDT, ETH/USDT, SOL/USDT`)
  - Validation: `2023-01-01 to 2023-12-31` (FROZEN)
  - Out-of-Sample: `2024-01-01 to 2026-06-30` (UNTOUCHED)

### H1.4_DYNAMIC_PROFIT_LOCK_0_75R
- **Parent Hypothesis**: `HTF_TREND_CONTINUATION_V1`
- **Status**: **`REGISTERED_QUEUED`**
- **Economic / Microstructure Rationale**: Forensic Phase 1 showed trades reaching +0.5R to +0.9R had 38.6% failure rate because baseline trailing only engaged at +1.0R. Engaging break-even lock at +0.75R MFE protects +0.5R moves from collapsing into full losses.
- **Single Structural Modification**: Activate break-even stop ratchet at +0.75R MFE with +0.05R buffer for fees.
- **Affected Subsystem**: `ExecutionSimulator / TradeManagement`
- **Pre-Registered Parameters**: `{'profit_lock_trigger_r': 0.75, 'profit_lock_stop_r': 0.05}`
- **Expected Failure Mode**: Premature break-even stop-outs on natural counter-trend wicks, truncating larger multi-R continuation runs.
- **Acceptance Thresholds**: `{'dev_net_r_delta': '>= +10.0R', 'dev_expectancy_r': '> 0.0R', 'profit_factor': '> 1.0'}`
- **Rejection Thresholds**: `{'winner_retention_pct': '< 70.0%', 'dev_net_r_delta': '< 0.0R'}`
- **Partition Scopes**:
  - Development: `2021-01-01 to 2022-12-31` (`BTC/USDT, ETH/USDT, SOL/USDT`)
  - Validation: `2023-01-01 to 2023-12-31` (FROZEN)
  - Out-of-Sample: `2024-01-01 to 2026-06-30` (UNTOUCHED)

### H1.5_HTF_KEYZONE_FRESHNESS_7D
- **Parent Hypothesis**: `HTF_TREND_CONTINUATION_V1`
- **Status**: **`REGISTERED_QUEUED`**
- **Economic / Microstructure Rationale**: Forensic Phase 1 proved that KeyZones > 7 days old generated 0 winners and accounted for -18.6R in losses. Older zones represent re-auctioned retail inventory rather than fresh institutional liquidity.
- **Single Structural Modification**: Quarantine candidate qualification to HTF KeyZones where (interaction_time - creation_time) <= 7 days.
- **Affected Subsystem**: `KeyZoneEngine / CandidateTracker`
- **Pre-Registered Parameters**: `{'max_keyzone_age_days': 7.0}`
- **Expected Failure Mode**: Throughput compression from rejecting valid structural levels.
- **Acceptance Thresholds**: `{'winner_retention_pct': '100.0%', 'loss_removal_count': '>= 20', 'dev_net_r_delta': '>= +15.0R'}`
- **Rejection Thresholds**: `{'winner_retention_pct': '< 100.0%', 'dev_net_r_delta': '< +5.0R'}`
- **Partition Scopes**:
  - Development: `2021-01-01 to 2022-12-31` (`BTC/USDT, ETH/USDT, SOL/USDT`)
  - Validation: `2023-01-01 to 2023-12-31` (FROZEN)
  - Out-of-Sample: `2024-01-01 to 2026-06-30` (UNTOUCHED)

### H1.6_VOLATILITY_EXPANSION_QUALIFICATION
- **Parent Hypothesis**: `HTF_TREND_CONTINUATION_V1`
- **Status**: **`REGISTERED_QUEUED`**
- **Economic / Microstructure Rationale**: Forensic Phase 1 demonstrated compression regimes produce frequent false breakouts. Requiring MTF ATR > 50-period SMA(ATR) filters out dead-market chop.
- **Single Structural Modification**: Require MTF ATR_14 > SMA_50(ATR_14) at entry qualification.
- **Affected Subsystem**: `MarketIntelligenceCoordinator`
- **Pre-Registered Parameters**: `{'volatility_metric': 'ATR_14', 'volatility_threshold': 'SMA_50_ATR'}`
- **Expected Failure Mode**: Entering at the tail end of volatility expansion cycles, buying local top of volatility.
- **Acceptance Thresholds**: `{'dev_expectancy_r': '> 0.0R', 'profit_factor': '> 1.0'}`
- **Rejection Thresholds**: `{'dev_expectancy_r': '<= 0.0R', 'throughput_retention_pct': '< 40.0%'}`
- **Partition Scopes**:
  - Development: `2021-01-01 to 2022-12-31` (`BTC/USDT, ETH/USDT, SOL/USDT`)
  - Validation: `2023-01-01 to 2023-12-31` (FROZEN)
  - Out-of-Sample: `2024-01-01 to 2026-06-30` (UNTOUCHED)

### H1.7_FAST_MTF_RETEST_24H
- **Parent Hypothesis**: `HTF_TREND_CONTINUATION_V1`
- **Status**: **`REGISTERED_QUEUED`**
- **Economic / Microstructure Rationale**: Forensic Phase 1 showed fast retests (<=4h) produced +0.4377R expectancy (PF 1.65), whereas slow grinds (>24h) produced 0% win rate (-1.06R avg, 41.7% of losses). Filtering out stale retests eliminates exhausted setups.
- **Single Structural Modification**: Reject setups where MTF retest occurs > 24 hours after MTF alignment event.
- **Affected Subsystem**: `MTFAlignmentEngine / CandidateTracker`
- **Pre-Registered Parameters**: `{'max_retest_delay_hours': 24.0}`
- **Expected Failure Mode**: Missing multi-day accumulator pullbacks in high-timeframe trends.
- **Acceptance Thresholds**: `{'loss_removal_count': '>= 15', 'dev_expectancy_r': '> 0.0R', 'profit_factor': '> 1.0'}`
- **Rejection Thresholds**: `{'winner_retention_pct': '< 80.0%', 'dev_net_r_delta': '< +5.0R'}`
- **Partition Scopes**:
  - Development: `2021-01-01 to 2022-12-31` (`BTC/USDT, ETH/USDT, SOL/USDT`)
  - Validation: `2023-01-01 to 2023-12-31` (FROZEN)
  - Out-of-Sample: `2024-01-01 to 2026-06-30` (UNTOUCHED)
