import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open(r'research/results/PHASE_Q_FRACTAL_VALIDATION/master_phase_q_fractal_validation.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print('=== ALIGNMENT CONDITIONED ===')
for k, v in d['alignment_conditioned_performance'].items():
    print(f"{k:25s} N={v['total_trades']:>5} ExpR={v['expectancy_r']:>7.4f} TotR={v['total_r']:>8.2f} PF={v['profit_factor']:>6.3f} WR={v['win_rate']*100:>5.1f}%")

print('\n=== CROSS-SET SUPPORT ===')
for k, v in d['cross_set_support_performance'].items():
    print(f"{k:25s} N={v['total_trades']:>5} ExpR={v['expectancy_r']:>7.4f} TotR={v['total_r']:>8.2f} PF={v['profit_factor']:>6.3f} WR={v['win_rate']*100:>5.1f}%")

print('\n=== CONFIDENCE SWEEP ===')
for k, v in d['confidence_threshold_sweep'].items():
    print(f"{k:25s} N={v['total_trades']:>5} ExpR={v['expectancy_r']:>7.4f} TotR={v['total_r']:>8.2f} PF={v['profit_factor']:>6.3f} TrimR={v['trimmed_expectancy_r']:>7.4f}")

print('\n=== DEDUPLICATION ANALYSIS ===')
print(json.dumps(d['deduplication_analysis'], indent=2))

print('\n=== SCALE AGGREGATES ===')
for k, v in d['scale_aggregates'].items():
    print(f"{k:10s} N={v['total_trades']:>5} ExpR={v['expectancy_r']:>7.4f} TotR={v['total_r']:>8.2f} PF={v['profit_factor']:>6.3f} WR={v['win_rate']*100:>5.1f}%")

print('\n=== ASSET AGGREGATES ===')
for k, v in d['asset_aggregates'].items():
    print(f"{k:10s} N={v['total_trades']:>5} ExpR={v['expectancy_r']:>7.4f} TotR={v['total_r']:>8.2f} PF={v['profit_factor']:>6.3f} WR={v['win_rate']*100:>5.1f}%")

print('\n=== PHASE AGGREGATES ===')
for k, v in d['phase_aggregates'].items():
    print(f"{k:15s} N={v['total_trades']:>5} ExpR={v['expectancy_r']:>7.4f} TotR={v['total_r']:>8.2f} PF={v['profit_factor']:>6.3f} WR={v['win_rate']*100:>5.1f}%")

print('\n=== STATISTICAL VALIDATION ===')
print(json.dumps(d['statistical_validation'], indent=2))
