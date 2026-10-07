# H-REPRO-01 — Certified Baseline Reproducibility / Engine Drift

## Status
INVALIDATED

## Research question
Can the stored certified EXP_TARGET_STRUCTURAL_01 result be reproduced bit-comparably on the current working tree?

## Null hypothesis
Certified results are reproducible on current tree.

## Falsification criteria
Material deviation from stored certified metrics.

## Mechanism summary
Recompute composite base + STRUCTURAL_OBJECTIVE on the current tree and diff vs stored certified file.

## Decision
DRIFT DETECTED (-16.54R N=79 vs stored certified). Invalidated as evidence of engine drift; negative evidence preserved; blocks promotion of dependent legacy results.

- Created: 2026-09-19T08:02:37.442157+00:00
