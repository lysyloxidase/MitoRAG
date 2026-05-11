"use client";

import { ArrowUp, BookOpen, Brain, ExternalLink, Loader2, User } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";

import { AgentTracePanel } from "@/components/agent-trace-panel";
import { ContradictionBadge } from "@/components/contradiction-badge";
import { renderCitations } from "@/components/citation-link";
import { AGENT_TRACE, SUGGESTED_QUESTIONS } from "@/lib/mock-data";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const STREAM_STEP = 30;

type Role = "user" | "assistant";

interface SourcePaper {
  citation: string;
  title: string;
  source: string;
  pmid?: string | null;
  doi?: string | null;
  year?: number | null;
  score: number;
  snippet: string;
  url?: string | null;
}

interface Message {
  id: string;
  role: Role;
  content: string;
  streaming?: boolean;
  hasContradiction?: boolean;
  confidence?: number;
  sources?: SourcePaper[];
}

function uid() {
  return Math.random().toString(36).slice(2);
}

async function fetchAnswer(question: string): Promise<{
  answer: string;
  confidence: number;
  hasContradiction: boolean;
  sources: SourcePaper[];
}> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 180_000);
  try {
    const res = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`API error ${res.status}`);
    const data = await res.json();
    const hasContradiction = Array.isArray(data.contradictions) && data.contradictions.length > 0;
    return {
      answer: data.answer ?? "",
      confidence: data.confidence ?? 0,
      hasContradiction,
      sources: Array.isArray(data.sources) ? data.sources : [],
    };
  } finally {
    window.clearTimeout(timeout);
  }
}

function mockAnswer(question: string): string {
  const q = question.toLowerCase();
  if (q.includes("drug") || q.includes("therap") || q.includes("treatment")) {
    return "**Answering: drug-targeted approaches to mitochondrial dysfunction**\n\nIdebenone bypasses impaired Complex I electron transfer and is approved in Europe for LHON [PMID:26988832]. Urolithin A activates mitophagy and improves muscle endurance in older adults [doi:10.1038/s41591-022-01892-8]. MitoQ targets matrix-proximal ROS via a triphenylphosphonium moiety [PMID:18039652].\n\n**References used.**\n- [PMID:26988832] — Idebenone for LHON\n- [PMID:18039652] — MitoQ targeting\n- [doi:10.1038/s41591-022-01892-8] — Urolithin A trial";
  }
  if (q.includes("melas") || q.includes("3243")) {
    return "**Answering: MELAS pathophysiology**\n\nMELAS is most commonly caused by the m.3243A>G transition in MT-TL1 encoding mitochondrial tRNA-Leu [PMID:25613900]. Threshold for clinical expression is typically >80% heteroplasmy in affected tissues such as skeletal muscle and brain.\n\n**References used.**\n- [PMID:25613900] — MELAS molecular features";
  }
  return `For "${question}" — connect the API to retrieve full PubMed/S2/EuropePMC evidence.`;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setInput("");
    setLoading(true);

    const userMsg: Message = { id: uid(), role: "user", content: trimmed };
    const assistantId = uid();
    const assistantMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      streaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    let fullText = "";
    let confidence = 0;
    let hasContradiction = false;
    let sources: SourcePaper[] = [];

    try {
      const result = await fetchAnswer(trimmed);
      fullText = result.answer;
      confidence = result.confidence;
      hasContradiction = result.hasContradiction;
      sources = result.sources;
    } catch {
      fullText = mockAnswer(trimmed);
      hasContradiction = false;
    }

    if (!fullText) {
      fullText = "No answer produced — please try a more specific mitochondrial question.";
    }

    let cursor = 0;
    const interval = window.setInterval(() => {
      cursor += STREAM_STEP;
      const chunk = fullText.slice(0, cursor);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: chunk, streaming: cursor < fullText.length } : m
        )
      );
      if (cursor >= fullText.length) {
        window.clearInterval(interval);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: fullText,
                  streaming: false,
                  hasContradiction,
                  confidence,
                  sources,
                }
              : m
          )
        );
        setLoading(false);
      }
    }, 26);
  }

  const empty = messages.length === 0;

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col">
      <section className="grid flex-1 grid-cols-1 xl:grid-cols-[1fr_360px] overflow-hidden">
        <div className="flex flex-col overflow-hidden">
          {/* Conversation thread */}
          <div className="scrollbar-thin flex-1 overflow-y-auto px-4 py-6">
            {empty ? (
              <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
                <div>
                  <Brain className="mx-auto mb-3 text-gene" size={40} />
                  <h2 className="text-xl font-semibold text-ink">MitoRAG Research Assistant</h2>
                  <p className="mt-1 text-sm text-muted">
                    Ask anything about mitochondria — the agents will search PubMed, Semantic Scholar,
                    Europe PMC, and bioRxiv, then synthesize a cited answer.
                  </p>
                </div>
                <div className="flex max-w-2xl flex-wrap justify-center gap-2">
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      className="rounded border border-line bg-[#111b24] px-3 py-2 text-sm text-muted hover:border-gene hover:text-ink"
                      key={q}
                      onClick={() => sendMessage(q)}
                      type="button"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mx-auto max-w-3xl space-y-6">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}
                  >
                    {msg.role === "assistant" && (
                      <div className="mr-3 mt-1 flex-shrink-0">
                        <div className="grid h-8 w-8 place-items-center rounded-full bg-gene text-[#071019]">
                          <Brain size={15} />
                        </div>
                      </div>
                    )}

                    <div className={`max-w-[85%] ${msg.role === "user" ? "order-1" : ""}`}>
                      {msg.role === "user" ? (
                        <div className="rounded-2xl rounded-tr-sm bg-gene px-4 py-3 text-[#071019]">
                          <p className="text-sm font-medium">{msg.content}</p>
                        </div>
                      ) : (
                        <div className="rounded-2xl rounded-tl-sm border border-line bg-[#0f1922] px-5 py-4 shadow-glow">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            {msg.hasContradiction && !msg.streaming && (
                              <ContradictionBadge label="Contradiction detected" />
                            )}
                            {msg.streaming && (
                              <span className="inline-flex items-center gap-1.5 text-xs text-muted">
                                <Loader2 className="animate-spin" size={12} />
                                searching literature…
                              </span>
                            )}
                            {!msg.streaming && msg.confidence != null && msg.confidence > 0 && (
                              <span className="text-xs text-muted">
                                confidence {(msg.confidence * 100).toFixed(0)}%
                              </span>
                            )}
                            {!msg.streaming && msg.sources && msg.sources.length > 0 && (
                              <span className="inline-flex items-center gap-1 text-xs text-muted">
                                <BookOpen size={12} />
                                {msg.sources.length} sources
                              </span>
                            )}
                          </div>

                          {msg.content ? (
                            <FormattedAnswer text={msg.content} />
                          ) : (
                            <p className="text-muted italic text-sm">
                              Fanning out to PubMed, Semantic Scholar, Europe PMC, and bioRxiv…
                            </p>
                          )}

                          {!msg.streaming && msg.sources && msg.sources.length > 0 && (
                            <SourceList sources={msg.sources} />
                          )}
                        </div>
                      )}
                    </div>

                    {msg.role === "user" && (
                      <div className="ml-3 mt-1 flex-shrink-0">
                        <div className="grid h-8 w-8 place-items-center rounded-full bg-[#1e2d3d] text-muted">
                          <User size={15} />
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {/* Suggested follow-ups */}
                {!loading && messages.length >= 2 && (
                  <div className="flex flex-wrap gap-2 pl-11">
                    {SUGGESTED_QUESTIONS.slice(0, 3).map((q) => (
                      <button
                        className="rounded border border-line bg-[#111b24] px-3 py-1.5 text-xs text-muted hover:border-gene hover:text-ink"
                        key={q}
                        onClick={() => sendMessage(q)}
                        type="button"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}

                <div ref={bottomRef} />
              </div>
            )}
          </div>

          {/* Input bar */}
          <form
            className="border-t border-line bg-[#0b1016] p-4"
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage(input);
            }}
          >
            <div className="mx-auto flex max-w-3xl items-end gap-3">
              <input
                ref={inputRef}
                className="min-h-12 flex-1 rounded-xl border border-line bg-[#111b24] px-4 text-sm text-ink outline-none placeholder:text-muted focus:border-gene disabled:opacity-50"
                disabled={loading}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage(input);
                  }
                }}
                placeholder="Ask any question about mitochondria..."
                value={input}
                autoFocus
              />
              <button
                className="grid h-12 w-12 flex-shrink-0 place-items-center rounded-xl bg-gene text-[#071019] hover:bg-[#79bdff] disabled:opacity-40"
                disabled={loading || !input.trim()}
                title="Send"
                type="submit"
              >
                {loading ? <Loader2 className="animate-spin" size={18} /> : <ArrowUp size={20} />}
              </button>
            </div>
          </form>
        </div>

        <aside className="border-l border-line bg-[#0e151c] overflow-y-auto">
          <AgentTracePanel trace={AGENT_TRACE} />
          <section className="space-y-4 border-t border-line p-5">
            <h2 className="font-semibold">Search coverage</h2>
            <div className="grid gap-2 text-sm text-muted">
              <div className="rounded border border-line bg-[#111c25] p-3">PubMed (NCBI E-utilities)</div>
              <div className="rounded border border-line bg-[#111c25] p-3">Semantic Scholar</div>
              <div className="rounded border border-line bg-[#111c25] p-3">Europe PMC</div>
              <div className="rounded border border-line bg-[#111c25] p-3">bioRxiv / medRxiv</div>
              <div className="rounded border border-line bg-[#111c25] p-3">PubTator3 annotations</div>
              <div className="rounded border border-line bg-[#111c25] p-3">Local PDF library + KG</div>
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}

function FormattedAnswer({ text }: { text: string }) {
  const lines = text.split("\n");
  const blocks: Array<{ kind: "h" | "li" | "p"; content: string }> = [];

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line.trim()) continue;
    const headerMatch = /^\*\*(.+?)\.\*\*\s*(.*)$/.exec(line) || /^\*\*(.+?)\*\*\s*(.*)$/.exec(line);
    if (headerMatch) {
      blocks.push({ kind: "h", content: headerMatch[1].trim() });
      const tail = headerMatch[2]?.trim();
      if (tail) blocks.push({ kind: "p", content: tail });
      continue;
    }
    if (line.trimStart().startsWith("- ")) {
      blocks.push({ kind: "li", content: line.trimStart().slice(2) });
      continue;
    }
    blocks.push({ kind: "p", content: line });
  }

  return (
    <div className="space-y-3 text-sm leading-7 text-[#d9e6f2]">
      {blocks.map((block, idx) => {
        if (block.kind === "h") {
          return (
            <h3 key={idx} className="mt-2 text-xs font-semibold uppercase tracking-wider text-gene">
              {block.content}
            </h3>
          );
        }
        if (block.kind === "li") {
          return (
            <div key={idx} className="flex gap-2">
              <span className="mt-2 inline-block h-1.5 w-1.5 flex-shrink-0 rounded-full bg-gene" />
              <p className="flex-1">{renderInline(block.content)}</p>
            </div>
          );
        }
        return (
          <p key={idx} className="whitespace-pre-wrap">
            {renderInline(block.content)}
          </p>
        );
      })}
    </div>
  );
}

function renderInline(text: string) {
  const boldSplit = text.split(/(\*\*[^*]+\*\*)/g);
  return boldSplit.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-ink">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <Fragment key={i}>{renderCitations(part)}</Fragment>;
  });
}

function SourceList({ sources }: { sources: SourcePaper[] }) {
  return (
    <details className="mt-4 rounded-lg border border-line bg-[#0b1219] p-3 text-xs">
      <summary className="cursor-pointer text-sm font-medium text-ink hover:text-gene">
        <BookOpen size={13} className="mr-1.5 inline" />
        Source papers ({sources.length})
      </summary>
      <ul className="mt-3 space-y-2.5">
        {sources.map((s, idx) => (
          <li key={`${s.citation}-${idx}`} className="rounded border border-line bg-[#0f1922] p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[10px] uppercase text-gene">{s.source}</span>
                  {s.year && <span className="text-muted">{s.year}</span>}
                  {s.citation && (
                    <span className="font-mono text-[11px] text-muted">{s.citation}</span>
                  )}
                </div>
                <p className="text-sm font-medium text-ink">{s.title || "Untitled"}</p>
                {s.snippet && (
                  <p className="mt-1.5 text-xs leading-5 text-muted">{s.snippet}</p>
                )}
              </div>
              {s.url && (
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex-shrink-0 text-muted hover:text-gene"
                  title="Open source"
                >
                  <ExternalLink size={14} />
                </a>
              )}
            </div>
          </li>
        ))}
      </ul>
    </details>
  );
}
