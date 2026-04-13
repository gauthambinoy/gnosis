"""Embedding service — generates vector embeddings for memory storage and retrieval."""
import hashlib
import numpy as np
from typing import Optional


class EmbeddingService:
    """Generates embeddings. Uses a lightweight approach that works without GPU."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dimension: int = 384):
        self.model_name = model_name
        self.dimension = dimension
        self._model = None
        self._cache: dict[str, np.ndarray] = {}
        self._max_cache = 10000

    def _get_model(self):
        """Lazy load the sentence-transformers model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                self._model = "fallback"
        return self._model

    def _cache_key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a text string."""
        key = self._cache_key(text)
        if key in self._cache:
            return self._cache[key]

        model = self._get_model()
        if model == "fallback":
            embedding = self._fallback_embed(text)
        else:
            embedding = model.encode(text, normalize_embeddings=True)

        # Cache it
        if len(self._cache) >= self._max_cache:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = embedding
        return embedding

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Batch embed multiple texts."""
        results = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            key = self._cache_key(text)
            if key in self._cache:
                results.append(self._cache[key])
            else:
                results.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)

        if uncached_texts:
            model = self._get_model()
            if model == "fallback":
                new_embeddings = [self._fallback_embed(t) for t in uncached_texts]
            else:
                new_embeddings = model.encode(uncached_texts, normalize_embeddings=True)

            for idx, emb in zip(uncached_indices, new_embeddings):
                key = self._cache_key(texts[idx])
                self._cache[key] = emb
                results[idx] = emb

        return results

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two embeddings."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    def _fallback_embed(self, text: str) -> np.ndarray:
        """Simple hash-based embedding when sentence-transformers isn't available."""
        np.random.seed(int(hashlib.md5(text.lower().encode()).hexdigest()[:8], 16) % (2**31))
        vec = np.random.randn(self.dimension).astype(np.float32)
        return vec / (np.linalg.norm(vec) + 1e-8)

    @property
    def cache_stats(self) -> dict:
        return {"cached": len(self._cache), "max": self._max_cache, "model": self.model_name, "dimension": self.dimension}


# Global singleton
embedding_service = EmbeddingService()
