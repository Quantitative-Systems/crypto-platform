# Forensic Repository Inventory

## Verified M2 Baseline
- Baseline commit: `7d96b77`
- Verified to contain core operational acceptance tests and continuous paper daemon.

## Useful New Architecture (To Retain)
- `market_data/certified_research_universe.py`
- `market_data/data_acquisition_governor.py`
- `market_data/universal_data_fabric.py`
- `market_intelligence/continuous_regime_engine.py`
- `market_intelligence/opportunity_detector.py`
- `portfolio_engine/capital_allocator.py`
- `portfolio_engine/portfolio_intelligence.py`
- `production/autonomous_platform_orchestrator.py`
- `production/economic_truth_engine.py`
- `production/live_trader.py`
- `platform_core/promotion_governor.py`
- `research/discovery_lab/relative_value_config.py`
- `research/discovery_lab/relative_value_engine.py`
- `research/experiments/run_relative_value_baseline.py`
- `risk_engine/autonomous_risk_governor.py`
- `risk_engine/unified_risk_engine.py`

## Out of Scope for Current Milestone / Experimental (To Quarantine)
- `billing/` (SaaS/Support)
- `web_app/` (SaaS/Support)
- `multi_tenancy/` (SaaS/Support)
- `derivatives_engine/` (Experimental without data)
- `market_making/` (Experimental without causal/friction models)
- `low_latency/` (Experimental without economic justification)
- `execution_gateway/` (Architecture theater, not economically validated)
- `security/` (Support system)
- `observability/` (Support system)
- `disaster_recovery/` (Support system)

## Action Plan
1. Move the quarantined directories to `quarantine/`.
2. Refocus development exclusively on the empirical alpha discovery engine, relative value (RV) research, and the core economic truth engine.
