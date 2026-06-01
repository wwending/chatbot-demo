export type Intent = "chat" | "keyword" | "tool" | "rag" | string;

export interface Source {
  file_name: string;
  chunk_id: string;
  score: number;
  content_preview: string;
}

export interface ChatResponse {
  session_id: string;
  intent: Intent;
  answer: string;
  sources: Source[];
  tool_result: Record<string, unknown> | null;
  model: string;
  latency_ms: number;
}

export interface MessageRecord {
  id: number;
  session_id: string;
  role: "user" | "assistant" | string;
  content: string;
  intent: Intent | null;
  created_at: string;
}

export interface SessionSummary {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface HealthStatus {
  api: string;
  sqlite: boolean;
  vector_store: boolean;
  llm_configured: boolean;
  llm_provider: string;
  llm_model: string;
}

export interface KnowledgeImportResponse {
  imported_files: number;
  chunks: number;
  vector_store: string;
  files: string[];
}

export interface UiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: Intent | null;
  model?: string;
  latency_ms?: number;
  sources?: Source[];
  tool_result?: Record<string, unknown> | null;
}
