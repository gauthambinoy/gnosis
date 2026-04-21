"""Memory decay task — periodically reduces memory strength using exponential decay.

Correction-tier memories NEVER decay (they are permanent). The actual decay
math now lives on ``MemoryEngine`` so it can operate directly against the
persistent store; this module simply exposes backwards-compatible entry points
the rest of the codebase already imports.
"""

import asyncio
import logging

logger = logging.getLogger("gnosis.tasks.memory_decay")

# Kept as module-level constants for code that introspects them.
DECAY_RATES = {
    "sensory": 0.95,
    "episodic": 0.98,
    "semantic": 0.995,
    "procedural": 0.99,
    "correction": 1.0,
}
STRENGTH_FLOOR = 0.01


def _await(coro):
    """Run *coro* from a sync caller, including from inside a running loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


def decay_agent_memories(memory_engine, agent_id: str) -> dict:
    """Apply exponential decay to all memories for an agent.

    Returns stats about decayed/pruned/preserved memories. Safe to call from
    either sync or async contexts (uses a worker thread if a loop is already
    running).
    """
    return _await(memory_engine.decay_agent(agent_id))


def run_decay_cycle(memory_engine) -> dict:
    """Run decay cycle across ALL known agents."""
    stats = _await(memory_engine.decay_all())
    logger.info(f"Memory decay cycle complete: {stats}")
    return stats
