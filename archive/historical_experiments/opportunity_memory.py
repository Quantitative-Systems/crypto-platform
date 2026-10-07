"""
QCP Opportunity Memory.
Maintains persistent memory of tested hypotheses, their validation status,
and forensic failure taxonomy. Prevents redundant testing under unchanged conditions
while enabling causal reopening when market regimes shift or feature spaces expand.
"""

from __future__ import annotations

import enum
import os
import sqlite3
from typing import Dict, Any, Optional, List, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "research_vault.db")


class FailureCategory(str, enum.Enum):
    LOOKAHEAD_VIOLATION = "LOOKAHEAD_VIOLATION"
    FRICTION_OVERWHELMED = "FRICTION_OVERWHELMED"
    LATENCY_DECAY = "LATENCY_DECAY"
    WINDFALL_DEPENDENCY = "WINDFALL_DEPENDENCY"
    SUB_HURDLE_EDGE = "SUB_HURDLE_EDGE"
    REGIME_MISMATCH = "REGIME_MISMATCH"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    SURVIVED = "SURVIVED"
    UNKNOWN = "UNKNOWN"


class OpportunityMemory:
    """
    Cryptographic and relational memory for hypotheses evaluated by the Falsification Engine.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Hypothesis Memory Table with failure taxonomy and regime context
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hypothesis_memory (
                    alpha_id TEXT PRIMARY KEY,
                    opportunity_type TEXT,
                    symbol TEXT,
                    timeframe TEXT,
                    falsified BOOLEAN,
                    failure_reason TEXT,
                    failure_category TEXT DEFAULT 'UNKNOWN',
                    regime_context TEXT DEFAULT '',
                    net_edge_r REAL,
                    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Ensure columns exist for backwards compatibility
            cursor.execute("PRAGMA table_info(hypothesis_memory)")
            cols = [row[1] for row in cursor.fetchall()]
            if "failure_category" not in cols:
                cursor.execute("ALTER TABLE hypothesis_memory ADD COLUMN failure_category TEXT DEFAULT 'UNKNOWN'")
            if "regime_context" not in cols:
                cursor.execute("ALTER TABLE hypothesis_memory ADD COLUMN regime_context TEXT DEFAULT ''")

            conn.commit()

    @staticmethod
    def classify_failure(falsified: bool, failure_reason: str) -> FailureCategory:
        """Categorizes forensic audit failure reason into canonical failure taxonomy."""
        if not falsified:
            return FailureCategory.SURVIVED
        
        reason_upper = failure_reason.upper()
        if "LOOKAHEAD" in reason_upper or "CAUSAL" in reason_upper:
            return FailureCategory.LOOKAHEAD_VIOLATION
        elif "FRICTION" in reason_upper or "SLIPPAGE" in reason_upper or "FEE" in reason_upper:
            return FailureCategory.FRICTION_OVERWHELMED
        elif "LATENCY" in reason_upper or "EXECUTION" in reason_upper:
            return FailureCategory.LATENCY_DECAY
        elif "WINDFALL" in reason_upper or "OUTLIER" in reason_upper:
            return FailureCategory.WINDFALL_DEPENDENCY
        elif "DATA" in reason_upper or "UNAVAILABLE" in reason_upper:
            return FailureCategory.DATA_UNAVAILABLE
        elif "SUB_HURDLE" in reason_upper or "HURDLE" in reason_upper or "EDGE" in reason_upper:
            return FailureCategory.SUB_HURDLE_EDGE
        elif "REGIME" in reason_upper:
            return FailureCategory.REGIME_MISMATCH
        return FailureCategory.UNKNOWN

    def record_hypothesis_evaluation(
        self,
        alpha_id: str,
        opportunity_type: str,
        symbol: str,
        timeframe: str,
        falsified: bool,
        failure_reason: str,
        net_edge_r: float,
        failure_category: Optional[str] = None,
        regime_context: Optional[str] = None
    ) -> None:
        """
        Records the outcome of the adversarial falsification audit for a hypothesis.
        """
        if failure_category is None:
            cat_enum = self.classify_failure(falsified, failure_reason)
            failure_category = cat_enum.value

        reg_ctx = regime_context or ""

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO hypothesis_memory (
                    alpha_id, opportunity_type, symbol, timeframe, falsified, failure_reason, failure_category, regime_context, net_edge_r
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alpha_id, opportunity_type, symbol, timeframe, 
                bool(falsified), failure_reason, failure_category, reg_ctx, net_edge_r
            ))
            conn.commit()

    def is_recently_falsified(self, opportunity_type: str, symbol: str) -> bool:
        """
        Checks if a similar opportunity was recently falsified.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT falsified FROM hypothesis_memory 
                WHERE opportunity_type = ? AND symbol = ? 
                ORDER BY evaluated_at DESC LIMIT 1
            """, (opportunity_type, symbol))
            
            row = cursor.fetchone()
            if row:
                return bool(row[0])
            return False

    def can_reopen_hypothesis(
        self,
        opportunity_type: str,
        symbol: str,
        current_regime: Optional[str] = None,
        new_features: Optional[List[str]] = None,
        has_new_features: bool = False
    ) -> Tuple[bool, str]:
        """
        Determines whether a hypothesis should be tested:
        - If never tested -> True ("NEW_HYPOTHESIS")
        - If previously passed -> True ("QUALIFIED_CANDIDATE")
        - If falsified due to LOOKAHEAD -> False ("PERMANENT_CODE_DEFECT_SUPPRESSED")
        - If new feature set provided -> True ("EXPANDED_FEATURE_SET_REOPEN")
        - If falsified under a different regime and current regime changed -> True ("REGIME_TRANSITION_REOPEN")
        - Otherwise -> False ("SUPPRESSED_IDENTICAL_CONDITIONS")
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT falsified, failure_category, regime_context 
                FROM hypothesis_memory 
                WHERE opportunity_type = ? AND symbol = ? 
                ORDER BY evaluated_at DESC LIMIT 1
            """, (opportunity_type, symbol))
            
            row = cursor.fetchone()
            if not row:
                return True, "NEW_HYPOTHESIS"
            
            falsified, cat, prev_regime = bool(row[0]), row[1], row[2]
            if not falsified:
                return True, "PREVIOUSLY_SURVIVED"
            
            if cat == FailureCategory.LOOKAHEAD_VIOLATION.value:
                return False, "PERMANENT_CODE_DEFECT_SUPPRESSED: lookahead defect cannot be cured by regime change"
            
            if (new_features and len(new_features) > 0) or has_new_features:
                return True, "Expanded feature space: EXPANDED_FEATURE_SET_REOPEN"
            
            if current_regime and prev_regime and current_regime != prev_regime:
                return True, f"Regime shifted: REGIME_TRANSITION_REOPEN({prev_regime}->{current_regime})"
            
            return False, "Active memory suppression: SUPPRESSED_IDENTICAL_CONDITIONS"

    def get_memory_stats(self) -> Dict[str, Any]:
        """Returns comprehensive statistics on the research vault's memory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM hypothesis_memory")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM hypothesis_memory WHERE falsified = 1")
            falsified = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT failure_category, COUNT(*) 
                FROM hypothesis_memory 
                WHERE falsified = 1 
                GROUP BY failure_category
            """)
            category_counts = dict(cursor.fetchall())

            return {
                "total_hypotheses_evaluated": total,
                "falsified_hypotheses": falsified,
                "survived_hypotheses": total - falsified,
                "failure_taxonomy_distribution": category_counts
            }

    def get_falsification_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns chronological history of tested hypotheses."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT alpha_id, opportunity_type, symbol, timeframe, falsified, failure_reason, failure_category, regime_context, net_edge_r, evaluated_at
                FROM hypothesis_memory
                ORDER BY evaluated_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [
                {
                    "alpha_id": r[0],
                    "opportunity_type": r[1],
                    "symbol": r[2],
                    "timeframe": r[3],
                    "falsified": bool(r[4]),
                    "failure_reason": r[5],
                    "failure_category": r[6],
                    "regime_context": r[7],
                    "net_edge_r": r[8],
                    "evaluated_at": r[9]
                }
                for r in rows
            ]
