import json, glob, os

def get_ap(f):
    try:
        d = json.load(open(f))
        ap = d.get('aggregate_performance', {})
        man = d.get('manifest', {})
        return {
            'file': os.path.basename(f),
            'N': ap.get('total_trades', -1),
            'NetR': ap.get('net_r', 0),
            'PF': ap.get('profit_factor', 0),
            'WR': ap.get('win_rate', 0),
            'treat': man.get('treatment', ''),
            'config': man.get('config_hash', ''),
            'git': man.get('git_commit', '')[:7],
        }
    except Exception as e:
        return {'file': os.path.basename(f), 'error': str(e)[:60]}

print("FILE".ljust(45), "N".rjust(5), "NetR".rjust(8), "PF".rjust(6), "WR".rjust(6), "  Treatment / Config")
print('-' * 115)
for f in sorted(glob.glob('scratch/*_dev_results.json')):
    r = get_ap(f)
    if 'error' in r:
        print(r['file'].ljust(45), "ERROR:", r['error'])
    else:
        tag = r['treat'][:30]
        print(r['file'].ljust(45), str(r['N']).rjust(5), ("%+.3f" % r['NetR']).rjust(8), ("%.2f" % r['PF']).rjust(6), ("%.1f%%" % r['WR']).rjust(6), "  ", tag, "cfg="+r['config'])
