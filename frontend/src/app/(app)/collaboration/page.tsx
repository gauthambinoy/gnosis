"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";

interface Room {
  id: string;
  name: string;
  topic: string;
  agent_count: number;
  message_count: number;
  status: string;
  created_at: string;
}

interface RoomDetail {
  id: string;
  name: string;
  topic: string;
  agent_ids: string[];
  agent_names: Record<string, string>;
  messages: Message[];
  status: string;
  created_at: string;
  resolved_at: string | null;
  conclusion: string | null;
  max_rounds: number;
}

interface Message {
  id: string;
  room_id: string;
  agent_id: string;
  agent_name: string;
  content: string;
  message_type: string;
  in_reply_to: string | null;
  timestamp: string;
}

interface CollabStats {
  total_rooms: number;
  total_messages: number;
  by_status: Record<string, number>;
}

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500/20 text-green-400",
  resolved: "bg-blue-500/20 text-blue-400",
  archived: "bg-gray-500/20 text-gray-400",
};

const MSG_TYPE_ICONS: Record<string, string> = {
  discussion: "💬",
  proposal: "💡",
  decision: "✅",
  question: "❓",
  answer: "📝",
};

export default function CollaborationPage() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [stats, setStats] = useState<CollabStats | null>(null);
  const [selectedRoom, setSelectedRoom] = useState<RoomDetail | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);
  const [newRoom, setNewRoom] = useState({ name: "", topic: "", agent_ids: "", max_rounds: 5 });
  const [loading, setLoading] = useState(false);

  const fetchRooms = useCallback(async () => {
    try {
      const url = filterStatus
        ? `/collaboration/rooms?status=${filterStatus}`
        : `/collaboration/rooms`;
      const [roomsRes, statsRes] = await Promise.all([
        api.get(url),
        api.get("/collaboration/stats"),
      ]);
      const roomsData = await roomsRes.json();
      const statsData = await statsRes.json();
      setRooms(roomsData.rooms || []);
      setStats(statsData);
    } catch {
      /* API unavailable */
    }
  }, [filterStatus]);

  useEffect(() => {
    fetchRooms();
  }, [fetchRooms]);

  const openRoom = async (roomId: string) => {
    try {
      const res = await api.get(`/collaboration/rooms/${roomId}`);
      const data = await res.json();
      setSelectedRoom(data);
    } catch {
      /* ignore */
    }
  };

  const createRoom = async () => {
    if (!newRoom.name || !newRoom.topic || !newRoom.agent_ids) return;
    setLoading(true);
    try {
      const agentIds = newRoom.agent_ids.split(",").map((s) => s.trim()).filter(Boolean);
      const agentNames: Record<string, string> = {};
      agentIds.forEach((id, i) => {
        agentNames[id] = `Agent-${i + 1}`;
      });
      await api.post("/collaboration/rooms", {
        name: newRoom.name,
        topic: newRoom.topic,
        agent_ids: agentIds,
        agent_names: agentNames,
        max_rounds: newRoom.max_rounds,
      });
      setNewRoom({ name: "", topic: "", agent_ids: "", max_rounds: 5 });
      setShowCreate(false);
      await fetchRooms();
    } catch {
      /* ignore */
    }
    setLoading(false);
  };

  const runDiscussion = async (roomId: string) => {
    setLoading(true);
    try {
      await api.post(`/collaboration/rooms/${roomId}/discuss`);
      await openRoom(roomId);
      await fetchRooms();
    } catch {
      /* ignore */
    }
    setLoading(false);
  };

  const archiveRoom = async (roomId: string) => {
    try {
      await api.post(`/collaboration/rooms/${roomId}/archive`);
      setSelectedRoom(null);
      await fetchRooms();
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-gnosis-text flex items-center gap-3">
            <span className="text-4xl">🤝</span>
            Collaboration Rooms
          </h1>
          <p className="text-gnosis-muted mt-1">
            Multi-agent discussion rooms for collaborative problem solving
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-gnosis-primary/20 text-gnosis-primary rounded-xl text-sm font-medium hover:bg-gnosis-primary/30 transition-colors"
        >
          + New Room
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4">
            <p className="text-xs text-gnosis-muted uppercase tracking-wider">Total Rooms</p>
            <p className="text-2xl font-bold text-gnosis-text mt-1">{stats.total_rooms}</p>
          </div>
          <div className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4">
            <p className="text-xs text-gnosis-muted uppercase tracking-wider">Total Messages</p>
            <p className="text-2xl font-bold text-gnosis-text mt-1">{stats.total_messages}</p>
          </div>
          {Object.entries(stats.by_status).map(([status, count]) => (
            <div key={status} className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4">
              <p className="text-xs text-gnosis-muted uppercase tracking-wider">{status}</p>
              <p className="text-2xl font-bold text-gnosis-text mt-1">{count}</p>
            </div>
          ))}
        </div>
      )}

      {/* Create Room Form */}
      {showCreate && (
        <div className="bg-gnosis-surface border border-gnosis-border rounded-xl p-6">
          <h2 className="text-lg font-semibold text-gnosis-text mb-4">Create New Room</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="Room name"
              value={newRoom.name}
              onChange={(e) => setNewRoom({ ...newRoom, name: e.target.value })}
              className="bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted focus:outline-none focus:border-gnosis-primary"
            />
            <input
              type="text"
              placeholder="Agent IDs (comma-separated)"
              value={newRoom.agent_ids}
              onChange={(e) => setNewRoom({ ...newRoom, agent_ids: e.target.value })}
              className="bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted focus:outline-none focus:border-gnosis-primary"
            />
            <textarea
              placeholder="Discussion topic"
              value={newRoom.topic}
              onChange={(e) => setNewRoom({ ...newRoom, topic: e.target.value })}
              rows={2}
              className="md:col-span-2 bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted focus:outline-none focus:border-gnosis-primary resize-none"
            />
            <div className="flex items-center gap-3">
              <label className="text-sm text-gnosis-muted">Max Rounds:</label>
              <input
                type="number"
                min={1}
                max={20}
                value={newRoom.max_rounds}
                onChange={(e) => setNewRoom({ ...newRoom, max_rounds: parseInt(e.target.value) || 5 })}
                className="w-20 bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary"
              />
            </div>
            <div className="flex justify-end">
              <button
                onClick={createRoom}
                disabled={loading}
                className="px-4 py-2 bg-gnosis-primary text-white rounded-lg text-sm font-medium hover:bg-gnosis-primary/80 transition-colors disabled:opacity-50"
              >
                {loading ? "Creating..." : "Create Room"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Room List */}
        <div className="lg:col-span-1 space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-gnosis-text flex-1">Rooms</h2>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-gnosis-bg border border-gnosis-border rounded-lg px-2 py-1 text-xs text-gnosis-text"
            >
              <option value="">All</option>
              <option value="active">Active</option>
              <option value="resolved">Resolved</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          {rooms.length === 0 && (
            <p className="text-sm text-gnosis-muted text-center py-8">No rooms yet. Create one to get started.</p>
          )}
          {rooms.map((room) => (
            <div
              key={room.id}
              onClick={() => openRoom(room.id)}
              className={`bg-gnosis-surface border border-gnosis-border rounded-xl p-4 cursor-pointer hover:border-gnosis-primary/50 transition-colors ${
                selectedRoom?.id === room.id ? "border-gnosis-primary" : ""
              }`}
            >
              <div className="flex items-start justify-between">
                <h3 className="text-sm font-medium text-gnosis-text">{room.name}</h3>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${STATUS_COLORS[room.status] || ""}`}>
                  {room.status}
                </span>
              </div>
              <p className="text-xs text-gnosis-muted mt-1 line-clamp-2">{room.topic}</p>
              <div className="flex gap-3 mt-2 text-[10px] text-gnosis-muted">
                <span>👥 {room.agent_count} agents</span>
                <span>💬 {room.message_count} msgs</span>
              </div>
            </div>
          ))}
        </div>

        {/* Room Detail */}
        <div className="lg:col-span-2">
          {selectedRoom ? (
            <div className="bg-gnosis-surface border border-gnosis-border rounded-xl p-6 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gnosis-text">{selectedRoom.name}</h2>
                  <p className="text-sm text-gnosis-muted mt-1">{selectedRoom.topic}</p>
                </div>
                <div className="flex gap-2">
                  {selectedRoom.status === "active" && (
                    <button
                      onClick={() => runDiscussion(selectedRoom.id)}
                      disabled={loading}
                      className="px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg text-xs hover:bg-green-500/30 transition-colors disabled:opacity-50"
                    >
                      {loading ? "Running..." : "▶ Run Discussion"}
                    </button>
                  )}
                  {selectedRoom.status !== "archived" && (
                    <button
                      onClick={() => archiveRoom(selectedRoom.id)}
                      className="px-3 py-1.5 bg-gray-500/20 text-gray-400 rounded-lg text-xs hover:bg-gray-500/30 transition-colors"
                    >
                      Archive
                    </button>
                  )}
                </div>
              </div>

              {/* Agents */}
              <div className="flex flex-wrap gap-2">
                {Object.entries(selectedRoom.agent_names).map(([id, name]) => (
                  <span
                    key={id}
                    className="text-[10px] px-2 py-1 bg-gnosis-primary/10 text-gnosis-primary rounded-full"
                  >
                    {name}
                  </span>
                ))}
              </div>

              {/* Conclusion */}
              {selectedRoom.conclusion && (
                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                  <p className="text-xs font-medium text-blue-400 mb-1">✅ Conclusion</p>
                  <p className="text-sm text-gnosis-text">{selectedRoom.conclusion}</p>
                </div>
              )}

              {/* Messages */}
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {selectedRoom.messages.length === 0 && (
                  <p className="text-sm text-gnosis-muted text-center py-4">
                    No messages yet. Run a discussion to start.
                  </p>
                )}
                {selectedRoom.messages.map((msg) => (
                  <div key={msg.id} className="bg-gnosis-bg rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs">{MSG_TYPE_ICONS[msg.message_type] || "💬"}</span>
                      <span className="text-xs font-medium text-gnosis-primary">{msg.agent_name}</span>
                      <span className="text-[10px] text-gnosis-muted ml-auto">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-gnosis-text">{msg.content}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-gnosis-surface border border-gnosis-border rounded-xl p-12 text-center">
              <p className="text-4xl mb-3">🤝</p>
              <p className="text-gnosis-muted">Select a room to view the discussion</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
