import json, glob, os

files = sorted(glob.glob('scratch/*_dev_results.json') + glob.glob('scratch/EXP_*.json'))
print(f'Total result files: {len(files)}')
print()

results = []
for f in files:
    try:
        d = json.load(open(f))
        agg = d.get('aggregate_performance', {})
        manifest = d.get('manifest', {})
        results.append({
            'file': f,
            'basename': os.path.basename(f),
            'N': agg.get('total_trades', 0),
            'NetR': agg.get('net_r', 0),
            'WR': agg.get('win_rate', 0),
            'PF': agg.get('profit_factor', 0),
            'config': manifest.get('config_hash', '?'),
            'stop': manifest.get('stop_anchor_mode', '?'),
            'mit_check': manifest.get('enable_historical_mitigation_check', '?'),
        })
    except Exception as e:
        print(f'ERROR {f}: {e}')

# Sort by NetR descending
results.sort(key=lambda x: x['NetR'], reverse=True)

print(f"{'File':<55} {'N':>4} {'NetR':>7} {'WR%':>6} {'PF':>5} {'config':>12} {'stop':>18} {'mit':>3}")
print('-' * 115)
for r in results:
    print(f"{r['basename']:<55} {r['N']:>4} {r['NetR']:+7.2f} {r['WR']:>5.1f} {r['PF']:>5.2f} {r['config']:>12} {r['stop']:>18} {str(r['mit_check']):>3}")

print()
print(f'{"STRONGEST RESULTS":-^80}')
print(f"{'File':<55} {'N':>4} {'NetR':>7} {'WR%':>6} {'PF':>5} {'config':>12} {'stop':>18} {'mit':>3}")
print('-' * 115)
strong = [r for r in results if r['NetR'] > 0]
for r in sorted(strong, key=lambda x: x['NetR'], reverse=True):
    print(f"{r['basename']:<55} {r['N']:>4} {r['NetR']:+7.2f} {r['WR']:>5.1f} {r['PF']:>5.2f} {r['config']:>12} {r['stop']:>18} {str(r['mit_check']):>3}")

print()
print(f'{"NEGATIVE RESULTS":-^80}')
print(f"{'File':<55} {'N':>4} {'NetR':>7} {'WR%':>6} {'PF':>5} {'stop':>18} {'mit':>3}")
print('-' * 115)
neg = [r for r in results if r['NetR'] <= 0]
for r in sorted(neg, key=lambda x: x['NetR']):
    print(f"{r['basename']:<55} {r['N']:>4} {r['NetR']:+7.2f} {r['WR']:>5.1f} {r['PF']:>5.2f} {r['stop']:>18} {str(r['mit_check']):>3}")
