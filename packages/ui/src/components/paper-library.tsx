"use client";

import { FileUp, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { PAPERS } from "@/lib/mock-data";
import type { PaperRecord } from "@/lib/types";

export function PaperLibrary() {
  const [papers, setPapers] = useState(PAPERS);
  const [query, setQuery] = useState("");
  const [dropState, setDropState] = useState<"idle" | "ready" | "uploading">("idle");

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return papers;
    return papers.filter(
      (paper) =>
        paper.title.toLowerCase().includes(term) ||
        paper.entities.some((entity) => entity.toLowerCase().includes(term))
    );
  }, [papers, query]);

  async function ingestFiles(files: FileList | File[]) {
    const first = Array.from(files)[0];
    if (!first) return;
    setDropState("uploading");
    const nextPaper: PaperRecord = {
      id: `local:${first.name}`,
      title: first.name.replace(/\.pdf$/i, ""),
      journal: "Local library",
      year: new Date().getFullYear(),
      status: "processing",
      chunks: 0,
      entities: ["pending"],
      triples: 0
    };
    setPapers((items) => [nextPaper, ...items]);

    const apiBase = process.env.NEXT_PUBLIC_API_BASE;
    if (apiBase) {
      const formData = new FormData();
      formData.append("file", first);
      await fetch(`${apiBase}/ingest/upload`, { method: "POST", body: formData }).catch(() => null);
    }

    window.setTimeout(() => {
      setPapers((items) =>
        items.map((item) =>
          item.id === nextPaper.id
            ? {
                ...item,
                status: "indexed",
                chunks: 38,
                entities: ["Complex I", "PINK1", "Parkin"],
                triples: 9
              }
            : item
        )
      );
      setDropState("idle");
    }, 900);
  }

  return (
    <main className="grid min-h-[calc(100vh-3.5rem)] grid-cols-1 lg:grid-cols-[340px_1fr]">
      <aside className="border-r border-line bg-[#0e151c] p-5">
        <h1 className="text-2xl font-semibold">Paper library</h1>
        <p className="mt-2 text-sm text-muted">Local PDFs, extracted entities, and Auto-KG status.</p>

        <label className="mt-5 flex items-center gap-2 rounded border border-line bg-[#111b24] px-3 py-2">
          <Search size={16} />
          <input
            className="w-full bg-transparent text-sm outline-none"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search local corpus"
            value={query}
          />
        </label>

        <div
          className={`mt-5 grid min-h-44 place-items-center rounded border border-dashed p-4 text-center ${
            dropState === "ready" ? "border-gene bg-[#10202c]" : "border-line bg-[#111b24]"
          }`}
          onDragLeave={() => setDropState("idle")}
          onDragOver={(event) => {
            event.preventDefault();
            setDropState("ready");
          }}
          onDrop={(event) => {
            event.preventDefault();
            void ingestFiles(event.dataTransfer.files);
          }}
        >
          <div>
            <FileUp className="mx-auto mb-3" size={28} />
            <div className="font-medium">
              {dropState === "uploading" ? "Ingesting PDF..." : "Drop PDFs here"}
            </div>
            <label className="mt-3 inline-block cursor-pointer rounded bg-gene px-3 py-2 text-sm text-[#071019]">
              Choose file
              <input
                accept="application/pdf"
                className="hidden"
                onChange={(event) => {
                  if (event.target.files) void ingestFiles(event.target.files);
                }}
                type="file"
              />
            </label>
          </div>
        </div>
      </aside>

      <section className="scrollbar-thin overflow-y-auto p-5">
        <div className="grid gap-3">
          {visible.map((paper) => (
            <article className="rounded border border-line bg-[#111b24] p-4" key={paper.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-sm text-muted">
                    {paper.id} · {paper.journal} · {paper.year}
                  </div>
                  <h2 className="mt-1 text-lg font-semibold">{paper.title}</h2>
                </div>
                <span className="rounded bg-[#1d2b36] px-3 py-1 text-sm">{paper.status}</span>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <Metric label="chunks" value={paper.chunks} />
                <Metric label="triples" value={paper.triples} />
                <Metric label="entities" value={paper.entities.length} />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {paper.entities.map((entity) => (
                  <span className="rounded border border-line px-2 py-1 text-sm text-muted" key={entity}>
                    {entity}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-line bg-[#0e151c] p-3">
      <div className="text-xl font-semibold">{value}</div>
      <div className="text-sm text-muted">{label}</div>
    </div>
  );
}
