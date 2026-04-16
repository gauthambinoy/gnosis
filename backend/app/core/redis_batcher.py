"""Gnosis Redis Batcher — Batch multiple Redis ops into single round-trips."""
import asyncio
import logging
import time
from typing import List, Any, Optional, Dict
from dataclasses import dataclass, field

logger = logging.getLogger("gnosis.redis_batcher")

@dataclass
class BatchMetrics:
    total_batches: int = 0
    total_ops: int = 0
    total_saved_roundtrips: int = 0
    avg_batch_size: float = 0
    avg_batch_ms: float = 0

class RedisBatcher:
    """Batches Redis operations into pipelines for reduced round-trips."""
    
    def __init__(self):
        self._metrics = BatchMetrics()
        self._pending: Dict[str, List] = {}  # namespace -> [(command, args, kwargs)]

    async def execute_batch(self, operations: List[tuple], redis_client=None) -> List[Any]:
        """Execute a batch of Redis operations in a single pipeline.
        
        operations: List of (method_name, *args) tuples, e.g.:
            [("get", "key1"), ("set", "key2", "value"), ("hgetall", "hash1")]
        """
        if not operations:
            return []
        
        if redis_client is None:
            try:
                from app.core.redis_client import redis_manager
                redis_client = redis_manager._client
            except Exception:
                logger.error("No Redis client available")
                return [None] * len(operations)
        
        start = time.time()
        
        try:
            pipe = redis_client.pipeline(transaction=False)
            for op in operations:
                method = op[0]
                args = op[1:] if len(op) > 1 else ()
                getattr(pipe, method)(*args)
            
            results = await pipe.execute()
            
            elapsed_ms = (time.time() - start) * 1000
            self._metrics.total_batches += 1
            self._metrics.total_ops += len(operations)
            self._metrics.total_saved_roundtrips += len(operations) - 1
            self._metrics.avg_batch_size = self._metrics.total_ops / self._metrics.total_batches
            self._metrics.avg_batch_ms = (self._metrics.avg_batch_ms * 0.9) + (elapsed_ms * 0.1)
            
            return results
            
        except Exception as e:
            logger.error(f"Redis batch failed: {e}")
            return [None] * len(operations)

    async def multi_get(self, keys: List[str], redis_client=None) -> Dict[str, Any]:
        """Get multiple keys in a single pipeline."""
        ops = [("get", key) for key in keys]
        results = await self.execute_batch(ops, redis_client)
        return dict(zip(keys, results))

    async def multi_set(self, mapping: Dict[str, Any], ttl: int = None, redis_client=None) -> bool:
        """Set multiple key-value pairs in a single pipeline."""
        ops = []
        for key, value in mapping.items():
            if ttl:
                ops.append(("setex", key, ttl, value))
            else:
                ops.append(("set", key, value))
        await self.execute_batch(ops, redis_client)
        return True

    async def multi_delete(self, keys: List[str], redis_client=None) -> int:
        """Delete multiple keys in a single pipeline."""
        ops = [("delete", key) for key in keys]
        results = await self.execute_batch(ops, redis_client)
        return sum(1 for r in results if r)

    @property
    def metrics(self) -> dict:
        return {
            "total_batches": self._metrics.total_batches,
            "total_ops": self._metrics.total_ops,
            "saved_roundtrips": self._metrics.total_saved_roundtrips,
            "avg_batch_size": round(self._metrics.avg_batch_size, 1),
            "avg_batch_ms": round(self._metrics.avg_batch_ms, 2),
        }

redis_batcher = RedisBatcher()
