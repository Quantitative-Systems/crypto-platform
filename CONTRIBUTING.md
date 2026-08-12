# Contributing to Crypto Quantitative Systems Platform

We welcome contributions from quantitative developers, systems engineers, and researchers.

## Core Engineering Principles
Before submitting a pull request, ensure your contribution adheres to the platform's core engineering laws:
1. **Temporal Causality**: Do not introduce lookahead bias. You cannot use future data to make historical decisions.
2. **Deterministic Reproducibility**: The same inputs must always yield the same outputs.
3. **Domain Isolation**: Ensure strict unidirectional dependency. Do not leak downstream information into upstream engines.
4. **Fail Closed**: Handle ambiguous states safely rather than making assumptions.

## Development Setup
1. Fork and clone the repository.
2. Install dependencies (environment instructions provided in relevant engine directories).
3. Ensure all tests pass by running: `PYTHONPATH=. pytest`

## Pull Request Guidelines
- Create a feature branch with a descriptive name (`feat/market-structure-enhancement`).
- Ensure all 145+ tests pass.
- Do not introduce optimization parameters without robust justification and corresponding test logic.
- Follow the exact architectural separation defined in the README.

*Note: This platform is not currently accepting "strategy-only" PRs without accompanying rigorous testing frameworks.*
