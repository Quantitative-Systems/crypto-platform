from research.experiments.run_canonical_v21_diagnostic import *
res = run_phase_1()
for r in res:
    if r.overall:
        print(f"{r.symbol} {r.timeframe}: {r.overall.performance.trade_count} trades")
