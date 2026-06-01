import type { ChatResponse, HealthStatus, KnowledgeImportResponse, MessageRecord, SessionSummary } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: options?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}

export function listSessions(userId?: string): Promise<SessionSummary[]> {
  const query = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
  return request<SessionSummary[]>(`/sessions${query}`);
}

export function listMessages(sessionId: string): Promise<MessageRecord[]> {
  return request<MessageRecord[]>(`/sessions/${sessionId}/messages`);
}

export function sendChat(userId: string, message: string, sessionId?: string | null): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, message, session_id: sessionId || null })
  });
}

export function importDefaultKnowledge(): Promise<KnowledgeImportResponse> {
  return request<KnowledgeImportResponse>("/knowledge/import", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export function uploadKnowledge(file: File): Promise<KnowledgeImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<KnowledgeImportResponse>("/knowledge/upload", {
    method: "POST",
    body: formData
  });
}
