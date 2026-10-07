# QCP — portfolio summary (factual, do not publish automatically)

I built QCP (Quantitative Crypto Platform): a reproducible quantitative
research system in Python — causal backtesting, execution/friction modelling,
risk governance, and adversarial falsification across crypto markets.

- Modular strategy grammar (HTF bias -> MTF setup -> LTF entry -> SL/TP/
  trailing) evaluated point-in-time with zero lookahead.
- Forensic execution study: reproduced a 77-trade DEV baseline (+1.64R gross
  / -22.64R net), showed a target-R sweep was inoperative, and proved
  fill-model changes shift trade populations — all negative, all preserved.
- Engineering: 604/620 tests passing with 2 documented failures + 14
  quarantine import errors; SHA-256 data lineage; fail-closed production
  gate ($0.00 live capital); negative results kept as first-class artifacts.

No profitability claimed — validated alpha: none. That honest null result is
the point: evidence first, reproduction second, validation third.
