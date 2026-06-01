import { ChangeEvent, FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Bot,
  Clock,
  Database,
  FileUp,
  History,
  MessageSquarePlus,
  RefreshCw,
  Send,
  Sparkles,
  UploadCloud,
  User
} from "lucide-react";
import {
  getHealth,
  importDefaultKnowledge,
  listMessages,
  listSessions,
  sendChat,
  uploadKnowledge
} from "./api";
import type { ChatResponse, HealthStatus, KnowledgeImportResponse, SessionSummary, UiMessage } from "./types";

const SAMPLE_PROMPTS = ["你好", "/time 北京", "/weather 上海", "根据知识库介绍一下这个项目的技术栈"];

function App() {
  const [userId, setUserId] = useState("demo");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);
  const [knowledgeStatus, setKnowledgeStatus] = useState<KnowledgeImportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void refreshHealth();
    void refreshSessions();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function refreshHealth() {
    try {
      setHealth(await getHealth());
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "健康检查失败");
    }
  }

  async function refreshSessions(nextUserId = userId) {
    try {
      setSessions(await listSessions(nextUserId));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "会话加载失败");
    }
  }

  async function openSession(id: string) {
    setSessionId(id);
    setLastResponse(null);
    const records = await listMessages(id);
    setMessages(
      records.map((item) => ({
        id: String(item.id),
        role: item.role === "assistant" ? "assistant" : "user",
        content: item.content,
        intent: item.intent
      }))
    );
  }

  function newSession() {
    setSessionId(null);
    setLastResponse(null);
    setMessages([]);
    setNotice("已准备新会话");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setLoading(true);
    setNotice("");
    const optimistic: UiMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text
    };
    setMessages((current) => [...current, optimistic]);

    try {
      const response = await sendChat(userId, text, sessionId);
      setSessionId(response.session_id);
      setLastResponse(response);
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.answer,
          intent: response.intent,
          model: response.model,
          latency_ms: response.latency_ms,
          sources: response.sources,
          tool_result: response.tool_result
        }
      ]);
      await refreshSessions();
      await refreshHealth();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "发送失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleImportDefault() {
    setLoading(true);
    setNotice("");
    try {
      const result = await importDefaultKnowledge();
      setKnowledgeStatus(result);
      await refreshHealth();
      setNotice(`已导入 ${result.imported_files} 个文件，生成 ${result.chunks} 个片段`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "导入失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setNotice("");
    try {
      const result = await uploadKnowledge(file);
      setKnowledgeStatus(result);
      await refreshHealth();
      setNotice(`已上传并索引 ${file.name}`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "上传失败");
    } finally {
      event.target.value = "";
      setLoading(false);
    }
  }

  const activeSession = useMemo(
    () => sessions.find((item) => item.id === sessionId),
    [sessions, sessionId]
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Sparkles size={20} />
          </div>
          <div>
            <h1>Knowledge Chatbot</h1>
            <p>FastAPI + RAG + Tools</p>
          </div>
        </div>

        <label className="field">
          <span>用户 ID</span>
          <input value={userId} onChange={(event) => setUserId(event.target.value || "demo")} />
        </label>

        <div className="side-actions">
          <button type="button" onClick={newSession} title="新建会话">
            <MessageSquarePlus size={17} />
            新建
          </button>
          <button type="button" onClick={() => refreshSessions()} title="刷新会话">
            <RefreshCw size={17} />
            刷新
          </button>
        </div>

        <div className="section-title">
          <History size={16} />
          会话
        </div>
        <div className="session-list">
          {sessions.length === 0 ? (
            <p className="empty">暂无会话，发送第一条消息后会自动创建。</p>
          ) : (
            sessions.map((item) => (
              <button
                type="button"
                key={item.id}
                className={item.id === sessionId ? "session active" : "session"}
                onClick={() => openSession(item.id)}
              >
                <span>{item.title || "新会话"}</span>
                <small>{new Date(item.updated_at).toLocaleString()}</small>
              </button>
            ))
          )}
        </div>
      </aside>

      <main className="chat-panel">
        <header className="chat-header">
          <div>
            <h2>{activeSession?.title || "新会话"}</h2>
            <p>{sessionId ? `Session: ${sessionId}` : "发送消息后自动创建会话"}</p>
          </div>
          <div className="prompt-row">
            {SAMPLE_PROMPTS.map((prompt) => (
              <button type="button" key={prompt} onClick={() => setInput(prompt)}>
                {prompt}
              </button>
            ))}
          </div>
        </header>

        <section className="messages">
          {messages.length === 0 ? (
            <div className="welcome">
              <Bot size={36} />
              <h2>开始一次可观测的智能问答</h2>
              <p>发送普通聊天、关键词、工具指令，或基于知识库的问题。</p>
            </div>
          ) : (
            messages.map((message) => <MessageBubble key={message.id} message={message} />)
          )}
          {loading ? (
            <div className="message assistant">
              <div className="avatar">
                <Bot size={18} />
              </div>
              <div className="bubble muted">处理中...</div>
            </div>
          ) : null}
          <div ref={endRef} />
        </section>

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="输入消息，例如：根据知识库介绍一下这个项目的技术栈"
            rows={2}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <button type="submit" disabled={loading || !input.trim()} title="发送">
            <Send size={19} />
          </button>
        </form>
        {notice ? <div className="notice">{notice}</div> : null}
      </main>

      <aside className="inspector">
        <Panel title="系统状态" icon={<Activity size={16} />}>
          <StatusRow label="API" value={health?.api ?? "unknown"} ok={health?.api === "ok"} />
          <StatusRow label="SQLite" value={health?.sqlite ? "ready" : "not ready"} ok={Boolean(health?.sqlite)} />
          <StatusRow
            label="向量库"
            value={health?.vector_store ? "ready" : "not ready"}
            ok={Boolean(health?.vector_store)}
          />
          <StatusRow
            label="大模型"
            value={health?.llm_configured ? health.llm_model : "offline-demo"}
            ok={Boolean(health?.llm_configured)}
            soft
          />
        </Panel>

        <Panel title="最近响应" icon={<Clock size={16} />}>
          {lastResponse ? (
            <div className="metric-grid">
              <Metric label="Intent" value={lastResponse.intent} />
              <Metric label="Model" value={lastResponse.model} />
              <Metric label="Latency" value={`${lastResponse.latency_ms} ms`} />
              <Metric label="Sources" value={String(lastResponse.sources.length)} />
            </div>
          ) : (
            <p className="empty">暂无响应数据。</p>
          )}
        </Panel>

        <Panel title="工具结果" icon={<Database size={16} />}>
          {lastResponse?.tool_result ? (
            <pre className="json-view">{JSON.stringify(lastResponse.tool_result, null, 2)}</pre>
          ) : (
            <p className="empty">触发 /time 或 /weather 后会显示。</p>
          )}
        </Panel>

        <Panel title="RAG 来源" icon={<FileUp size={16} />}>
          {lastResponse?.sources.length ? (
            <div className="source-list">
              {lastResponse.sources.map((source) => (
                <article key={source.chunk_id} className="source-card">
                  <div>
                    <strong>{source.file_name}</strong>
                    <span>{source.score.toFixed(3)}</span>
                  </div>
                  <p>{source.content_preview}</p>
                  <small>{source.chunk_id}</small>
                </article>
              ))}
            </div>
          ) : (
            <p className="empty">RAG 问答会在这里列出引用片段。</p>
          )}
        </Panel>

        <Panel title="知识库" icon={<UploadCloud size={16} />}>
          <button type="button" className="wide-button" onClick={handleImportDefault} disabled={loading}>
            <Database size={16} />
            导入默认知识库
          </button>
          <label className="upload-button">
            <UploadCloud size={16} />
            上传 .txt / .md
            <input type="file" accept=".txt,.md" onChange={handleUpload} />
          </label>
          {knowledgeStatus ? (
            <p className="knowledge-status">
              {knowledgeStatus.imported_files} 文件 · {knowledgeStatus.chunks} 片段
            </p>
          ) : null}
        </Panel>
      </aside>
    </div>
  );
}

function MessageBubble({ message }: { message: UiMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={isUser ? "message user-message" : "message assistant"}>
      {!isUser ? (
        <div className="avatar">
          <Bot size={18} />
        </div>
      ) : null}
      <div className="message-content">
        <div className="bubble">{message.content}</div>
        {!isUser ? (
          <div className="meta-row">
            {message.intent ? <span>{message.intent}</span> : null}
            {message.model ? <span>{message.model}</span> : null}
            {message.latency_ms !== undefined ? <span>{message.latency_ms} ms</span> : null}
          </div>
        ) : null}
      </div>
      {isUser ? (
        <div className="avatar user-avatar">
          <User size={18} />
        </div>
      ) : null}
    </div>
  );
}

function Panel({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <section className="panel">
      <h3>
        {icon}
        {title}
      </h3>
      {children}
    </section>
  );
}

function StatusRow({ label, value, ok, soft = false }: { label: string; value: string; ok: boolean; soft?: boolean }) {
  return (
    <div className="status-row">
      <span>{label}</span>
      <strong className={ok ? "ok" : soft ? "soft" : "bad"}>{value}</strong>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default App;
