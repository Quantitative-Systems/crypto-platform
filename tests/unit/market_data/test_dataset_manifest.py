"""
Unit tests for DatasetManifestManager and SHA256 provenance tracking.
"""

import os
import tempfile
import json
import pytest
from market_data.dataset_manifest import (
    DatasetManifest,
    DatasetManifestManager
)


def test_dataset_manifest_generation_and_audit():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        manifest_out = tf.name

    try:
        manifests = DatasetManifestManager.audit_and_save_manifests(output_file=manifest_out)
        
        # Verify that manifests were generated for available cache files
        assert isinstance(manifests, list)
        if manifests:
            m = manifests[0]
            assert m.symbol.endswith("/USDT")
            assert len(m.sha256_checksum) == 64
            assert m.timezone == "UTC"
            assert m.schema_version == "v2.0-CANONICAL"
            assert m.certification_status in ["RAW", "NORMALIZED", "VALIDATED", "CERTIFIED", "RESEARCH_ELIGIBLE", "REJECTED"]

        # Verify output json file
        assert os.path.exists(manifest_out)
        with open(manifest_out, "r") as f:
            data = json.load(f)
        assert "total_datasets" in data
        assert "manifests" in data
    finally:
        if os.path.exists(manifest_out):
            os.remove(manifest_out)
