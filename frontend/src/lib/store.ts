import { create } from "zustand";

interface Agent {
  id: string;
  name: string;
  description: string;
  status: "active" | "idle" | "paused" | "error";
  trust_level: number;
  actions_today: number;
  accuracy: number;
}

interface AppState {
  agents: Agent[];
  setAgents: (agents: Agent[]) => void;
  selectedAgentId: string | null;
  setSelectedAgentId: (id: string | null) => void;
  sidebarOpen: boolean;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  agents: [],
  setAgents: (agents) => set({ agents }),
  selectedAgentId: null,
  setSelectedAgentId: (id) => set({ selectedAgentId: id }),
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}));
