# Changelog

All notable changes to the Crypto Quantitative Systems Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to Semantic Versioning.

## [Unreleased] - Next
### Planned
- **Product 04 (Research Laboratory)**: Market replay engine, historical backtesting, and performance attribution pipeline.

## [v0.3.0] - Foundation Complete (Day 30)
### Added
- **Product 03 (Risk Firewall)**: Immutable `1.0%` equity risk caps, multi-tier drawdown circuits (`-3%` daily, `-6%` weekly, `-10%` systemic), redundant R:R gate, and robust risk rejection telemetry pipeline.
- **Product 02 (Strategy Lifecycle)**: Stateful multi-candle candidate tracking (`CandidateTracker`, `ActiveTradeManager`), formalized structural trade proposals, and dual independent hypotheses (Pullback Riding and Continuation Riding).
- **Product 01 (Market Intelligence)**: 100% test coverage and formal acceptance for the core deterministic structural layer (Swings, Liquidity, KeyZones, Phases, Trend).
- **Documentation**: Comprehensive domain architecture and explicit disclaimers regarding research-first methodology.

### Verified
- **145/145** automated repository tests passing across the `market_intelligence`, `strategy_engine`, and `risk_engine` domains.
