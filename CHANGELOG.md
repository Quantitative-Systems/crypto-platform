# Changelog

All notable changes to the Crypto Quantitative Systems Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to Semantic Versioning.

## [Unreleased] - Next
### Planned
- **Product 05 (Live Execution Gateway)**: Real-time exchange WebSocket/REST connectivity and automated order routing.

## [v0.4.0] - Research & Backtesting Laboratory Complete (Day 32)
### Added
- **Product 04 (Research Laboratory)**:
  - Causal multi-timeframe market replayer (`CausalReplayer`) with zero-lookahead guarantees across canonical Sets 1 to 4 (`TimeframeAligner`).
  - Realistic execution & friction simulator (`ExecutionSimulator`, `TradeLedger`) supporting limit orders, taker slippage, maker/taker exchange fees, and conservative adverse-first intrabar collision handling.
  - Performance metrics and attribution engine (`MetricsEngine`, `ExitAttributionEngine`, `FailureAnalyzer`) computing Expectancy, Profit Factor, Max Drawdown, Sharpe, Sortino, R-distribution, and semantic zero-division edge cases.
  - 24-Baseline research matrix runner (`MatrixRunner`) orchestrating 2 Hypotheses × 4 Timeframe Sets × 3 Assets (BTC, ETH, SOL) in memory-quarantined streams.
  - MTF structural trailing comparative study (`TrailingABExperiment`) measuring empirical edge delta between Baseline A (No Trailing) and Baseline B (With Trailing).
  - Reproducible artifact exporter (`ArtifactExporter`) writing JSON provenance traces to `research/results/`.

### Verified
- **155/155** automated repository tests passing with zero regressions across `market_intelligence`, `strategy_engine`, `risk_engine`, and `research`.
### Added
- **Product 03 (Risk Firewall)**: Immutable `1.0%` equity risk caps, multi-tier drawdown circuits (`-3%` daily, `-6%` weekly, `-10%` systemic), redundant R:R gate, and robust risk rejection telemetry pipeline.
- **Product 02 (Strategy Lifecycle)**: Stateful multi-candle candidate tracking (`CandidateTracker`, `ActiveTradeManager`), formalized structural trade proposals, and dual independent hypotheses (Pullback Riding and Continuation Riding).
- **Product 01 (Market Intelligence)**: 100% test coverage and formal acceptance for the core deterministic structural layer (Swings, Liquidity, KeyZones, Phases, Trend).
- **Documentation**: Comprehensive domain architecture and explicit disclaimers regarding research-first methodology.

### Verified
- **145/145** automated repository tests passing across the `market_intelligence`, `strategy_engine`, and `risk_engine` domains.
