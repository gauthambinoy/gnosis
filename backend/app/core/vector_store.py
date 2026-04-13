"""Vector store — FAISS-backed similarity search for agent memories."""
import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class SearchResult:
    id: str
    score: float
    metadata: dict


class VectorStore:
    """Per-agent vector store. Uses numpy for similarity search (upgrades to FAISS for scale)."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._vectors: dict[str, np.ndarray] = {}  # id -> embedding
        self._metadata: dict[str, dict] = {}  # id -> metadata
        self._faiss_index = None
        self._try_faiss()

    def _try_faiss(self):
        """Try to use FAISS if available."""
        try:
            import faiss
            self._faiss_index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine on normalized)
            self._faiss_ids: list[str] = []
        except ImportError:
            self._faiss_index = None

    def add(self, id: str, embedding: np.ndarray, metadata: dict | None = None):
        """Add a vector to the store."""
        embedding = embedding.astype(np.float32)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        self._vectors[id] = embedding
        self._metadata[id] = metadata or {}

        if self._faiss_index is not None:
            import faiss
            self._faiss_index.add(embedding.reshape(1, -1))
            self._faiss_ids.append(id)

    def search(self, query_embedding: np.ndarray, top_k: int = 10, min_score: float = 0.0) -> list[SearchResult]:
        """Find most similar vectors."""
        if not self._vectors:
            return []

        query = query_embedding.astype(np.float32)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm

        if self._faiss_index is not None and self._faiss_index.ntotal > 0:
            import faiss
            scores, indices = self._faiss_index.search(query.reshape(1, -1), min(top_k, self._faiss_index.ntotal))
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and score >= min_score:
                    vec_id = self._faiss_ids[idx]
                    results.append(SearchResult(id=vec_id, score=float(score), metadata=self._metadata.get(vec_id, {})))
            return results
        else:
            # Numpy fallback
            ids = list(self._vectors.keys())
            matrix = np.array([self._vectors[id] for id in ids])
            scores = matrix @ query
            sorted_indices = np.argsort(scores)[::-1][:top_k]
            results = []
            for idx in sorted_indices:
                if scores[idx] >= min_score:
                    results.append(SearchResult(id=ids[idx], score=float(scores[idx]), metadata=self._metadata.get(ids[idx], {})))
            return results

    def remove(self, id: str):
        """Remove a vector (note: FAISS doesn't support removal, so we rebuild)."""
        self._vectors.pop(id, None)
        self._metadata.pop(id, None)

    @property
    def size(self) -> int:
        return len(self._vectors)


class AgentVectorStores:
    """Manages per-agent, per-tier vector stores."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._stores: dict[str, dict[str, VectorStore]] = {}  # agent_id -> tier -> store

    def get_store(self, agent_id: str, tier: str) -> VectorStore:
        if agent_id not in self._stores:
            self._stores[agent_id] = {}
        if tier not in self._stores[agent_id]:
            self._stores[agent_id][tier] = VectorStore(self.dimension)
        return self._stores[agent_id][tier]

    def search_all_tiers(self, agent_id: str, query_embedding: np.ndarray, top_k: int = 10) -> list[SearchResult]:
        """Search across all tiers for an agent, prioritizing corrections."""
        results = []
        tier_order = ["correction", "procedural", "semantic", "episodic"]
        for tier in tier_order:
            store = self.get_store(agent_id, tier)
            tier_results = store.search(query_embedding, top_k=top_k)
            for r in tier_results:
                r.metadata["tier"] = tier
            results.extend(tier_results)

        # Sort by score but boost corrections
        for r in results:
            if r.metadata.get("tier") == "correction":
                r.score *= 1.5  # Corrections always surface first

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def stats(self, agent_id: str) -> dict:
        if agent_id not in self._stores:
            return {"tiers": {}}
        return {"tiers": {tier: store.size for tier, store in self._stores[agent_id].items()}}


# Global singleton
agent_vectors = AgentVectorStores()
