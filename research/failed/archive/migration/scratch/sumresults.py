import json, glob, os
results = []
for f in sorted(glob.glob('scratch/*_dev_results.json')):
    try:
        d = json.load(open(f))
        a = d.get('aggregate_performance', {})
        n = a.get('total_trades', 0)
        if n > 0:
            results.append((
                os.path.basename(f).replace('_dev_results.json', ''),
                n, a.get('net_r', 0.0), a.get('profit_factor', 0.0),
                a.get('win_rate', 0.0), a.get('expectancy', 0.0),
                a.get('max_drawdown_r', 0.0)
            ))
    except Exception as e:
        print(f'ERR {f}: {e}', flush=True)

results.sort(key=lambda x: x[2], reverse=True)
print(f'{"EXPERIMENT":55s} {"N":>5s} {"NetR":>8s} {"PF":>5s} {"WR%":>5s} {"Exp":>7s} {"DD_R":>6s}')
print('-'*95)
for r in results[:50]:
    name,n,netr,pf,wr,exp,dd = r
    print(f'{name:55s} {n:5d} {netr:+8.3f} {pf:5.2f} {wr:5.0f} {exp:+7.4f} {dd:6.2f}')
