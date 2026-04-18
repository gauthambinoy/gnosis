"""Gnosis Compression — bandwidth-optimized responses with delta support."""
from datetime import datetime, timezone
import hashlib
import json
import zlib
import base64


class CompressionEngine:
    """Provides compressed and delta responses for bandwidth optimization."""

    def __init__(self):
        self._hash_cache: dict[str, str] = {}
        self._stats = {"total_requests": 0, "delta_hits": 0, "bytes_saved": 0, "full_responses": 0}

    def compute_hash(self, data: dict | list | str) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def compress_response(self, data: dict | list | str, previous_hash: str | None = None) -> dict:
        self._stats["total_requests"] += 1
        serialized = json.dumps(data, sort_keys=True, default=str)
        current_hash = hashlib.sha256(serialized.encode()).hexdigest()

        if previous_hash and previous_hash == current_hash:
            self._stats["delta_hits"] += 1
            self._stats["bytes_saved"] += len(serialized)
            return {
                "type": "no_change",
                "hash": current_hash,
                "size_bytes": 0,
            }

        compressed = zlib.compress(serialized.encode())
        encoded = base64.b64encode(compressed).decode()
        original_size = len(serialized)
        compressed_size = len(encoded)
        self._stats["bytes_saved"] += max(0, original_size - compressed_size)
        self._stats["full_responses"] += 1

        return {
            "type": "full",
            "hash": current_hash,
            "data": encoded,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "ratio": round(compressed_size / max(original_size, 1), 3),
        }

    def get_stats(self) -> dict:
        return {**self._stats, "timestamp": datetime.now(timezone.utc).isoformat()}


compression_engine = CompressionEngine()
