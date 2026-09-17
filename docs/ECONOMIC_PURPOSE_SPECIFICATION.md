# QCP Economic Purpose Specification
**Directive**: EABG-001  
**Platform**: Quantitative Crypto Platform (QCP)  
**Status**: Canonical Architectural Reference  
**Capital Allocation**: $0.00 (Fail-Closed Governance Firewall)

---

## Executive Principle: The Economic Imperative

In accordance with Directive **EABG-001**, the Quantitative Crypto Platform rejects architectural theater, vanity feature counts, and manufactured backtests. Every market-facing capability and subsystem must answer ten fundamental economic questions. If a component cannot provide verifiable, causal answers to these questions, it is classified as **supporting infrastructure** rather than alpha.

```
                    ECONOMIC PURPOSE GOVERNANCE LOOP
                     
      [1. INEFFICIENCY] ──► [2. DATA REQUIREMENT] ──► [3. RETURN MECHANISM]
                                                              │
                                                              ▼
      [6. STOP REGIME]  ◄── [5. OPERATING REGIME] ◄── [4. FRICTION COSTS]
             │
             ▼
      [7. DESTRUCTIVE RISKS] ──► [8. FALSIFICATION] ──► [9. PROMOTION] ──► [10. RETIREMENT]
```

---

## Table of Subsystem Classifications

| Subsystem / Capability | Canonical Classification | Primary Economic Objective |
| :--- | :--- | :--- |
| **1. Trend Continuation** | Alpha Family (FAM-01) | Capture persistent directional drift driven by structural capital flows |
| **2. Mean Reversion** | Alpha Family (FAM-02) | Exploit temporary liquidity dislocations and price overextension |
| **3. Breakout Expansion** | Alpha Family (FAM-03) | Monetize volatility compression transitions into directional expansion |
| **4. Relative Value** | Alpha Family (FAM-09) | Harvest mean-reverting stationary spreads between cointegrated assets |
| **5. Basis Arbitrage** | Alpha Family (FAM-06) | Monetize premium/discount between spot and derivative instruments |
| **6. Funding Carry** | Alpha Family (FAM-07) | Capture perpetual swap funding rate premia while neutralizing delta |
| **7. Cross-Venue Arbitrage** | Alpha Family (FAM-10) | Extract spatial price dislocations across segmented execution venues |
| **8. Market Making** | Execution / Alpha (FAM-11) | Harvest bid-ask spread liquidity premia under inventory risk bounds |
| **9. Options & Volatility** | Derivative Alpha (FAM-08) | Monetize implied vs realized volatility and non-linear risk premia |
| **10. Hedging Engine** | Risk Reduction Engine | Minimize unwanted portfolio beta, delta, and tail exposure |
| **11. Portfolio Allocator** | Capital Engine | Dynamically optimize risk-budgeted capital allocation under heat caps |
| **12. Execution OS & SOR** | Cost Reduction Engine | Minimize implementation shortfall, slippage, and adverse selection |
| **13. Market Data Engine** | Core Infrastructure | Deliver certified, causally sequenced, gap-audited market feeds |
| **14. Research Engine** | Discovery & Falsification | Eliminate lookahead bias and rigorously falsify invalid claims |
| **15. Regime Engine** | Context & Filter Engine | Classify market environment to enable or disable appropriate alphas |
| **16. Unified Risk Engine** | Capital Preservation | Absolute sovereign veto over all capital decisions and small account gating |
| **17. Forward Paper Daemon** | Empirical Verification | Continuous out-of-sample forward observation without lookahead |

---

## 1. Trend Continuation Engine (`TrendStrategy` / FAM-01)

1. **Market Inefficiency**: Information diffusion friction, institutional rebalancing inertia, and herd momentum cause crypto asset prices to drift directionally across higher timeframes (1h, 4h, 1d) rather than instantaneously reflecting fair value.
2. **Observable Data**: Certified OHLCV bars (1h, 4h, 1d), volume moving averages, and cross-timeframe trend filters (EMA 50/200, ATR).
3. **Return Mechanism**: Enters in the direction of established momentum following pullbacks; captures fat-tailed right-skewed gains while cutting losing trades at predefined stop losses.
4. **Friction Costs**: Taker exchange fees (4–10 bps), execution slippage on market/stop orders (2–8 bps), and funding carry drag if holding long perpetual positions during bull regimes.
5. **Operating Regimes**: Strong directional trend regimes (`BULL_TREND`, `BEAR_TREND`) characterized by low-to-moderate volatility and consistent directional volume.
6. **Stop Regimes**: Ranging, mean-reverting, low-volatility chop (`RANGING_LOW_VOL`) or extreme deleveraging cascades where trend signals suffer consecutive whipsaw stops.
7. **Destructive Risks**: Prolonged whipsaw markets (wiping out capital through consecutive false breakouts), flash crashes violating stop-loss orders via gap slippage, and abrupt regime reversals.
8. **Falsification Method**: Subjection to 5-year multi-asset backtest with 16 bps roundtrip friction; failure to achieve positive net expectancy across both bull and bear partitions; degradation of win rate below 35% with profit factor < 1.10.
9. **Promotion Evidence**: Statistically significant out-of-sample positive return (t-stat > 2.0, net Sharpe > 1.2, expectancy > +0.20R) maintained across at least two independent certified assets.
10. **Retirement Evidence**: Realized maximum drawdown exceeding 1.5x historical backtest maximum drawdown, or 20 consecutive trades with negative cumulative R in forward paper trading.

---

## 2. Mean Reversion Engine (`MeanReversionStrategy` / FAM-02)

1. **Market Inefficiency**: Retail panic liquidation, stop-loss cascades, and localized order book depletion push prices temporarily beyond statistical fair value, followed by liquidity restoration.
2. **Observable Data**: L2 order book depth, short-timeframe OHLCV (5m, 15m, 1h), relative strength index (RSI), Bollinger Bands, and intraday VWAP deviations.
3. **Return Mechanism**: Fades statistical extremes (Z-score > 2.5 or RSI < 25 / > 75); captures rapid price snapback toward rolling VWAP or moving average.
4. **Friction Costs**: Roundtrip taker fees (8–16 bps) or maker fees (0–4 bps) and adverse selection slippage if the "temporary" dislocation is actually fundamental price discovery.
5. **Operating Regimes**: Stationary, range-bound markets (`RANGING_NORMAL_VOL`, `RANGING_LOW_VOL`) with well-defined support and resistance levels.
6. **Stop Regimes**: High-momentum directional breakouts (`BREAKOUT_EXPANSION`), macro news shocks, or liquidity runs where fading price results in catching a falling knife.
7. **Destructive Risks**: Adverse selection during genuine regime breaks; asymmetric downside during cascading liquidations.
8. **Falsification Method**: Inability of the residual spread or price deviation to demonstrate statistical stationarity (Augmented Dickey-Fuller p-value > 0.05); negative net return under 20 bps roundtrip friction.
9. **Promotion Evidence**: Positive expectancy (> +0.15R) under 2x friction stress testing, win rate > 58%, and empirical stability across 200+ out-of-sample trade events.
10. **Retirement Evidence**: Three consecutive stop-loss hits resulting from strong trend continuation, or rolling 30-day profit factor < 0.90.

---

## 3. Breakout Expansion Engine (`BreakoutStrategy` / FAM-03)

1. **Market Inefficiency**: Volatility compression (coiling) creates order clustering above/below consolidation ranges. When broken, trapped counter-trend traders and breakout momentum buyers trigger rapid price expansion.
2. **Observable Data**: Rolling ATR, Donchian channels, Bollinger Band width (volatility squeeze), volume spikes, and order book bid/ask liquidity clusters.
3. **Return Mechanism**: Places conditional stop-entry orders at the consolidation boundaries to ride the explosive expansion of volatility into a new trend.
4. **Friction Costs**: Breakout entries often suffer high slippage (4–12 bps) due to thin liquidity at breakout points, coupled with taker fees.
5. **Operating Regimes**: Transitions from low-volatility compression into high-volatility expansion (`VOL_EXPANSION`, `TRANSITION_TO_TREND`).
6. **Stop Regimes**: Extended late-stage trends, low-liquidity ranges with frequent false breakouts (headfakes), and high-frequency noise environments.
7. **Destructive Risks**: Repeated false breakouts causing cumulative friction bleed; liquidity black holes on stop execution.
8. **Falsification Method**: Failure to demonstrate positive net R after removing the single largest windfall trade; failure to survive adversarial entry-delay stress testing (1-bar lag).
9. **Promotion Evidence**: Out-of-sample win rate > 40% with an average win-to-loss ratio > 2.5:1, yielding positive net Sharpe (> 1.0) under realistic fee assumptions.
10. **Retirement Evidence**: Strategy drawdowns persisting beyond 60 calendar days or consecutive false breakout rate exceeding 70%.

---

## 4. Relative Value Engine (`RelativeValueStrategy` / FAM-09)

1. **Market Inefficiency**: Pairs of economically linked crypto assets (e.g., L1 competitors, store-of-value vs smart contracts) share macro beta, but idiosyncratic order flow causes their price ratio to temporarily diverge.
2. **Observable Data**: Synchronous 1h/4h/1d closing prices of asset pairs (BTC/ETH, SOL/ETH, SOL/BTC), cointegration vectors, and rolling spread Z-scores.
3. **Return Mechanism**: Takes a market-neutral long-short position when the normalized spread deviates beyond 2.0 standard deviations, closing when the spread reverts to the mean.
4. **Friction Costs**: Double roundtrip friction across two legs (minimum 32–64 bps total), funding rate divergence between the long and short perpetual legs, and rebalancing transaction costs.
5. **Operating Regimes**: Macro regime consensus where crypto assets move under shared beta with stable historical correlation.
6. **Stop Regimes**: Structural decoupling events (e.g., regulatory action against one asset, protocol failure, ecosystem migration, hard forks).
7. **Destructive Risks**: Non-stationary spread drift (structural regime shift where spread diverges indefinitely without mean-reverting), leading to catastrophic double-leg losses.
8. **Falsification Method**: Engle-Granger two-step test failing to reject the null hypothesis of non-cointegration (p-value > 0.05); Ornstein-Uhlenbeck half-life exceeding 45 bars; negative net return under 32 bps baseline friction.
9. **Promotion Evidence**: Mathematically proven cointegration (p < 0.01) across 2+ years of data, stable OLS/TLS hedge ratios, and positive out-of-sample net return across both long and short spread legs.
10. **Retirement Evidence**: ADF test p-value rising above 0.10 on a rolling 90-day window; spread widening beyond 4.0 standard deviations without mean-reverting.

---

## 5. Basis Arbitrage Engine (`BasisStrategy` / FAM-06)

1. **Market Inefficiency**: Structural demand for leveraged upside in crypto futures markets creates a persistent premium of perpetual/quarterly futures over spot (contango), occasionally flipping to backwardation during panics.
2. **Observable Data**: Spot order book best bid/ask, perpetual/quarterly futures mark prices, contract expiration schedules, and lending rates.
3. **Return Mechanism**: Cash-and-carry arbitrage: Long physical/spot asset, short corresponding futures contract; locks in risk-free basis convergence at expiry or collects funding rate.
4. **Friction Costs**: Spot trading fees, futures trading fees, spot custody/withdrawal fees, futures settlement fees, and interest/borrowing costs.
5. **Operating Regimes**: High retail exuberance (wide contango > 10% annualized) or severe institutional hedge demand (steep backwardation).
6. **Stop Regimes**: Compressed basis regimes (< 3% annualized), where the expected yield is lower than the risk-free rate or funding volatility.
7. **Destructive Risks**: Liquidation of the short futures leg during parabolic upside spikes prior to basis convergence; exchange insolvency or custody freeze on spot.
8. **Falsification Method**: Basis yield failing to exceed the benchmark US Treasury risk-free rate plus 200 bps after deducting all entry, exit, and margin maintenance costs.
9. **Promotion Evidence**: Realized net yield exceeding 8% annualized with near-zero delta exposure (|Delta| < 0.01) over 90 consecutive calendar days.
10. **Retirement Evidence**: Convergence failure, exchange margin policy changes reducing capital efficiency below hurdle rate, or basis compression below 2% annualized.

---

## 6. Funding Rate Carry Engine (`FundingStrategy` / FAM-07)

1. **Market Inefficiency**: Perpetual futures contracts utilize periodic funding payments (every 8 hours) to tether perp prices to spot. When perpetual markets are net long, longs pay shorts a predictable cash flow.
2. **Observable Data**: Historical and predicted 8h funding rates, spot vs perp basis, open interest, and borrowing interest rates.
3. **Return Mechanism**: Holds a delta-neutral position (Long Spot, Short Perp); continuously harvests incoming funding payments credited to the short perp position.
4. **Friction Costs**: Entry and exit taker fees on both spot and perp (16–32 bps total setup cost), negative funding rate periods where shorts pay longs, and margin rebalancing friction.
5. **Operating Regimes**: Bullish sentiment with sustained positive funding rates (> 0.01% per 8h = ~10.9% annualized).
6. **Stop Regimes**: Bearish sentiment or sustained negative funding regimes, where shorts are penalized for maintaining positions.
7. **Destructive Risks**: Abrupt funding rate inversion, margin imbalance leading to liquidation of the short leg during explosive moves, and counterparty exchange failure.
8. **Falsification Method**: Realized funding receipts over a 1-year historical cycle failing to cover total turnover costs and spot borrowing fees.
9. **Promotion Evidence**: Sustained positive net carry (> 6% annualized net of all fees) with Sharpe ratio > 2.5 and maximum delta drawdown < 1.0%.
10. **Retirement Evidence**: Rolling 30-day average funding rate turning negative; exchange fee changes eliminating the margin of safety.

---

## 7. Cross-Venue Arbitrage Engine (`CrossVenueStrategy` / FAM-10)

1. **Market Inefficiency**: Fragmented liquidity across geographically and legally distinct exchanges causes identical digital assets to temporarily trade at different prices due to localized order flow imbalances.
2. **Observable Data**: L2 order book feeds from multiple venues (Binance, OKX, Bybit, Coinbase), network transfer times, and venue fee tiers.
3. **Return Mechanism**: Concurrently buys on the lower-priced venue and sells on the higher-priced venue; locks in the spread without directional market risk.
4. **Friction Costs**: Taker fees on both exchanges (8–20 bps combined), venue withdrawal/deposit network fees, and slippage on leg execution.
5. **Operating Regimes**: High market volatility with fragmented order flow across venues.
6. **Stop Regimes**: Calm, low-volatility markets where cross-venue spreads are tighter than combined two-venue taker fees.
7. **Destructive Risks**: Execution leg risk (one leg fills, the other fails or moves before execution), venue API outage, withdrawal freezes, or inventory rebalancing costs.
8. **Falsification Method**: Simulated execution modeling realistic network latency (> 50ms) revealing that cross-venue dislocations disappear before order execution.
9. **Promotion Evidence**: Proven profitability on paper forward paper trading with simulated 100ms API latency and realistic book depth consumption.
10. **Retirement Evidence**: Institutional market makers compressing inter-exchange spreads permanently below transaction fee hurdles.

---

## 8. Market Making Engine (`AvellanedaStoikov` / FAM-11)

1. **Market Inefficiency**: Natural market participants demand immediate execution and pay the bid-ask spread; market makers provide continuous liquidity and earn the spread premium.
2. **Observable Data**: Microsecond L2 order book depth, tick-level trade flow, realized volatility, and current inventory levels.
3. **Return Mechanism**: Posts simultaneous limit buy and sell orders around the reservation price derived from inventory skew; captures the spread when both sides are crossed.
4. **Friction Costs**: Exchange maker/taker fees, adverse selection costs (being filled immediately before a price move), and inventory carrying costs.
5. **Operating Regimes**: High-volume, range-bound markets with balanced two-sided retail trade flow.
6. **Stop Regimes**: Extreme directional momentum, news releases, flash crashes, or illiquid markets with wide, erratic spreads.
7. **Destructive Risks**: Toxic order flow / adverse selection (informed traders pick off stale quotes); catastrophic inventory accumulation during a one-way market.
8. **Falsification Method**: Backtesting against historical tick data showing that adverse selection losses exceed gross spread revenue; failure to operate profitably without exchange VIP rebates.
9. **Promotion Evidence**: Positive daily PnL over 30 days of forward simulation with strict inventory variance bounds (< 15% of max balance) and zero manual intervention.
10. **Retirement Evidence**: Market structural change resulting in persistent inventory skew and loss of VIP maker rebate status.

---

## 9. Options & Volatility Engine (`OptionsPricer` / FAM-08)

1. **Market Inefficiency**: Crypto options markets exhibit structural volatility smile/skew and variance risk premia, where implied volatility frequently trades at a premium to subsequently realized volatility.
2. **Observable Data**: Options chain quotes, strike prices, expirations, implied volatility surfaces, underlying spot prices, and interest rates.
3. **Return Mechanism**: Sells overvalued implied volatility via delta-hedged straddles/strangles, or purchases undervalued tails to hedge portfolio convexity.
4. **Friction Costs**: Wide options bid-ask spreads (often 2–5% of option premium), continuous delta-hedging transaction costs on the underlying perpetual contract.
5. **Operating Regimes**: Post-volatility spike regimes with high implied volatility collapse (`VOL_CRUSH`), or calm regimes with cheap tail risk protection.
6. **Stop Regimes**: Extreme liquidity evaporation, market gaps where continuous delta hedging is impossible, or regulatory restrictions on derivative venues.
7. **Destructive Risks**: Non-linear gamma risk (accelerating losses on explosive moves), vega shocks (implied volatility spiking dramatically), and pin risk at expiration.
8. **Falsification Method**: Failure to account for discrete hedging intervals and bid-ask spread friction in delta-hedging simulations, resulting in simulated profit turning into real loss.
9. **Promotion Evidence**: Mathematically consistent Greek calculations across the full surface and verified positive net return after hedging costs over 180 out-of-sample days.
10. **Retirement Evidence**: Structural widening of options bid-ask spreads rendering delta hedging uneconomic.

---

## 10. Hedging Engine (`PortfolioExposureDecomposer` & `HedgeGenerator`)

1. **Market Inefficiency**: A portfolio of diverse crypto strategies accumulates unintentional systematic exposures (market beta, directional delta, funding exposure) that dominate idiosyncratic alpha.
2. **Observable Data**: Realtime portfolio positions, asset beta to BTC/ETH, rolling covariance matrices, and derivative hedge venue liquidity.
3. **Return Mechanism**: Does not seek to generate positive return directly; generates overlay short/long derivative orders to eliminate systematic factor risk, preserving net alpha while reducing portfolio variance.
4. **Friction Costs**: Trading fees on hedge instruments, slippage during hedge adjustments, and drag from basis/funding on hedge positions.
5. **Operating Regimes**: High portfolio concentration, high macro uncertainty, or when gross exposure threatens risk budget limits.
6. **Stop Regimes**: When total portfolio exposure is negligible, or when hedging costs exceed the expected drawdown reduction benefits.
7. **Destructive Risks**: Over-hedging (locking in permanent capital loss), basis breakdown (hedge asset decouples from portfolio assets), and execution lag during violent market dislocations.
8. **Falsification Method**: Empirical demonstration that adding the hedge overlay increases maximum drawdown or reduces risk-adjusted return (Sharpe/Sortino) compared to the unhedged portfolio over a full cycle.
9. **Promotion Evidence**: Documented reduction in portfolio standard deviation (> 25%) and tail drawdown (> 30%) with a drag on total return of less than 2% annually.
10. **Retirement Evidence**: Persistent hedge tracking error (> 15% discrepancy between portfolio delta and hedge response) or prohibitive hedge transaction costs.

---

## 11. Portfolio Risk Budget Allocation (`RiskBudgetAllocator`)

1. **Market Inefficiency**: Naive equal-weighted or capital-weighted allocations over-allocate to high-volatility, correlated strategies, leading to simultaneous drawdowns during adverse regimes.
2. **Observable Data**: Strategy return histories, rolling covariance matrices, current market regime classifications, and individual strategy uncertainty scores.
3. **Return Mechanism**: Allocates risk budget (portfolio heat) proportionally to expected edge, inverse variance, and orthogonal factor contribution; cuts allocation to zero when no genuine edge is present.
4. **Friction Costs**: Turnover transaction costs from frequent rebalancing.
5. **Operating Regimes**: Active across all market regimes; dynamically adjusts allocations from 100% risk capacity down to 0% (full cash).
6. **Stop Regimes**: Never stops operating; maintains sovereign authority to allocate zero capital (`ALLOCATION_ZERO`).
7. **Destructive Risks**: Model estimation error in covariance matrices (Markowitz curse); sudden correlation breakdown during liquidity panics (all correlations approach 1.0).
8. **Falsification Method**: Allocation outperforming an equal-weight naive baseline only in backtest optimization, but underperforming naive allocation out-of-sample.
9. **Promotion Evidence**: Superior out-of-sample Calmar and Sharpe ratios compared to both 1/N equal weighting and individual strategy performance.
10. **Retirement Evidence**: Covariance shrinkage model failure or persistent violation of the hard 3.00% portfolio heat ceiling.

---

## 12. Smart Order Routing & Execution OS (`ExecutionPlanner` / SOR)

1. **Market Inefficiency**: Large orders executed naively as market orders suffer severe price impact, adverse selection, and unnecessary exchange fees.
2. **Observable Data**: L2 order book depth, tick volume, recent trade prints, venue fee schedules, and historic slippage models.
3. **Return Mechanism**: Slices parent orders into intelligent child orders (TWAP, VWAP, Iceberg, Passive Limit); captures liquidity rebates and minimizes market impact.
4. **Friction Costs**: Venue execution fees, latency overhead, and opportunity cost of unfilled limit orders (adverse selection on uncompleted orders).
5. **Operating Regimes**: Active for all order executions across all market environments.
6. **Stop Regimes**: Emergency market orders during kill-switch liquidations (where speed of de-risking supersedes price optimization).
7. **Destructive Risks**: Execution stall (child orders fail to fill while market runs away), order routing loops, and exchange API connection failures.
8. **Falsification Method**: Measured implementation shortfall exceeding naive baseline market order execution costs on sample test orders.
9. **Promotion Evidence**: Statistically verified reduction in execution slippage (> 3 bps saved on average) across 500+ executed child orders.
10. **Retirement Evidence**: Execution latency degradation exceeding 250ms or failure to route around venue rate limits and downtime.

---

## 13. Market Data Engine (`RealtimeStreamManager` & Data Pipeline)

1. **Market Inefficiency**: Crypto market data feeds are prone to dropped packets, sequence gaps, timestamp jitter, and exchange-specific formatting quirks that corrupt quantitative models.
2. **Observable Data**: Raw exchange WebSockets and REST endpoints for trades, order books, candles, funding rates, and open interest.
3. **Return Mechanism**: Foundational infrastructure; does not generate returns directly, but guarantees causal integrity, preventing garbage-in-garbage-out model failure.
4. **Friction Costs**: Network bandwidth, hardware memory, and storage costs for continuous data capture.
5. **Operating Regimes**: 24/7/365 continuous operation across all market conditions.
6. **Stop Regimes**: Never stops; executes automated reconnection and gap-recovery protocols during exchange outages.
7. **Destructive Risks**: Silent sequence corruption, undetected clock drift, and lookahead timestamp leakage into historical datasets.
8. **Falsification Method**: Detection of any timestamp inversion, unhandled sequence gap, or bar timestamp overlapping with forward execution.
9. **Promotion Evidence**: Zero detected sequence gaps and zero integrity violations across 30 consecutive days of live multi-venue stream ingestion.
10. **Retirement Evidence**: Unresolvable data corruption or deprecated venue APIs that cannot be certified.

---

## 14. Research Engine & Strategy Graveyard (`CausalAuditGate` & Lifecycle)

1. **Market Inefficiency**: Quantitative research is intrinsically susceptible to p-hacking, overfitting, lookahead bias, and survival bias, producing illusory backtest profits.
2. **Observable Data**: Historical candidate signals, execution logs, parameter spaces, and out-of-sample data partitions.
3. **Return Mechanism**: Eliminates false positives before capital is at risk; preserves all historical failures in an immutable graveyard to prevent repeated mistakes.
4. **Friction Costs**: Computational resources for walk-forward validation, Monte Carlo permutations, and causal audits.
5. **Operating Regimes**: Operates during all offline and automated research phases.
6. **Stop Regimes**: Never stops; continuously evaluates active strategies for performance degradation.
7. **Destructive Risks**: Softening of validation gates to accommodate pet hypotheses; leakage of out-of-sample data into model training.
8. **Falsification Method**: Synthetic insertion of known lookahead bias; failure of the audit gate to detect and reject the poisoned strategy.
9. **Promotion Evidence**: Rigorous rejection of 90%+ of generated candidates; only robust, causal strategies pass through to paper trading.
10. **Retirement Evidence**: Any bypass of the immutable graveyard or failure to record a falsified candidate.

---

## 15. Market Regime Classification Engine (`RegimeClassificationEngine`)

1. **Market Inefficiency**: Market dynamics alternate between trending, range-bound, high-volatility, and deleveraging regimes. Strategies designed for one regime will bleed capital in another.
2. **Observable Data**: Multi-timeframe volatility (ATR, realized volatility), trend strength indicators (ADX, moving average slopes), order book depth, and funding rate polarity.
3. **Return Mechanism**: Filters strategy signals so that only strategies mathematically suited to the current regime are permitted to deploy risk.
4. **Friction Costs**: Minor signal delay caused by confirmation requirements for regime transitions.
5. **Operating Regimes**: Evaluates market conditions across all assets and timeframes continuously.
6. **Stop Regimes**: Operates continuously; outputs `UNKNOWN` regime when indicators conflict, triggering automatic risk reduction.
7. **Destructive Risks**: Regime lag (identifying a regime after it has already reversed), frequent regime thrashing causing rapid allocation changes.
8. **Falsification Method**: Showing that regime-filtered strategy portfolios underperform un-filtered portfolios over out-of-sample market cycles.
9. **Promotion Evidence**: Significant reduction in strategy drawdown (> 20%) achieved by disabling strategies during their identified adverse regimes.
10. **Retirement Evidence**: Inability to identify major market transition events within 3 bars of occurrence.

---

## 16. Unified Risk Engine & Kill Switch (`UnifiedRiskEngine`)

1. **Market Inefficiency**: Unchecked algorithmic trading systems inevitably experience tail events, software bugs, execution loops, or exchange outages that can cause total portfolio ruin.
2. **Observable Data**: Account equity, intraday PnL, gross leverage, individual position sizes, open orders, and portfolio heat.
3. **Return Mechanism**: Capital preservation is the prerequisite for all quantitative returns; prevents catastrophic drawdowns and ensures system survival.
4. **Friction Costs**: Occasional premature trade exit or missed opportunity when risk limits are approached.
5. **Operating Regimes**: Sovereign authority across all regimes, 24/7.
6. **Stop Regimes**: Never stops under any circumstances; cannot be bypassed by any user, strategy, or algorithm.
7. **Destructive Risks**: Failure of the kill-switch trigger mechanism, stale price data blinding the risk monitors, or unhandled exceptions in risk evaluation code.
8. **Falsification Method**: Simulated stress test injecting orders that violate limits; failure of the engine to reject the illegal orders.
9. **Promotion Evidence**: 100% rejection rate of non-compliant orders and instant execution of emergency halt in under 5ms during automated tests.
10. **Retirement Evidence**: Any single instance of an order bypassing risk checks to reach execution.

---

## 17. Small Account Safety & Economic Viability

1. **Market Inefficiency**: Small accounts (e.g., $100) face disproportionate friction because minimum exchange lot sizes, fixed fees, and spreads consume an unsustainable percentage of the risk budget.
2. **Observable Data**: Account equity ($USD), venue minimum order sizes ($USD notional and base asset lot), taker/maker fee schedules, and asset bid-ask spread.
3. **Return Mechanism**: Prevents capital destruction by mathematically proving whether a trade is economically viable before execution; refuses trades on unviable accounts (`INSUFFICIENT CAPITAL / NO TRADE`).
4. **Friction Costs**: Zero friction incurred because unprofitable trades are prevented.
5. **Operating Regimes**: Active whenever account equity is below the minimum viable capital threshold.
6. **Stop Regimes**: Automatically transitions to standard risk sizing once account equity is sufficient to support proper position sizing.
7. **Destructive Risks**: Forcing small accounts to trade by ignoring minimum order constraints, leading to massive over-leverage and rapid ruin.
8. **Falsification Method**: Account simulation demonstrating that trading a $100 account under normal strategy parameters results in negative net return purely due to fee and lot-size drag.
9. **Promotion Evidence**: Complete prevention of unviable trades on accounts under $500 while maintaining mathematically sound risk sizing on accounts with adequate capital.
10. **Retirement Evidence**: Failure to detect that transaction costs exceed 20% of the trade's expected risk budget.
