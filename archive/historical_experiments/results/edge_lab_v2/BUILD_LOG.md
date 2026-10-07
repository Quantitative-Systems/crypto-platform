# QCP Edge Lab — profitable-edge build log (research-only, $0 live capital)

## What was wrong (forensics, not opinions)
- Canonical stack enforced 6R (strategy_candidate_v2) / 4R (risk firewall)
  planned-RR floors. Structural report: 5,246 firewall rejections -> 77 trades,
  friction 1478% of gross. Edge was filtered to death, then eaten by costs.
- SET_5 (5m) / SET_6 (1m) cache is 10-35 days. Median ATR: 5m=12.6bps,
  1m=3.3bps. Roundtrip cost ~22bps = 87% / 332% of a 2xATR stop. No signal
  survives; honest verdict is NO_TRADE, not a tuned "winner".
- v1 sweep (60 streams, DEV->VAL->OOS, 1.5-3R targets): only SET_1/SET_2
  showed DEV+/VAL+/OOS+; SET_4/5/6 decayed or were negative everywhere.

## What was built (this session, causal + cost-aware)
- `research/edge_lab/`: indicators / families / engine / sweep / runner /
  runner_v2 / filters / families_v2 / promotion / improve / portfolio /
  cli / promote_cli. Next-bar-open fills, adverse-first SL/TP, taker+slip+
  spread on both sides, one position/stream, DEV select -> VAL confirm ->
  OOS report (OOS never tuned).
- V2 adds: ATR-percentile expansion gate, trend-strength gate, per-set
  minimum-stop cost floor (SET_6 correctly returns NO_DEV_CANDIDATE).

## V2 results (frozen, reproducible)
- Command: `PYTHONPATH=. python3 -m research.edge_lab.promote_cli`
- Ledger: `research/results/edge_lab_v2/edge_lab_v2.json`,
  `summary.csv`, `promotion.json`.
- 6 streams PROMOTABLE_PAPER_ONLY (all survive +50% cost shock, bootstrap
  P(positive OOS edge) 0.65-0.98, DD<=30R, sign-stable DEV/VAL/OOS):

  BTC/SET_2 BREAK50 atr2.5/tgt3.0 DEV 0.535 VAL 0.177 OOS 0.203 shock 0.168
  SOL/SET_3 BREAK20 atr2.5/tgt3.0 DEV 0.140 VAL 0.056 OOS 0.050 shock 0.013
  BNB/SET_2 BREAK20 atr1.5/tgt3.0 DEV 0.592 VAL 0.198 OOS 0.268 shock 0.216
  XRP/SET_2 BREAK50 atr3.0/tgt3.0 DEV 0.290 VAL 0.061 OOS 0.512 shock 0.487
  ADA/SET_2 BREAK50 atr2.5/tgt3.0 DEV 0.379 VAL 0.501 OOS 0.384 shock 0.363
  LINK/SET_2 BREAK20 atr2.5/tgt2.5 DEV 0.211 VAL 0.115 OOS 0.527 shock 0.499

- OOS paper portfolio (6 streams, 0.25% risk/stream): +59.2R at 1% units
  = +14.8R at paper risk (~+3.7% OOS window, costs included).
- 54/60 REJECTED (honest): all SET_4short-horizon intraday decay, all
  SET_5/SET_6 cost-blocked or negative — reported, not hidden.

## Self-improving / future-proof loop (implemented, not promised)
- `improve.py::improve()`: re-sweeps same frozen grid on new data, keeps
  champion unless challenger wins on VAL with OOS sign agreement.
  Re-running after cache growth auto re-evaluates SET_5/SET_6.
- `promotion.py::evaluate()`: 7-dimension gate (data/alpha/stats/WFR/
  cost-shock/sign-stability/drawdown). Promotion = PAPER ONLY.
- `portfolio.py::PaperPortfolio`: 0.25%/stream, max 3 concurrent, 1% heat,
  -3R daily halt, 6R stream retire. Order submission stays DISABLED;
  live capital $0.00.

## What "profitable across all sets/assets" honestly means here
- NOT achieved and NOT claimable: SET_5/SET_6 cannot be profitable on
  22bps costs with 7-25bps stops; SET_4 shows no stable edge in this data.
  Claiming otherwise would require weakening costs or overfitting OOS.
- Achieved: a governed, causal, cost-aware machine that (a) found the
  tradeable pocket (daily/4h Donchian expansion, 6 streams), (b) rejects
  everything else with reasons, (c) improves itself as data grows, and
  (d) can only paper-trade under kill-switches. That is the profitable-edge
  platform: edge where it exists, refusal where it does not.
