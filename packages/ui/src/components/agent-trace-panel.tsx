"use client";

import { Activity, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

import type { AgentTraceItem } from "@/lib/types";

export function AgentTracePanel({ trace }: { trace: AgentTraceItem[] }) {
  const [open, setOpen] = useState(true);
  const total = trace.reduce((sum, item) => sum + item.latencyMs, 0);

  return (
    <section className="border-t border-line bg-[#0e151c]">
      <button
        className="flex w-full items-center justify-between px-5 py-3 text-left text-sm text-ink"
        onClick={() => setOpen((value) => !value)}
        type="button"
      >
        <span className="flex items-center gap-2">
          <Activity size={16} />
          Agent trace
          <span className="text-muted">{trace.length} agents, {(total / 1000).toFixed(1)}s</span>
        </span>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      {open ? (
        <div className="grid gap-2 px-5 pb-5 md:grid-cols-2 xl:grid-cols-3">
          {trace.map((item) => (
            <div
              className="rounded border border-line bg-[#111c25] p-3"
              key={item.agent}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium">{item.agent}</span>
                <span className="rounded bg-[#1d2b36] px-2 py-1 text-xs text-muted">
                  {item.latencyMs} ms
                </span>
              </div>
              <p className="mt-2 text-sm text-muted">{item.role}</p>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
