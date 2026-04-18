"""Gnosis RAG Engine — Document ingestion, chunking, embedding, and retrieval."""

import uuid
import hashlib
import logging
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.rag")


@dataclass
class Document:
    id: str
    name: str
    content: str
    chunk_count: int = 0
    agent_id: Optional[str] = None
    uploaded_by: Optional[str] = None
    file_type: str = "txt"
    size_bytes: int = 0
    checksum: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Chunk:
    id: str
    document_id: str
    content: str
    chunk_index: int
    embedding: Optional[list] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class RAGResult:
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    score: float
    chunk_index: int


class TextChunker:
    """Split text into overlapping chunks for embedding."""

    @staticmethod
    def chunk(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        # Try to split on paragraphs first
        paragraphs = re.split(r"\n\n+", text)

        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += "\n\n" + para if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # If paragraph itself is too long, split by sentences
                if len(para) > chunk_size:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    current_chunk = ""
                    for sent in sentences:
                        if len(current_chunk) + len(sent) <= chunk_size:
                            current_chunk += " " + sent if current_chunk else sent
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = sent
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk.strip())

        # Add overlap between chunks
        if overlap > 0 and len(chunks) > 1:
            overlapped = [chunks[0]]
            for i in range(1, len(chunks)):
                prev_end = (
                    chunks[i - 1][-overlap:]
                    if len(chunks[i - 1]) > overlap
                    else chunks[i - 1]
                )
                overlapped.append(prev_end + " " + chunks[i])
            chunks = overlapped

        return [c for c in chunks if c.strip()]


class RAGEngine:
    """Manages document ingestion, chunking, and retrieval."""

    def __init__(self):
        self._documents: Dict[str, Document] = {}
        self._chunks: Dict[str, Chunk] = {}  # chunk_id -> Chunk
        self._doc_chunks: Dict[str, List[str]] = {}  # doc_id -> chunk_ids
        self._embeddings: Dict[str, list] = {}  # chunk_id -> embedding
        self._chunker = TextChunker()

    def _embed(self, text: str) -> list:
        """Get embedding for text."""
        try:
            from app.core.embeddings import embedding_service

            return embedding_service.embed(text).tolist()
        except Exception:
            # Fallback: simple hash-based embedding
            import numpy as np

            h = hashlib.md5(text.encode()).hexdigest()
            np.random.seed(int(h[:8], 16))
            vec = np.random.randn(384).astype(float)
            vec = vec / np.linalg.norm(vec)
            return vec.tolist()

    async def ingest(
        self,
        name: str,
        content: str,
        file_type: str = "txt",
        agent_id: str = None,
        uploaded_by: str = None,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> Document:
        """Ingest a document: chunk it, embed chunks, store for retrieval."""
        doc_id = str(uuid.uuid4())
        checksum = hashlib.sha256(content.encode()).hexdigest()

        doc = Document(
            id=doc_id,
            name=name,
            content=content,
            agent_id=agent_id,
            uploaded_by=uploaded_by,
            file_type=file_type,
            size_bytes=len(content.encode()),
            checksum=checksum,
        )

        # Chunk the content
        text_chunks = self._chunker.chunk(
            content, chunk_size=chunk_size, overlap=overlap
        )
        chunk_ids = []

        for i, chunk_text in enumerate(text_chunks):
            chunk_id = str(uuid.uuid4())
            embedding = self._embed(chunk_text)

            chunk = Chunk(
                id=chunk_id,
                document_id=doc_id,
                content=chunk_text,
                chunk_index=i,
                embedding=embedding,
                metadata={
                    "document_name": name,
                    "file_type": file_type,
                    "agent_id": agent_id or "",
                },
            )
            self._chunks[chunk_id] = chunk
            self._embeddings[chunk_id] = embedding
            chunk_ids.append(chunk_id)

        doc.chunk_count = len(chunk_ids)
        self._documents[doc_id] = doc
        self._doc_chunks[doc_id] = chunk_ids

        logger.info(f"Document ingested: {doc_id} ({name}, {len(text_chunks)} chunks)")
        return doc

    async def search(
        self, query: str, agent_id: str = None, top_k: int = 5
    ) -> List[RAGResult]:
        """Search across all ingested documents."""
        import numpy as np

        query_embedding = np.array(self._embed(query))
        query_norm = np.linalg.norm(query_embedding)
        if query_norm > 0:
            query_embedding = query_embedding / query_norm

        scores = []
        for chunk_id, embedding in self._embeddings.items():
            chunk = self._chunks.get(chunk_id)
            if not chunk:
                continue
            # Filter by agent if specified
            if agent_id and chunk.metadata.get("agent_id") != agent_id:
                continue

            emb = np.array(embedding)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            score = float(np.dot(query_embedding, emb))
            scores.append((chunk_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for chunk_id, score in scores[:top_k]:
            chunk = self._chunks[chunk_id]
            doc = self._documents.get(chunk.document_id)
            results.append(
                RAGResult(
                    chunk_id=chunk_id,
                    document_id=chunk.document_id,
                    document_name=doc.name if doc else "unknown",
                    content=chunk.content,
                    score=round(score, 4),
                    chunk_index=chunk.chunk_index,
                )
            )

        return results

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self._documents.get(doc_id)

    def list_documents(self, agent_id: str = None) -> List[Document]:
        docs = list(self._documents.values())
        if agent_id:
            docs = [d for d in docs if d.agent_id == agent_id]
        return sorted(docs, key=lambda d: d.created_at, reverse=True)

    def delete_document(self, doc_id: str) -> bool:
        doc = self._documents.pop(doc_id, None)
        if not doc:
            return False
        chunk_ids = self._doc_chunks.pop(doc_id, [])
        for cid in chunk_ids:
            self._chunks.pop(cid, None)
            self._embeddings.pop(cid, None)
        logger.info(f"Document deleted: {doc_id} ({len(chunk_ids)} chunks removed)")
        return True

    def get_chunks(self, doc_id: str) -> List[Chunk]:
        chunk_ids = self._doc_chunks.get(doc_id, [])
        return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]

    @property
    def stats(self) -> dict:
        return {
            "total_documents": len(self._documents),
            "total_chunks": len(self._chunks),
            "total_size_bytes": sum(d.size_bytes for d in self._documents.values()),
        }


rag_engine = RAGEngine()
