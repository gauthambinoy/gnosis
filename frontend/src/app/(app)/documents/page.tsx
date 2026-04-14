"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface Document {
  id: string;
  name: string;
  content: string;
  chunk_count: number;
  agent_id: string | null;
  file_type: string;
  size_bytes: number;
  checksum: string;
  created_at: string;
}

interface ChunkItem {
  id: string;
  content: string;
  chunk_index: number;
}

interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_name: string;
  content: string;
  score: number;
  chunk_index: number;
}

interface RAGStats {
  total_documents: number;
  total_chunks: number;
  total_size_bytes: number;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const FILE_TYPE_COLORS: Record<string, string> = {
  txt: "bg-blue-500/20 text-blue-400",
  md: "bg-purple-500/20 text-purple-400",
  csv: "bg-green-500/20 text-green-400",
  json: "bg-yellow-500/20 text-yellow-400",
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [stats, setStats] = useState<RAGStats>({ total_documents: 0, total_chunks: 0, total_size_bytes: 0 });
  const [loading, setLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);

  // Upload state
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Text ingest state
  const [showTextInput, setShowTextInput] = useState(false);
  const [textName, setTextName] = useState("");
  const [textContent, setTextContent] = useState("");
  const [textIngesting, setTextIngesting] = useState(false);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchPerformed, setSearchPerformed] = useState(false);

  // Filter
  const [agentFilter, setAgentFilter] = useState("");

  const fetchDocuments = useCallback(async () => {
    try {
      const params = agentFilter ? `?agent_id=${agentFilter}` : "";
      const [docsRes, statsRes] = await Promise.all([
        api.get(`/rag/documents${params}`),
        api.get("/rag/stats"),
      ]);
      if (docsRes.ok) {
        const data = await docsRes.json();
        setDocuments(data.documents || []);
      }
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [agentFilter]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append("file", file);
        if (agentFilter) formData.append("agent_id", agentFilter);
        const token = useAuth.getState().accessToken;
        await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/rag/ingest/file${agentFilter ? `?agent_id=${agentFilter}` : ""}`,
          {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: formData,
          }
        );
      }
      await fetchDocuments();
    } catch {
      // silent
    } finally {
      setUploading(false);
    }
  };

  const handleTextIngest = async () => {
    if (!textName.trim() || !textContent.trim()) return;
    setTextIngesting(true);
    try {
      await api.post("/rag/ingest/text", {
        name: textName,
        content: textContent,
        agent_id: agentFilter || undefined,
      });
      setTextName("");
      setTextContent("");
      setShowTextInput(false);
      await fetchDocuments();
    } catch {
      // silent
    } finally {
      setTextIngesting(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    setSearchPerformed(true);
    try {
      const res = await api.post("/rag/search", {
        query: searchQuery,
        agent_id: agentFilter || undefined,
        top_k: 10,
      });
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      }
    } catch {
      // silent
    } finally {
      setSearching(false);
    }
  };

  const handleViewChunks = async (docId: string) => {
    if (selectedDoc === docId) {
      setSelectedDoc(null);
      setChunks([]);
      return;
    }
    setSelectedDoc(docId);
    setChunksLoading(true);
    try {
      const res = await api.get(`/rag/documents/${docId}/chunks`);
      if (res.ok) {
        const data = await res.json();
        setChunks(data.chunks || []);
      }
    } catch {
      // silent
    } finally {
      setChunksLoading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await api.delete(`/rag/documents/${docId}`);
      if (selectedDoc === docId) {
        setSelectedDoc(null);
        setChunks([]);
      }
      await fetchDocuments();
    } catch {
      // silent
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFileUpload(e.dataTransfer.files);
  };

  const scoreColor = (score: number) => {
    if (score >= 0.8) return "text-green-400";
    if (score >= 0.5) return "text-yellow-400";
    return "text-gnosis-muted";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-gnosis-text">
            📄 Documents
          </h1>
          <p className="text-sm text-gnosis-muted mt-1">
            RAG knowledge base — upload, chunk, embed, and search documents
          </p>
        </div>
        <button
          onClick={() => setShowTextInput(!showTextInput)}
          className="px-4 py-2 bg-gnosis-primary text-black font-medium rounded-xl hover:bg-gnosis-primary/90 transition-colors text-sm"
        >
          + Paste Text
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Documents", value: stats.total_documents, icon: "📄" },
          { label: "Chunks", value: stats.total_chunks, icon: "🧩" },
          { label: "Total Size", value: formatBytes(stats.total_size_bytes), icon: "💾" },
        ].map((s) => (
          <div
            key={s.label}
            className="bg-[#0A0A0A] border border-white/[0.06] rounded-2xl p-4"
          >
            <div className="flex items-center gap-2 text-gnosis-muted text-xs mb-1">
              <span>{s.icon}</span>
              {s.label}
            </div>
            <div className="text-xl font-bold text-gnosis-text">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Upload Area */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200
          ${dragOver
            ? "border-gnosis-primary bg-gnosis-primary/5"
            : "border-white/[0.08] hover:border-white/[0.15] bg-[#0A0A0A]"
          }
          ${uploading ? "opacity-50 pointer-events-none" : ""}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".txt,.md,.csv,.json"
          className="hidden"
          onChange={(e) => handleFileUpload(e.target.files)}
        />
        <div className="text-3xl mb-2">{uploading ? "⏳" : "📁"}</div>
        <p className="text-gnosis-text font-medium">
          {uploading ? "Uploading..." : "Drop files here or click to upload"}
        </p>
        <p className="text-gnosis-muted text-xs mt-1">
          TXT, MD, CSV, JSON — files are chunked and embedded automatically
        </p>
      </div>

      {/* Text Input Panel */}
      <AnimatePresence>
        {showTextInput && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-[#0A0A0A] border border-white/[0.06] rounded-2xl p-5 space-y-3">
              <input
                type="text"
                placeholder="Document name..."
                value={textName}
                onChange={(e) => setTextName(e.target.value)}
                className="w-full bg-[#050505] border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50"
              />
              <textarea
                placeholder="Paste document content..."
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                rows={6}
                className="w-full bg-[#050505] border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50 resize-none"
              />
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowTextInput(false)}
                  className="px-4 py-2 text-sm text-gnosis-muted hover:text-gnosis-text transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleTextIngest}
                  disabled={textIngesting || !textName.trim() || !textContent.trim()}
                  className="px-4 py-2 bg-gnosis-primary text-black font-medium rounded-xl hover:bg-gnosis-primary/90 transition-colors text-sm disabled:opacity-50"
                >
                  {textIngesting ? "Ingesting..." : "Ingest"}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Search */}
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <input
            type="text"
            placeholder="Search across all documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-full bg-[#0A0A0A] border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50"
          />
        </div>
        <input
          type="text"
          placeholder="Agent ID filter..."
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="w-40 bg-[#0A0A0A] border border-white/[0.08] rounded-xl px-3 py-2.5 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50"
        />
        <button
          onClick={handleSearch}
          disabled={searching || !searchQuery.trim()}
          className="px-5 py-2.5 bg-gnosis-primary text-black font-medium rounded-xl hover:bg-gnosis-primary/90 transition-colors text-sm disabled:opacity-50"
        >
          {searching ? "..." : "Search"}
        </button>
      </div>

      {/* Search Results */}
      <AnimatePresence>
        {searchPerformed && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-2"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium text-gnosis-muted">
                Search Results ({searchResults.length})
              </h2>
              <button
                onClick={() => { setSearchPerformed(false); setSearchResults([]); setSearchQuery(""); }}
                className="text-xs text-gnosis-muted hover:text-gnosis-text"
              >
                Clear
              </button>
            </div>
            {searchResults.length === 0 ? (
              <p className="text-sm text-gnosis-muted py-4 text-center">No results found.</p>
            ) : (
              searchResults.map((r) => (
                <div
                  key={r.chunk_id}
                  className="bg-[#0A0A0A] border border-white/[0.06] rounded-xl p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gnosis-text">
                      {r.document_name}
                      <span className="text-gnosis-muted ml-2 text-xs">chunk #{r.chunk_index}</span>
                    </span>
                    <span className={`text-xs font-mono font-bold ${scoreColor(r.score)}`}>
                      {(r.score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-xs text-gnosis-muted leading-relaxed line-clamp-3">
                    {r.content}
                  </p>
                  {/* Score bar */}
                  <div className="mt-2 h-1 bg-white/[0.04] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gnosis-primary/60 rounded-full transition-all"
                      style={{ width: `${Math.max(r.score * 100, 2)}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Document List */}
      <div className="space-y-2">
        <h2 className="text-sm font-medium text-gnosis-muted">
          Documents ({documents.length})
        </h2>
        {loading ? (
          <div className="text-center py-8 text-gnosis-muted text-sm">Loading...</div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12 text-gnosis-muted text-sm">
            No documents yet. Upload files or paste text to get started.
          </div>
        ) : (
          documents.map((doc) => (
            <div key={doc.id}>
              <div
                className="bg-[#0A0A0A] border border-white/[0.06] rounded-xl p-4 hover:border-white/[0.1] transition-colors cursor-pointer"
                onClick={() => handleViewChunks(doc.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <span
                      className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-md ${
                        FILE_TYPE_COLORS[doc.file_type] || "bg-white/10 text-gnosis-muted"
                      }`}
                    >
                      {doc.file_type}
                    </span>
                    <span className="text-sm font-medium text-gnosis-text truncate">
                      {doc.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 shrink-0 text-xs text-gnosis-muted">
                    <span>{doc.chunk_count} chunks</span>
                    <span>{formatBytes(doc.size_bytes)}</span>
                    <span>{formatDate(doc.created_at)}</span>
                    {doc.agent_id && (
                      <span className="text-gnosis-primary/70 font-mono text-[10px]">
                        {doc.agent_id.slice(0, 8)}
                      </span>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
                      className="text-gnosis-muted hover:text-red-400 transition-colors"
                      title="Delete document"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </div>

              {/* Chunks panel */}
              <AnimatePresence>
                {selectedDoc === doc.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="ml-4 mt-1 mb-2 border-l-2 border-gnosis-primary/20 pl-4 space-y-2">
                      {chunksLoading ? (
                        <p className="text-xs text-gnosis-muted py-2">Loading chunks...</p>
                      ) : chunks.length === 0 ? (
                        <p className="text-xs text-gnosis-muted py-2">No chunks found.</p>
                      ) : (
                        chunks.map((c) => (
                          <div
                            key={c.id}
                            className="bg-[#080808] border border-white/[0.04] rounded-lg p-3"
                          >
                            <span className="text-[10px] text-gnosis-primary font-mono">
                              chunk #{c.chunk_index}
                            </span>
                            <p className="text-xs text-gnosis-muted mt-1 leading-relaxed line-clamp-4 whitespace-pre-wrap">
                              {c.content}
                            </p>
                          </div>
                        ))
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
