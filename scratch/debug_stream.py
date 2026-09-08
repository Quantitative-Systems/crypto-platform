import sys, json
sys.path.insert(0, "/home/mrcn2/crypto-platform")
from research.experiments.run_h_d03_dev_replay import run_single_stream_dev
res = run_single_stream_dev("BTC", "SET_1")
print("LIFECYCLE:")
print(json.dumps(res.get("lifecycle_funnel", {}), indent=2))
print("REJECTIONS:")
print(json.dumps(res.get("rejections", {}), indent=2))
