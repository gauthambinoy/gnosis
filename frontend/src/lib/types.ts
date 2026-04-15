/**
 * Shared TypeScript interfaces for the Gnosis platform.
 * Used across pages to replace `any` with proper typing.
 */

// ─── System Control ───

export interface SystemInfo {
  hostname: string;
  platform: string;
  architecture: string;
  cpu_count: number;
  cpu_percent: number;
  memory_total: number;
  memory_used: number;
  memory_percent: number;
  disk_total: number;
  disk_used: number;
  disk_percent: number;
  uptime_seconds: number;
  python_version: string;
  boot_time: number;
  load_avg: [number, number, number];
}

export interface ProcessInfo {
  pid: number;
  name: string;
  status: string;
  cpu_percent: number;
  memory_percent: number;
  memory_rss: number;
  create_time: number;
  username: string;
  cmdline: string;
}

export interface DirectoryEntry {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  modified: number;
  permissions: string;
}

export interface DirectoryData {
  path: string;
  entries: DirectoryEntry[];
  parent: string | null;
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
  containers: DockerContainer[];
  images: { id: string; tags: string[]; size: number }[];
  volumes: { name: string; driver: string; mountpoint: string }[];
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  action: string;
  user: string;
  details: string;
  severity: "info" | "warning" | "critical";
  ip_address?: string;
}

export interface TerminalEntry {
  command: string;
  output: string;
  exit_code: number;
  timestamp: string;
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
