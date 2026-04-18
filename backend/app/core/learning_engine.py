"""Gnosis Learning Engine — 3-loop self-learning system."""
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone

from app.core.memory_engine import memory_engine, MemoryEntry
from app.core.embeddings import embedding_service
from app.core.event_bus import event_bus, Events

logger = logging.getLogger(__name__)


class LearningEngine:
    """3-loop learning system:
    Loop 1 — Instant: immediate corrections stored with max priority.
    Loop 2 — Pattern: analyze recent episodic memories, extract procedural rules.
    Loop 3 — Evolution: periodic deep analysis, trust tuning, memory pruning.
    """

    def __init__(self):
        self._correction_log: dict[str, list[dict]] = {}  # agent_id → corrections
        self._pattern_log: dict[str, list[dict]] = {}  # agent_id → extracted patterns
        self._evolution_log: dict[str, list[dict]] = {}  # agent_id → evolution snapshots
        self._metrics: dict[str, dict] = {}  # agent_id → performance counters

    def _get_metrics(self, agent_id: str) -> dict:
        if agent_id not in self._metrics:
            self._metrics[agent_id] = {
                "corrections": 0,
                "patterns_extracted": 0,
                "evolutions": 0,
                "memories_pruned": 0,
                "memories_consolidated": 0,
            }
        return self._metrics[agent_id]

    # ------------------------------------------------------------------
    # Loop 1 — Instant correction learning
    # ------------------------------------------------------------------
    async def instant_learn(
        self, agent_id: str, execution: dict, feedback: dict
    ):
        """Immediate correction → stored in correction tier with max priority.

        `execution` — what the agent did (action, params, result).
        `feedback`  — what was wrong and the correction.
        """
        original_action = execution.get("action", str(execution))
        correction = feedback.get("correction", feedback.get("message", str(feedback)))
        context = {
            "situation": execution.get("trigger", execution.get("context", "")),
            "original_result": execution.get("result", ""),
            "feedback_type": feedback.get("type", "correction"),
        }

        # Store as correction memory (highest priority, never decays)
        mem = await memory_engine.store_correction(
            agent_id=agent_id,
            original_action=original_action,
            correction=correction,
            context=context,
        )

        # Track locally
        if agent_id not in self._correction_log:
            self._correction_log[agent_id] = []
        self._correction_log[agent_id].append({
            "memory_id": mem.id,
            "original": original_action,
            "correction": correction,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        metrics = self._get_metrics(agent_id)
        metrics["corrections"] += 1

        await event_bus.emit(Events.CORRECTION_RECEIVED, {
            "agent_id": agent_id,
            "memory_id": mem.id,
            "original": original_action,
            "correction": correction,
        })

    # ------------------------------------------------------------------
    # Loop 2 — Pattern learning
    # ------------------------------------------------------------------
    async def pattern_learn(self, agent_id: str):
        """Analyze last 50 episodic memories, find repeated patterns,
        extract procedural rules ('when X happens, always do Y')."""
        episodes = await memory_engine.get_agent_memories(
            agent_id, tier="episodic", limit=50
        )

        if len(episodes) < 3:
            return  # not enough data

        # Group similar memories by cosine similarity
        clusters = self._cluster_memories(episodes, threshold=0.8)

        patterns_extracted = 0
        for cluster in clusters:
            if len(cluster) < 2:
                continue  # need at least 2 instances to form a pattern

            # Extract common themes from cluster
            rule = self._extract_rule(cluster)
            if rule:
                # Store as procedural memory
                await memory_engine.store(
                    agent_id=agent_id,
                    tier="procedural",
                    content=rule["content"],
                    metadata={
                        "type": "learned_pattern",
                        "source_episodes": len(cluster),
                        "confidence": rule["confidence"],
                        "learned_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                patterns_extracted += 1

        # Track
        if agent_id not in self._pattern_log:
            self._pattern_log[agent_id] = []
        self._pattern_log[agent_id].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "episodes_analyzed": len(episodes),
            "clusters_found": len(clusters),
            "patterns_extracted": patterns_extracted,
        })

        metrics = self._get_metrics(agent_id)
        metrics["patterns_extracted"] += patterns_extracted

        if patterns_extracted > 0:
            await event_bus.emit(Events.LEARNING_COMPLETED, {
                "agent_id": agent_id,
                "loop": "pattern",
                "patterns_extracted": patterns_extracted,
                "episodes_analyzed": len(episodes),
            })

    def _cluster_memories(
        self, memories: list[MemoryEntry], threshold: float = 0.8
    ) -> list[list[MemoryEntry]]:
        """Group memories by cosine similarity > threshold."""
        if not memories:
            return []

        # Generate embeddings
        texts = [m.content for m in memories]
        embeddings = embedding_service.embed_batch(texts)

        # Simple greedy clustering
        assigned = set()
        clusters: list[list[MemoryEntry]] = []

        for i, mem_i in enumerate(memories):
            if i in assigned:
                continue
            cluster = [mem_i]
            assigned.add(i)

            for j in range(i + 1, len(memories)):
                if j in assigned:
                    continue
                sim = embedding_service.similarity(embeddings[i], embeddings[j])
                if sim >= threshold:
                    cluster.append(memories[j])
                    assigned.add(j)

            clusters.append(cluster)

        return clusters

    def _extract_rule(self, cluster: list[MemoryEntry]) -> dict | None:
        """Extract a procedural rule from a cluster of similar episodes."""
        if len(cluster) < 2:
            return None

        # Find common words across all cluster entries
        word_sets = []
        for mem in cluster:
            words = set(mem.content.lower().split())
            word_sets.append(words)

        if not word_sets:
            return None

        # Intersection of all word sets = common theme
        common_words = word_sets[0]
        for ws in word_sets[1:]:
            common_words = common_words & ws

        # Filter stop words
        stop_words = {"the", "a", "an", "is", "was", "were", "be", "been", "being",
                       "in", "of", "to", "for", "on", "at", "by", "with", "from",
                       "and", "or", "not", "no", "so", "do", "did", "has", "had",
                       "have", "this", "that", "it", "its", "as"}
        meaningful = [w for w in common_words if w not in stop_words and len(w) > 2]

        if not meaningful:
            return None

        # Extract common actions from metadata
        actions = []
        for mem in cluster:
            if "action" in mem.metadata:
                actions.append(mem.metadata["action"])
            elif "status" in mem.metadata:
                actions.append(mem.metadata["status"])

        action_counts = Counter(actions)
        most_common_action = action_counts.most_common(1)[0][0] if action_counts else "process"

        # Build rule
        theme = " ".join(sorted(meaningful)[:8])
        rule_content = (
            f"PATTERN: When context involves [{theme}], "
            f"the typical action is [{most_common_action}]. "
            f"Based on {len(cluster)} similar past experiences."
        )

        confidence = min(0.6 + len(cluster) * 0.1, 0.95)

        return {
            "content": rule_content,
            "confidence": confidence,
            "theme_words": meaningful,
            "common_action": most_common_action,
        }

    # ------------------------------------------------------------------
    # Loop 3 — Evolution learning
    # ------------------------------------------------------------------
    async def evolution_learn(self, agent_id: str):
        """Deep analysis of all metrics. Adjust trust, prune weak memories,
        strengthen successful patterns."""
        all_memories = await memory_engine.get_agent_memories(agent_id, limit=200)

        if not all_memories:
            return

        # Analyze memory distribution
        tier_counts: dict[str, int] = defaultdict(int)
        for mem in all_memories:
            tier_counts[mem.tier] += 1

        # Prune weak episodic memories (low relevance, never accessed)
        pruned = 0
        episodic = [m for m in all_memories if m.tier == "episodic"]
        if len(episodic) > 100:
            # Keep only the 100 most relevant
            sorted_ep = sorted(episodic, key=lambda m: m.relevance_score, reverse=True)
            to_prune = sorted_ep[100:]
            for mem in to_prune:
                try:
                    from app.core.vector_store import agent_vectors
                    store = agent_vectors.get_store(agent_id, "episodic")
                    store.remove(mem.id)
                    pruned += 1
                except Exception:
                    logger.warning("Learning pattern extraction failed", exc_info=True)

        # Strengthen procedural memories that have been validated
        procedural = [m for m in all_memories if m.tier == "procedural"]
        for proc in procedural:
            if proc.access_count > 5:
                proc.strength = min(proc.strength * 1.1, 2.0)

        # Calculate health score
        correction_count = tier_counts.get("correction", 0)
        total = len(all_memories) or 1
        correction_ratio = correction_count / total
        health_score = max(0.0, 1.0 - correction_ratio * 5)  # many corrections = low health

        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_memories": len(all_memories),
            "tier_distribution": dict(tier_counts),
            "pruned": pruned,
            "health_score": health_score,
            "correction_ratio": correction_ratio,
        }

        if agent_id not in self._evolution_log:
            self._evolution_log[agent_id] = []
        self._evolution_log[agent_id].append(snapshot)

        metrics = self._get_metrics(agent_id)
        metrics["evolutions"] += 1
        metrics["memories_pruned"] += pruned

        await event_bus.emit(Events.LEARNING_COMPLETED, {
            "agent_id": agent_id,
            "loop": "evolution",
            "health_score": health_score,
            "pruned": pruned,
            "total_memories": len(all_memories),
        })

    # ------------------------------------------------------------------
    # Memory consolidation
    # ------------------------------------------------------------------
    async def consolidate_memories(self, agent_id: str):
        """Move short-term → long-term, extract semantic from episodic clusters."""
        episodic = await memory_engine.get_agent_memories(
            agent_id, tier="episodic", limit=100
        )

        if len(episodic) < 5:
            return

        # Cluster episodic memories
        clusters = self._cluster_memories(episodic, threshold=0.75)
        consolidated = 0

        for cluster in clusters:
            if len(cluster) < 3:
                continue

            # Extract semantic summary from cluster
            summary = self._summarize_cluster(cluster)

            if summary:
                await memory_engine.store(
                    agent_id=agent_id,
                    tier="semantic",
                    content=summary,
                    metadata={
                        "type": "consolidated",
                        "source_count": len(cluster),
                        "consolidated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                consolidated += 1

        metrics = self._get_metrics(agent_id)
        metrics["memories_consolidated"] += consolidated

    def _summarize_cluster(self, cluster: list[MemoryEntry]) -> str | None:
        """Create a semantic summary from a cluster of episodic memories."""
        if not cluster:
            return None

        # Extract key information from cluster
        all_words: list[str] = []
        for mem in cluster:
            words = mem.content.lower().split()
            all_words.extend(words)

        word_freq = Counter(all_words)
        # Remove stop words and very short words
        stop = {"the", "a", "an", "is", "was", "in", "of", "to", "for", "on",
                "at", "by", "with", "and", "or", "not", "this", "that", "it"}
        key_words = [
            w for w, c in word_freq.most_common(20)
            if w not in stop and len(w) > 2
        ][:10]

        if not key_words:
            return None

        return (
            f"KNOWLEDGE: Based on {len(cluster)} experiences, "
            f"key concepts are [{', '.join(key_words)}]. "
            f"This pattern has been observed repeatedly."
        )

    # ------------------------------------------------------------------
    # Stats & history
    # ------------------------------------------------------------------
    def get_agent_learning_history(self, agent_id: str) -> dict:
        return {
            "corrections": self._correction_log.get(agent_id, [])[-20:],
            "patterns": self._pattern_log.get(agent_id, [])[-10:],
            "evolutions": self._evolution_log.get(agent_id, [])[-5:],
            "metrics": self._get_metrics(agent_id),
        }

    @property
    def stats(self) -> dict:
        return {
            "agents_learning": list(self._metrics.keys()),
            "total_corrections": sum(m.get("corrections", 0) for m in self._metrics.values()),
            "total_patterns": sum(m.get("patterns_extracted", 0) for m in self._metrics.values()),
            "total_evolutions": sum(m.get("evolutions", 0) for m in self._metrics.values()),
        }


# Global singleton
learning_engine = LearningEngine()
