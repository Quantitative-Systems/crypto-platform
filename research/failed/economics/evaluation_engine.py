        self.manifest_path = (
            Path(manifest_path) if manifest_path
            else repo_root / "proofs" / "work" / "dataset_manifests.json"
        )