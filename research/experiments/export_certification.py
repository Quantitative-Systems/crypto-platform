import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def main():
    manifests_path = REPO_ROOT / "scratch" / "dataset_manifests.json"
    output_path = REPO_ROOT / "research" / "results" / "ASSET_UNIVERSE_CERTIFICATION.json"
    
    if not manifests_path.exists():
        print("ERROR: dataset_manifests.json not found.")
        return

    with open(manifests_path, "r") as f:
        data = json.load(f)
        
    manifests = data.get("manifests", [])
    
    # We want to group by asset, showing coverage for each timeframe.
    certification_report = {
        "report_generated_utc": "2026-09-17T14:43:00Z",
        "universe_size": 10,
        "assets": {}
    }
    
    for m in manifests:
        symbol = m.get("symbol")
        if symbol not in certification_report["assets"]:
            certification_report["assets"][symbol] = {
                "asset": symbol,
                "venue": m.get("venue"),
                "timeframes": {}
            }
            
        tf = m.get("timeframe")
        certification_report["assets"][symbol]["timeframes"][tf] = {
            "start_date": m.get("start_date_str"),
            "end_date": m.get("end_date_str"),
            "row_count": m.get("row_count"),
            "missing_intervals": m.get("missing_intervals"),
            "ohlcv_validation_passed": m.get("ohlcv_validation_passed"),
            "certification_status": m.get("certification_status"),
            "research_eligibility": m.get("research_eligibility")
        }
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(certification_report, f, indent=2)
        
    print(f"Exported certification report to {output_path}")

if __name__ == "__main__":
    main()
