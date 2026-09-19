import os
import hashlib
from collections import defaultdict
import json

ROOT = "/home/mrcn2/crypto-platform"
DIRS_TO_SCAN = [
    "config",
    "market_data",
    "market_intelligence",
    "strategy_engine",
    "risk_engine",
    "trade_management",
    "execution_gateway",
    "portfolio_engine",
    "platform_core",
    "production",
    "research",
    "tests",
    "docs",
    "scratch"
]

def hash_file(filepath):
    h = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def classify_file(rel_path):
    parts = rel_path.split(os.sep)
    top = parts[0]
    filename = parts[-1]
    
    # Root level core modules
    if top in ["config", "market_data", "market_intelligence", "strategy_engine", 
               "risk_engine", "trade_management", "execution_gateway", 
               "portfolio_engine", "platform_core", "production"]:
        return "CANONICAL"
        
    if top == "tests":
        return "TEST"
        
    if top == "docs":
        if filename.startswith("HYP_") or filename.startswith("ALPHA_") or filename.startswith("CANONICAL_"):
            return "PERMANENT_ANALYTICS"
        return "CANONICAL"
        
    if top == "research":
        if "analytics" in parts:
            return "PERMANENT_ANALYTICS"
        elif "experiments" in parts:
            if "baseline" in filename or "canonical" in filename:
                return "ACTIVE_EXPERIMENT"
            return "ACTIVE_EXPERIMENT"
        elif "replayer" in parts or "simulation" in parts or "metrics" in parts:
            return "CANONICAL"
        return "ACTIVE_EXPERIMENT"
        
    if top == "scratch":
        if filename.startswith("fix_tests"):
            return "DEPRECATED"
        if filename.endswith(".patch") or filename.endswith(".rej"):
            return "DEPRECATED"
        if "fast_audit" in filename:
            return "DEPRECATED"
        if filename.endswith(".json") and ("certified" in filename or "baseline" in filename or "composite" in filename):
            return "PERMANENT_ANALYTICS"
        return "SCRATCH"
        
    return "UNKNOWN"

def run_inventory():
    file_records = []
    hash_map = defaultdict(list)
    
    for d in DIRS_TO_SCAN:
        dp = os.path.join(ROOT, d)
        if not os.path.exists(dp):
            continue
        for root, dirs, files in os.walk(dp):
            # Skip caches
            if "__pycache__" in root or ".pytest_cache" in root or ".git" in root:
                continue
            for f in sorted(files):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, ROOT)
                size = os.path.getsize(full_path)
                f_hash = hash_file(full_path)
                cls = classify_file(rel_path)
                
                record = {
                    "rel_path": rel_path,
                    "filename": f,
                    "directory": os.path.dirname(rel_path),
                    "size_bytes": size,
                    "classification": cls,
                    "sha256": f_hash
                }
                file_records.append(record)
                if f_hash:
                    hash_map[f_hash].append(rel_path)
                    
    # Detect exact duplicates
    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    
    # Classify counts
    counts = defaultdict(int)
    for r in file_records:
        if r["sha256"] in duplicates and r["classification"] == "SCRATCH":
            r["classification"] = "DUPLICATE"
        counts[r["classification"]] += 1
        
    print("=" * 80)
    print("REPOSITORY FILE INVENTORY SUMMARY")
    print("=" * 80)
    print(f"Total Files Scanned: {len(file_records)}")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {k:22s}: {v:4d} files ({v/len(file_records)*100:.1f}%)")
        
    print(f"\nExact Hash Duplicates Found: {len(duplicates)} sets")
    for h, paths in list(duplicates.items())[:10]:
        print(f"  Hash {h[:12]}... -> {paths}")
        
    with open(os.path.join(ROOT, "scratch/inventory_summary.json"), "w") as f:
        json.dump({
            "total_files": len(file_records),
            "classification_counts": counts,
            "exact_duplicate_sets": len(duplicates),
            "duplicates": duplicates,
            "files": file_records
        }, f, indent=2)
        
    print(f"\nSaved inventory report to scratch/inventory_summary.json")

if __name__ == "__main__":
    run_inventory()
