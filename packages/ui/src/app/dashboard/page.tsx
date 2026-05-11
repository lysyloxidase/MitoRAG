import { Activity, Database, FileText, Network, Timer } from "lucide-react";
import type { ReactNode } from "react";

import { AGENT_TRACE, DASHBOARD_STATS, INGESTION_LOG, RECENT_QUERIES } from "@/lib/mock-data";

export default function DashboardPage() {
  return (
    <main className="min-h-[calc(100vh-3.5rem)] p-5">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Operations dashboard</h1>
          <p className="mt-1 text-sm text-muted">KG growth, agent performance, and ingestion health.</p>
        </div>
        <div className="rounded border border-line bg-[#111b24] px-3 py-2 text-sm text-muted">
          Production target: 30-120s query latency
        </div>
      </div>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Stat icon={<Database size={18} />} label="KG nodes" value={DASHBOARD_STATS.nodes} />
        <Stat icon={<Network size={18} />} label="KG edges" value={DASHBOARD_STATS.edges} />
        <Stat icon={<FileText size={18} />} label="papers" value={DASHBOARD_STATS.papers} />
        <Stat icon={<Activity size={18} />} label="auto triples" value={DASHBOARD_STATS.triples} />
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded border border-line bg-[#111b24] p-5">
          <h2 className="mb-4 font-semibold">Agent latency</h2>
          <div className="space-y-3">
            {AGENT_TRACE.map((item) => (
              <div key={item.agent}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{item.agent}</span>
                  <span className="text-muted">{item.latencyMs} ms</span>
                </div>
                <div className="h-2 rounded bg-[#1d2b36]">
                  <div
                    className="h-2 rounded bg-gene"
                    style={{ width: `${Math.min(100, item.latencyMs / 80)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded border border-line bg-[#111b24] p-5">
          <h2 className="mb-4 font-semibold">Performance targets</h2>
          <div className="grid gap-3">
            <Target label="Hybrid retrieval" value={`${DASHBOARD_STATS.retrievalMs} ms`} target="<2s" />
            <Target label="Internet fan-out" value={`${DASHBOARD_STATS.webSearchMs} ms`} target="<5s" />
            <Target label="Full answer" value={`${DASHBOARD_STATS.querySeconds}s`} target="30-120s" />
            <Target label="PDF ingestion" value={`${DASHBOARD_STATS.ingestionSeconds}s`} target="<30s" />
          </div>
        </div>
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-2">
        <div className="rounded border border-line bg-[#111b24] p-5">
          <h2 className="mb-4 font-semibold">Recent queries</h2>
          <div className="space-y-2">
            {RECENT_QUERIES.map((query) => (
              <div className="rounded border border-line bg-[#0e151c] p-3 text-sm" key={query}>
                {query}
              </div>
            ))}
          </div>
        </div>
        <div className="rounded border border-line bg-[#111b24] p-5">
          <h2 className="mb-4 font-semibold">Ingestion log</h2>
          <div className="space-y-2">
            {INGESTION_LOG.map((item) => (
              <div className="flex gap-2 rounded border border-line bg-[#0e151c] p-3 text-sm" key={item}>
                <Timer className="mt-0.5 text-muted" size={14} />
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function Stat({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return (
    <div className="rounded border border-line bg-[#111b24] p-5">
      <div className="mb-3 text-muted">{icon}</div>
      <div className="text-3xl font-semibold">{value.toLocaleString()}</div>
      <div className="text-sm text-muted">{label}</div>
    </div>
  );
}

function Target({ label, value, target }: { label: string; value: string; target: string }) {
  return (
    <div className="flex items-center justify-between rounded border border-line bg-[#0e151c] p-3">
      <span>{label}</span>
      <span className="text-sm text-muted">
        {value} / {target}
      </span>
    </div>
  );
}
