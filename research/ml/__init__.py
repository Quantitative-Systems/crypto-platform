"""Machine Learning Research Domain.

Supervised and unsupervised quantitative machine learning research layer:
- Chronological, leakage-safe train/validation/test feature pipelines
- Discrete candidate signal ranking (Trade Quality Classification)
- Unsupervised regime classification (PCA, Mahalanobis distance)

Governed by the rule: ML never predicts raw price directly, and never replaces
the frozen Market Model. It acts as a conditional filter and ranking layer only.
"""
from __future__ import annotations

DOMAIN_NAME = "MACHINE_LEARNING"
