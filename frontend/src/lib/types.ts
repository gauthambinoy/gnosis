/**
 * Shared TypeScript interfaces for the Gnosis platform.
 * Used across pages to replace `any` with proper typing.
 */

// ─── System Control ───

export interface SystemInfo {
  hostname: string;
  os: string;
  architecture: string;
  python_version: string;
  uptime_seconds: number;
  cpu: {
    cores: number;
    usage_percent: number;
    per_core?: number[];
  };
  memory: {
    total_gb: number;
    used_gb: number;
    available_gb: number;
    percent: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  };
  network: {
    bytes_sent?: number;
    bytes_recv?: number;
    packets_sent?: number;
    packets_recv?: number;
  };
  processes?: {
    total: number;
    running: number;
  };
  // Flat aliases kept for backward compat with other pages
  platform?: string;
  cpu_count?: number;
  cpu_percent?: number;
  memory_total?: number;
  memory_used?: number;
  memory_percent?: number;
  disk_total?: number;
  disk_used?: number;
  disk_percent?: number;
  boot_time?: number;
  load_avg?: [number, number, number];
}

export interface ProcessInfo {
  pid: number;
  name: string;
  status: string;
  cpu_percent: number;
  memory_percent: number;
  user: string;
}

export interface DirectoryEntry {
  name: string;
  type: "dir" | "file" | "unknown";
  size?: number;
  modified?: number;
  permissions?: string;
  error?: string;
}

export interface DirectoryData {
  path?: string;
  entries: DirectoryEntry[];
  count?: number;
  error?: string;
}

export interface DockerContainer {
  id: string;
  name: string;
  image: string;
  status: string;
  state: string;
  created: string;
  ports: string;
}

export interface DockerData {
  status?: { available: boolean; compose_available: boolean; note?: string };
  containers?: { output?: string; error?: string };
  stats?: { output?: string; error?: string };
}

export interface AuditEntry {
  timestamp: number;
  user_id: string;
  action: string;
  detail: string;
  result?: string;
}

export interface TerminalEntry {
  id?: string;
  command: string;
  output?: string;
  error?: string;
  exit_code: number;
  executed_at?: number;
  duration_ms?: number;
  executed_by?: string;
}

// ─── Agents ───

export type AgentStatus = "active" | "idle" | "paused" | "error" | "learning";

export interface Agent {
  id: string;
  name: string;
  description: string;
  personality: string;
  avatar_emoji: string;
  status: AgentStatus;
  trigger_type: string;
  trust_level: number;
  model: string;
  total_executions: number;
  success_rate: number;
  created_at: string;
  updated_at: string;
}

// ─── Executions ───

export interface Execution {
  id: string;
  agent_id: string;
  trigger_type: string;
  trigger_data: Record<string, unknown>;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  result: Record<string, unknown> | null;
  was_corrected: boolean;
  total_cost_usd: number;
  config_version_id: string | null;
  started_at: string;
  completed_at: string | null;
  duration_ms: number;
}

// ─── Memory ───

export type MemoryTier = "correction" | "episodic" | "semantic" | "procedural" | "sensory";

export interface MemoryEntry {
  id: string;
  agent_id: string;
  tier: MemoryTier;
  content: string;
  relevance_score: number;
  access_count: number;
  strength: number;
  last_accessed: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
}

// ─── Pipelines ───

export type PipelineStatus = "draft" | "active" | "running" | "completed" | "failed" | "paused";

export interface PipelineStep {
  id: string;
  agent_id: string;
  name: string;
  order: number;
  transform_input: string | null;
  condition: string | null;
  timeout_seconds: number;
  max_retries: number;
}

export interface Pipeline {
  id: string;
  name: string;
  description: string;
  steps: PipelineStep[];
  status: PipelineStatus;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

// ─── Billing ───

export interface UsageSummary {
  total_tokens: number;
  total_cost_usd: number;
  period_start: string;
  period_end: string;
  by_model: Record<string, { tokens: number; cost: number }>;
}

// ─── Files ───

export interface FileRecord {
  id: string;
  filename: string;
  original_name: string;
  size: number;
  mime_type: string;
  checksum: string;
  agent_id: string | null;
  uploaded_by: string | null;
  tags: string[];
  created_at: string;
}

// ─── WebSocket Events ───

export interface WSMessage<T = unknown> {
  type: string;
  data: T;
  timestamp: string;
}

export interface WSExecutionUpdate {
  execution_id: string;
  status: string;
  progress: number;
  message: string;
}

export interface WSDashboardUpdate {
  agents: { total: number; active: number };
  executions: { running: number; today: number };
  memory: { total_entries: number };
}

// ─── API Responses ───

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface APIError {
  detail: string;
  status_code: number;
}
