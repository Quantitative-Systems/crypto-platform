# Changelog

All notable changes to the Crypto Quantitative Systems Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to Semantic Versioning.

## [Unreleased] - Day 48 repository closeout (document / freeze / publish)

### Added
- **Closeout report (`research/results/DAY_48_REPOSITORY_CLOSEOUT.md`)**:
  full IMPLEMENTED / PARTIAL / PLANNED / NOT inventory, 604/2/14 test
  record with failure diagnosis, Phase D findings, reconciliation status,
  limitations, GitHub readiness, and future fractal/composite hypotheses
  (recorded only, not implemented).
- **Portfolio summary (`docs/SOCIAL_PORTFOLIO_SUMMARY.md`)**: short factual
  summary for later social use (not auto-published, no profit claims).
### Added
- **Foundation Registry (`research/foundation_registry.py`)**: Machine-readable inventory of the canonical `HTF BIAS → MTF SETUP → LTF ENTRY` foundation. Reads every bias / setup / entry / stop / target / trailing family live from `ComponentRegistry`, classifies each one, flags registry aliases explicitly, and emits `research/results/FOUNDATION_MANIFEST.json`. `classification_complete` fails loudly if a new family is left unclassified.
- **Foundation Specification (`docs/FOUNDATION_HTF_BIAS_MTF_SETUP_LTF_ENTRY.md`)**: Canonical reference for the 6-Set ladder, the full family inventory per layer, the risk contract (1% risk, 1:4 planned RR, LTF stop → HTF target → MTF trailing), the news blackout policy, and the declared win-rate / profit-factor targets stated explicitly as unproven acceptance gates with breakeven arithmetic.
- **Foundation test suite (`tests/unit/research/test_foundation_registry.py`)**: 16 tests asserting the 6-Set ladder, config↔replayer↔grammar agreement, strict hierarchy, complete family classification, alias reporting, risk-constant parity with `risk_engine`, news-window parity with the live `NewsProvider`, and target arithmetic.

### Fixed
- **Canonical Timeframe Sets reconciled to the authoritative 6-Set ladder.** `config/timeframe_sets.py::CANONICAL_6_TIMEFRAME_SETS` is now keyed `SET_1`..`SET_6` and `research/replayer/timeframe_aligner.py` **derives** its `CANONICAL_TIMEFRAME_SETS` from it, eliminating a second hard-coded copy. The replayer previously exposed only 5 sets with stale numbering (`SET_5 = 15m/5m/1m`), so `SET_5 (1H → 15M → 5M)` was entirely absent and `SET_6 (15M → 5M → 1m)` was mis-numbered. All three layers (config, replayer, strategy grammar) now agree, verified by test.
- **`docs/CANONICAL_STRATEGY_SPECIFICATION.md` §29–§33, §50, §60, §64** updated from five to six timeframe sets, with `SET 5 — SHORT-TERM INTRADAY` inserted and the scalping set renumbered to `SET 6`.
- **`research/analytics/run_research_integrity_audit.py`** now reports the audited set count dynamically instead of hard-coding "5".
- **Stale test assertions** in `test_timeframe_aligner.py` and `test_strategy_ontology.py` updated to the 6-Set ladder (the legacy 5-Set alias table `TIMEFRAME_SETS` is retained for historical artifacts).

### Planned
- **Product 05 (Live Execution Gateway)**: Real-time exchange WebSocket/REST connectivity and automated order routing.

## [v0.5.0] - Institutional Quantitative Platform Standardization
### Standardized & Refactored
- **Professional Purpose-Driven Taxonomy**: Standardized all documentation, research reports, test suites, and engine modules under institutional, purpose-driven naming conventions.
- **Purged Legacy Jargon**: Completely eliminated ephemeral day tags, buzzword prefixes (`apex`, `alpha`), and colloquial naming across the repository.
- **Comprehensive Verification**: Verified full 15-stream backtest on the 2021–2022 Development partition, with zero data leakage and strict adverse-first execution physics.
- **Suite Expansion**: All 401 unit, integration, and regression tests passing with 100% green status.

## [v0.4.0] - Research & Backtesting Laboratory Complete (Phase 4 Completion)
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
