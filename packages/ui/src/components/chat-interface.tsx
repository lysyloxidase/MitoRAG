"use client";

import { ArrowUp, Brain, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";

import { AgentTracePanel } from "@/components/agent-trace-panel";
import { ContradictionBadge } from "@/components/contradiction-badge";
import { renderCitations } from "@/components/citation-link";
import { AGENT_TRACE, SAMPLE_ANSWER, SUGGESTED_QUESTIONS } from "@/lib/mock-data";

const STREAM_STEP = 34;

export function ChatInterface() {
  const [query, setQuery] = useState("How does Complex I contribute to ROS generation?");
  const [answer, setAnswer] = useState(SAMPLE_ANSWER);
  const [streaming, setStreaming] = useState(false);

  const hasContradiction = useMemo(
    () => answer.toLowerCase().includes("disputed") || answer.toLowerCase().includes("mptp"),
    [answer]
  );

  function runQuery(nextQuery = query) {
    const text = responseFor(nextQuery);
    setQuery(nextQuery);
    setAnswer("");
    setStreaming(true);
    let cursor = 0;
    const interval = window.setInterval(() => {
      cursor += STREAM_STEP;
      setAnswer(text.slice(0, cursor));
      if (cursor >= text.length) {
        window.clearInterval(interval);
        setStreaming(false);
      }
    }, 32);
  }

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col">
      <section className="grid flex-1 grid-cols-1 xl:grid-cols-[1fr_360px]">
        <div className="flex flex-col">
          <div className="border-b border-line px-5 py-4">
            <div className="flex flex-wrap items-center gap-2">
              {SUGGESTED_QUESTIONS.map((item) => (
                <button
                  className="rounded border border-line bg-[#111b24] px-3 py-2 text-sm text-muted hover:border-gene hover:text-ink"
                  key={item}
                  onClick={() => runQuery(item)}
                  type="button"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="scrollbar-thin flex-1 overflow-y-auto px-5 py-6">
            <div className="mx-auto max-w-5xl space-y-5">
              <div className="rounded border border-line bg-[#111b24] p-4">
                <div className="mb-2 text-sm text-muted">Research question</div>
                <p className="text-lg text-ink">{query}</p>
              </div>

              <article className="rounded border border-line bg-[#0f1922] p-5 shadow-glow">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2 font-semibold">
                    <Brain size={18} />
                    KG-grounded answer
                  </div>
                  <div className="flex items-center gap-2">
                    {hasContradiction ? <ContradictionBadge label="mPTP controversy" /> : null}
                    {streaming ? (
                      <span className="inline-flex items-center gap-2 text-sm text-muted">
                        <Loader2 className="animate-spin" size={14} />
                        streaming
                      </span>
                    ) : null}
                  </div>
                </div>
                <p className="whitespace-pre-wrap text-base leading-7 text-[#d9e6f2]">
                  {answer ? renderCitations(answer) : "Preparing retrieval, KG, and verification..."}
                </p>
              </article>
            </div>
          </div>

          <form
            className="border-t border-line bg-[#0b1016] p-4"
            onSubmit={(event) => {
              event.preventDefault();
              runQuery();
            }}
          >
            <div className="mx-auto flex max-w-5xl gap-3">
              <input
                className="min-h-12 flex-1 rounded border border-line bg-[#111b24] px-4 text-ink outline-none focus:border-gene"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ask any question about mitochondria..."
                value={query}
              />
              <button
                className="grid h-12 w-12 place-items-center rounded bg-gene text-[#071019] hover:bg-[#79bdff]"
                title="Ask"
                type="submit"
              >
                <ArrowUp size={20} />
              </button>
            </div>
          </form>
        </div>

        <aside className="border-l border-line bg-[#0e151c]">
          <AgentTracePanel trace={AGENT_TRACE} />
          <section className="space-y-4 border-t border-line p-5">
            <h2 className="font-semibold">Citation audit</h2>
            <div className="grid gap-3 text-sm text-muted">
              <div className="rounded border border-line bg-[#111c25] p-3">5 PMIDs validated</div>
              <div className="rounded border border-line bg-[#111c25] p-3">0 fabricated citations</div>
              <div className="rounded border border-line bg-[#111c25] p-3">Confidence 0.86</div>
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}

function responseFor(query: string): string {
  if (query.toLowerCase().includes("drug")) {
    return "Idebenone bypasses impaired Complex I electron transfer and is approved in Europe for LHON [PMID:26988832]. Urolithin A targets mitophagy and mitochondrial quality control, while MitoQ targets matrix-proximal oxidative stress [doi:10.1038/s41591-022-01892-8].";
  }
  return SAMPLE_ANSWER;
}
