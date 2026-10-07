"""
QCP Phase 12 — Binary Schema Serialization.
Implements compact, fixed-size binary encoding/decoding for L2 order book updates and trades.

Avoids JSON serialization overhead in performance-critical market data paths:
- Struct packing with little-endian byte ordering.
- Zero-copy parsing capability.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Tuple


# Format:
# Timestamp (uint64) = 8 bytes
# Price (double) = 8 bytes
# Quantity (double) = 8 bytes
# Sequence (uint64) = 8 bytes
# Side (uint8: 0=BUY, 1=SELL) = 1 byte
# Flags (uint8: 0=NONE, 1=SNAPSHOT, 2=CROSS) = 1 byte
# Total = 34 bytes per tick
TICK_STRUCT_FORMAT = "<QddQBB"
TICK_STRUCT_SIZE = struct.calcsize(TICK_STRUCT_FORMAT)


@dataclass
class BinaryTick:
    timestamp_ns: int
    price: float
    quantity: float
    sequence_id: int
    is_buy: bool
    is_snapshot: bool = False

    def serialize(self) -> bytes:
        return struct.pack(
            TICK_STRUCT_FORMAT,
            self.timestamp_ns,
            self.price,
            self.quantity,
            self.sequence_id,
            0 if self.is_buy else 1,
            1 if self.is_snapshot else 0,
        )

    @classmethod
    def deserialize(cls, data: bytes) -> BinaryTick:
        if len(data) < TICK_STRUCT_SIZE:
            raise ValueError(f"Binary data too short: {len(data)} < {TICK_STRUCT_SIZE} bytes")
        ts, price, qty, seq, side_byte, flag_byte = struct.unpack(TICK_STRUCT_FORMAT, data[:TICK_STRUCT_SIZE])
        return cls(
            timestamp_ns=ts,
            price=price,
            quantity=qty,
            sequence_id=seq,
            is_buy=(side_byte == 0),
            is_snapshot=(flag_byte == 1),
        )


class BinarySchemaCodec:
    """Fast serializer and batch codec for market data packets."""

    @staticmethod
    def encode_batch(ticks: list[BinaryTick]) -> bytes:
        return b"".join(t.serialize() for t in ticks)

    @staticmethod
    def decode_batch(buffer: bytes) -> list[BinaryTick]:
        ticks = []
        offset = 0
        buf_len = len(buffer)
        while offset + TICK_STRUCT_SIZE <= buf_len:
            chunk = buffer[offset:offset + TICK_STRUCT_SIZE]
            ticks.append(BinaryTick.deserialize(chunk))
            offset += TICK_STRUCT_SIZE
        return ticks
