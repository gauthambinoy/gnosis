"""Memory decay task — periodically reduces memory strength using exponential decay.

Correction-tier memories NEVER decay (they are permanent).
Other tiers decay based on age and access frequency.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.tasks.memory_decay")

DECAY_RATES = {
    "sensory": 0.95,    # Fastest decay
    "episodic": 0.98,   # Moderate decay
    "semantic": 0.995,  # Slow decay
    "procedural": 0.99, # Slow decay
    "correction": 1.0,  # Never decays
}

STRENGTH_FLOOR = 0.01  # Below this, memory is eligible for garbage collection


def decay_agent_memories(memory_engine, agent_id: str) -> dict:
    """Apply exponential decay to all memories for an agent.
    
    Returns stats about decayed/pruned memories.
    """
    stats = {"decayed": 0, "pruned": 0, "preserved": 0}
    
    for tier, rate in DECAY_RATES.items():
        if rate >= 1.0:
            # Corrections never decay
            memories = memory_engine._get_agent_memories(agent_id, tier)
            stats["preserved"] += len(memories)
            continue
        
        memories = memory_engine._get_agent_memories(agent_id, tier)
        to_remove = []
        
        for mem in memories:
            # Apply decay: strength *= rate^(1 + access_penalty)
            access_boost = min(mem.access_count * 0.01, 0.05)  # Accessed memories decay slower
            effective_rate = min(rate + access_boost, 0.999)
            mem.strength *= effective_rate
            
            if mem.strength < STRENGTH_FLOOR:
                to_remove.append(mem.id)
                stats["pruned"] += 1
            else:
                stats["decayed"] += 1
        
        # Remove pruned memories
        if to_remove:
            memory_engine._memories[agent_id][tier] = [
                m for m in memories if m.id not in set(to_remove)
            ]
    
    return stats


def run_decay_cycle(memory_engine) -> dict:
    """Run decay cycle across ALL agents."""
    total_stats = {"agents_processed": 0, "decayed": 0, "pruned": 0, "preserved": 0}
    
    for agent_id in list(memory_engine._memories.keys()):
        agent_stats = decay_agent_memories(memory_engine, agent_id)
        total_stats["agents_processed"] += 1
        for key in ("decayed", "pruned", "preserved"):
            total_stats[key] += agent_stats[key]
    
    logger.info(f"Memory decay cycle complete: {total_stats}")
    return total_stats
