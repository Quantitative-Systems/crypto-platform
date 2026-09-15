"""
Quantitative Crypto Platform (QCP) — Data Lineage & Certification Audit Runner.

Audits and certifies historical datasets for Relative-Value research across:
- BTC/USDT, ETH/USDT, SOL/USDT
- Timeframes: 1D, 4H
Computes data quality scores, gap analysis, SHA-256 cryptographic lineage hashes,
and establishes the certified common historical research window.

Outputs:
- research/results/DATA_LINEAGE_AUDIT.json
- research/discovery_lab/data_manifest.json
"""

import os
import json
import datetime
import logging
from typing import Dict, List, Any

from market_intelligence.primitives import Candle
from market_data.binance_fetcher import BinanceFetcher
from market_data.data_quality_engine import DataQualityEngine, DataQualityReport

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DataLineageAudit")


def run_data_certification():
    logger.info("Starting Data Lineage & Certification Audit...")
    
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    timeframes = ["1d", "4h"]
    
    audit_results: Dict[str, Any] = {
        "platform": "Quantitative Crypto Platform (QCP)",
        "audit_name": "DATA_LINEAGE_AND_CERTIFICATION_AUDIT",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "datasets": {},
        "common_window": {},
        "overall_verdict": "CERTIFIED_CLEAN",
    }
    
    manifest_datasets: List[Dict[str, Any]] = []
    
    min_end_ts = 9999999999
    max_start_ts = 0
    all_clean = True
    
    for sym in symbols:
        clean_sym = sym.replace("/", "")
        for tf in timeframes:
            key = f"{clean_sym}_{tf}"
            logger.info(f"Auditing dataset: {sym} ({tf})...")
            
            candles = BinanceFetcher.fetch_real_candles(symbol=sym, timeframe=tf, limit=50000)
            if not candles:
                logger.error(f"No candles found for {sym} {tf}")
                all_clean = False
                continue
                
            report: DataQualityReport = DataQualityEngine.audit_candles(
                symbol=sym,
                timeframe=tf,
                candles=candles,
            )
            
            report_dict = report.to_dict()
            report_dict["start_iso"] = datetime.datetime.fromtimestamp(report.start_timestamp, datetime.timezone.utc).isoformat()
            report_dict["end_iso"] = datetime.datetime.fromtimestamp(report.end_timestamp, datetime.timezone.utc).isoformat()
            
            audit_results["datasets"][key] = report_dict
            
            manifest_datasets.append({
                "dataset_id": key,
                "symbol": sym,
                "timeframe": tf,
                "start_timestamp": report.start_timestamp,
                "end_timestamp": report.end_timestamp,
                "start_iso": report_dict["start_iso"],
                "end_iso": report_dict["end_iso"],
                "total_bars": report.total_bars,
                "completeness_pct": report.completeness_pct,
                "quality_score": report.quality_score,
                "verdict": report.verdict.value,
                "sha256_hash": report.sha256_dataset_hash,
            })
            
            if report.start_timestamp > max_start_ts:
                max_start_ts = report.start_timestamp
            if report.end_timestamp < min_end_ts:
                min_end_ts = report.end_timestamp
                
            if report.verdict.value == "REJECTED_CORRUPT":
                all_clean = False
                
    common_start_iso = datetime.datetime.fromtimestamp(max_start_ts, datetime.timezone.utc).isoformat()
    common_end_iso = datetime.datetime.fromtimestamp(min_end_ts, datetime.timezone.utc).isoformat()
    
    audit_results["common_window"] = {
        "start_timestamp": max_start_ts,
        "end_timestamp": min_end_ts,
        "start_iso": common_start_iso,
        "end_iso": common_end_iso,
        "duration_days": round((min_end_ts - max_start_ts) / 86400.0, 1),
        "certified_window_note": "Common intersection across BTC, ETH, and SOL on 1D/4H. Bound by SOL listing on 2020-08-11.",
    }
    
    audit_results["overall_verdict"] = "CERTIFIED_CLEAN" if all_clean else "USABLE_WITH_WARNINGS"
    
    # Write DATA_LINEAGE_AUDIT.json
    out_audit_path = os.path.abspath("research/results/DATA_LINEAGE_AUDIT.json")
    os.makedirs(os.path.dirname(out_audit_path), exist_ok=True)
    with open(out_audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)
    logger.info(f"Data Lineage Audit saved to {out_audit_path}")
    
    # Write data_manifest.json
    manifest_data = {
        "manifest_version": "1.0",
        "description": "Certified Historical Datasets for Relative-Value Research",
        "common_research_window": audit_results["common_window"],
        "datasets": manifest_datasets,
    }
    out_manifest_path = os.path.abspath("research/discovery_lab/data_manifest.json")
    os.makedirs(os.path.dirname(out_manifest_path), exist_ok=True)
    with open(out_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    logger.info(f"Research Data Manifest saved to {out_manifest_path}")
    
    return audit_results


if __name__ == "__main__":
    run_data_certification()
