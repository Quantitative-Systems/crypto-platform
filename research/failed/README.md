# Historical Research Archive

This directory contains previous experiments, rejected hypotheses, failed
implementations, forensic investigations, and superseded research artifacts
retained for reproducibility and research history.

> **failed ≠ deleted. failed ≠ useless.**
> Negative results are part of the research record. They are the reason the
> current engine (see `../../qcp_platform/`) is built the way it is: strict
> walk-forward partitions, always-on cost modeling, explicit rejection
> reporting, and a governed paper-trading promotion path.

## Status

This archive is **not installed, not imported by the current research engine,
and not part of the test suite.** It exists for the record — to document what
was tried, why it was rejected, and to prevent rediscovering the same dead
ends.

Nothing in this directory should be assumed to work, be profitable, or meet
the quality standards of the current engine. Numerical results here are
historical measurements from superseded code and configurations; they are
preserved as evidence, not as claims.

## What is preserved

| Content | Examples |
|---|---|
| Superseded engine implementations | `platform_core/`, `strategy_engine/`, `portfolio_engine/`, `risk_engine/` |
| Rejected hypotheses & registries | `hypotheses/`, `hypotheses_registry_active/` |
| Failed experiments & forensic audits | `experiments/`, `analytics/`, `results/` |
| Strategy family definitions | `tp_families.py`, `sl_families.py`, `trailing_families.py`, `entry_families.py` |
| Data-lineage & integrity audits | `docs/`, `results/telemetry/` |
| Archived scratch analysis | `archive/migration/scratch/` |

## Conventions

- Files are preserved **verbatim**: original filenames, original code, and
  original numerical results are retained. Internal or development-era naming
  inside these files is historical and intentionally left as-is.
- The current, maintained research engine lives in `../../qcp_platform/`.
  Its current measured results live in `../../research/results/qcp_platform/`.
- Do not import from this directory. Do not use this code for new research.
- Do not alter historical conclusions or numerical outputs; add new analysis
  files alongside them instead.
