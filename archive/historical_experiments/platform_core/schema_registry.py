"""
Quantitative Crypto Platform (QCP) — Canonical Schema Registry.

Maintains versioned data contracts, schemas, event types, and validation rules
ensuring complete cross-service message compatibility.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type


@dataclass
class SchemaDefinition:
    schema_id: str
    version: str
    name: str
    description: str
    fields: Dict[str, str]
    immutable: bool = True
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "fields": self.fields,
            "immutable": self.immutable,
            "created_at_utc": self.created_at_utc,
        }


class SchemaRegistry:
    """
    Central repository for all versioned platform schemas.
    """

    _schemas: Dict[str, Dict[str, SchemaDefinition]] = {}

    @classmethod
    def register(cls, definition: SchemaDefinition) -> None:
        if definition.schema_id not in cls._schemas:
            cls._schemas[definition.schema_id] = {}
        cls._schemas[definition.schema_id][definition.version] = definition

    @classmethod
    def get(cls, schema_id: str, version: Optional[str] = None) -> Optional[SchemaDefinition]:
        versions = cls._schemas.get(schema_id)
        if not versions:
            return None
        if version:
            return versions.get(version)
        # return highest/latest
        latest_ver = sorted(versions.keys())[-1]
        return versions[latest_ver]

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        result = []
        for sid, v_dict in cls._schemas.items():
            for ver, definition in v_dict.items():
                result.append(definition.to_dict())
        return result


# Pre-register platform schemas
_CORE_SCHEMAS = [
    SchemaDefinition(
        schema_id="market_data.ohlcv",
        version="1.0.0",
        name="OHLCV Candle Record",
        description="Exchange-neutral 1-bar OHLCV candle",
        fields={"timestamp": "int", "open": "float", "high": "float", "low": "float", "close": "float", "volume": "float"},
    ),
    SchemaDefinition(
        schema_id="market_data.trade",
        version="1.0.0",
        name="Public Trade Tick Record",
        description="Normalized market trade print",
        fields={"timestamp": "int", "price": "float", "quantity": "float", "side": "str", "trade_id": "str"},
    ),
    SchemaDefinition(
        schema_id="market_data.order_book_l2",
        version="1.0.0",
        name="Level-2 Order Book Snapshot/Delta",
        description="Top of book and depth snapshot",
        fields={"timestamp": "int", "bids": "list", "asks": "list", "sequence_id": "int"},
    ),
    SchemaDefinition(
        schema_id="execution.order_intent",
        version="1.0.0",
        name="Order Intent Specification",
        description="Pre-risk execution order intent",
        fields={"intent_id": "str", "symbol": "str", "direction": "str", "target_units": "float", "urgency": "str"},
    ),
    SchemaDefinition(
        schema_id="execution.trade_telemetry",
        version="1.0.0",
        name="Execution Telemetry Record",
        description="Complete post-trade realization metrics",
        fields={"trade_id": "str", "strategy_id": "str", "symbol": "str", "entry_price": "float", "exit_price": "float", "net_r": "float"},
    ),
    SchemaDefinition(
        schema_id="risk.audit_record",
        version="1.0.0",
        name="Risk Firewall Audit Record",
        description="7-D Risk evaluation outcome and veto flags",
        fields={"audit_id": "str", "timestamp": "int", "passed": "bool", "portfolio_heat_pct": "float", "veto_reasons": "list"},
    ),
]

for _s in _CORE_SCHEMAS:
    SchemaRegistry.register(_s)
