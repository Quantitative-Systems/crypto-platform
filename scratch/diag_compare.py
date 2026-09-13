"""Compare trade populations between two results files."""
import json
import sys

a = json.load(open(sys.argv[1]))['all_trades']
b = json.load(open(sys.argv[2]))['all_trades']
ia = {t['trade_id'] for t in a}
ib = {t['trade_id'] for t in b}
print(f"{sys.argv[1]}: {len(ia)} trades")
print(f"{sys.argv[2]}: {len(ib)} trades")
print(f"common: {len(ia & ib)}")
print(f"only in A: {len(ia - ib)}")
print(f"only in B: {len(ib - ia)}")
for x in sorted(ia - ib):
    print('  A-only:', x)
for x in sorted(ib - ia):
    print('  B-only:', x)
