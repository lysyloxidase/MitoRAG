"use client";

import { CheckCircle2, FileUp, Loader2, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { PaperRecord } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

interface UploadState {
  filename: string;
  status: "queued" | "uploading" | "indexed" | "error";
  chunks: number;
  paperId?: string;
  title?: string;
  error?: string;
}

interface ApiPaper {
  filename: string;
  size_bytes: number;
  status?: string;
}

export function PaperLibrary() {
  const [papers, setPapers] = useState<PaperRecord[]>([]);
  const [query, setQuery] = useState("");
  const [dropState, setDropState] = useState<"idle" | "ready" | "uploading">("idle");
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [loadingList, setLoadingList] = useState(true);

  async function refreshPapers() {
    try {
      const res = await fetch(`${API_BASE}/ingest/papers`);
      if (!res.ok) return;
      const data: ApiPaper[] = await res.json();
      const records: PaperRecord[] = data.map((p) => ({
        id: `local:${p.filename}`,
        title: p.filename.replace(/\.pdf$/i, "").replace(/[._-]+/g, " "),
        journal: "Local PDF library",
        year: new Date().getFullYear(),
        status: p.status === "available" ? "indexed" : "needs-review",
        chunks: Math.max(8, Math.round(p.size_bytes / 8000)),
        entities: ["mitochondria"],
        triples: 0,
      }));
      setPapers(records);
    } finally {
      setLoadingList(false);
    }
  }

  useEffect(() => {
    void refreshPapers();
  }, []);

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return papers;
    return papers.filter(
      (paper) =>
        paper.title.toLowerCase().includes(term) ||
        paper.id.toLowerCase().includes(term)
    );
  }, [papers, query]);

  async function ingestFiles(files: FileList | File[]) {
    const list = Array.from(files).filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    if (list.length === 0) return;

    setDropState("uploading");
    const startingUploads: UploadState[] = list.map((f) => ({
      filename: f.name,
      status: "queued",
      chunks: 0,
    }));
    setUploads((prev) => [...startingUploads, ...prev]);

    for (const file of list) {
      setUploads((prev) =>
        prev.map((u) => (u.filename === file.name ? { ...u, status: "uploading" } : u))
      );
      try {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch(`${API_BASE}/ingest/upload`, {
          method: "POST",
          body: formData,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const result = await res.json();
        setUploads((prev) =>
          prev.map((u) =>
            u.filename === file.name
              ? {
                  ...u,
                  status: "indexed",
                  chunks: result.chunk_count ?? 0,
                  paperId: result.paper_id,
                  title: result.title,
                }
              : u
          )
        );
      } catch (err: unknown) {
        setUploads((prev) =>
          prev.map((u) =>
            u.filename === file.name
              ? { ...u, status: "error", error: (err as Error)?.message ?? "upload failed" }
              : u
          )
        );
      }
    }

    setDropState("idle");
    void refreshPapers();
  }

  const indexedCount = papers.length;
  const inProgress = uploads.filter((u) => u.status === "uploading" || u.status === "queued").length;

  return (
    <main className="grid min-h-[calc(100vh-3.5rem)] grid-cols-1 lg:grid-cols-[360px_1fr]">
      <aside className="border-r border-line bg-[#0e151c] p-5">
        <h1 className="text-2xl font-semibold">Paper library</h1>
        <p className="mt-2 text-sm text-muted">
          Drop unlimited PDFs to ingest into the RAG corpus. More papers = better grounding,
          less hallucination.
        </p>

        <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
          <div className="rounded border border-line bg-[#111b24] p-3">
            <div className="text-2xl font-semibold text-ink">{indexedCount}</div>
            <div className="text-xs text-muted">Indexed PDFs</div>
          </div>
          <div className="rounded border border-line bg-[#111b24] p-3">
            <div className="text-2xl font-semibold text-ink">
              {inProgress > 0 ? inProgress : "—"}
            </div>
            <div className="text-xs text-muted">In progress</div>
          </div>
        </div>

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
              {dropState === "uploading" ? "Ingesting PDFs…" : "Drop PDFs here"}
            </div>
            <p className="mt-1 text-xs text-muted">Multiple files supported · 100+ at a time</p>
            <label className="mt-3 inline-block cursor-pointer rounded bg-gene px-3 py-2 text-sm text-[#071019]">
              Choose files
              <input
                accept="application/pdf"
                className="hidden"
                multiple
                onChange={(event) => {
                  if (event.target.files) void ingestFiles(event.target.files);
                }}
                type="file"
              />
            </label>
          </div>
        </div>

        {uploads.length > 0 && (
          <div className="scrollbar-thin mt-4 max-h-56 overflow-y-auto rounded border border-line bg-[#0b1219] p-2">
            <div className="mb-1 px-1 text-xs font-medium uppercase tracking-wide text-muted">
              Recent uploads
            </div>
            {uploads.slice(0, 25).map((u) => (
              <div
                key={u.filename}
                className="flex items-center gap-2 rounded px-2 py-1.5 text-xs"
              >
                {u.status === "uploading" || u.status === "queued" ? (
                  <Loader2 className="animate-spin text-muted" size={12} />
                ) : u.status === "indexed" ? (
                  <CheckCircle2 className="text-gene" size={12} />
                ) : (
                  <span className="text-red-400">!</span>
                )}
                <span className="flex-1 truncate text-ink">{u.filename}</span>
                {u.status === "indexed" && (
                  <span className="text-muted">{u.chunks} chunks</span>
                )}
                {u.status === "error" && (
                  <span className="text-red-400" title={u.error}>
                    error
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        <details className="mt-4 rounded border border-line bg-[#0b1219] p-3 text-xs">
          <summary className="cursor-pointer text-sm font-medium text-ink hover:text-gene">
            Bulk import via terminal
          </summary>
          <div className="mt-2 space-y-2 text-muted">
            <p>Drop hundreds of PDFs into the watched folder:</p>
            <pre className="overflow-x-auto rounded bg-[#0f1922] p-2 text-[11px] text-gene">
{`cp /path/to/*.pdf data/papers/`}
            </pre>
            <p>Or fetch ~100 open-access mitochondrial papers automatically:</p>
            <pre className="overflow-x-auto rounded bg-[#0f1922] p-2 text-[11px] text-gene">
{`./scripts/fetch_mito_papers.sh 100`}
            </pre>
          </div>
        </details>
      </aside>

      <section className="scrollbar-thin overflow-y-auto p-5">
        {loadingList ? (
          <div className="grid h-40 place-items-center text-muted">
            <Loader2 className="animate-spin" size={24} />
          </div>
        ) : visible.length === 0 ? (
          <div className="grid h-40 place-items-center rounded border border-dashed border-line text-center text-muted">
            <div>
              <p className="font-medium text-ink">No papers ingested yet</p>
              <p className="mt-2 text-sm">
                Drop PDFs on the left, copy them into <code>data/papers/</code>, or run{" "}
                <code>./scripts/fetch_mito_papers.sh</code>.
              </p>
            </div>
          </div>
        ) : (
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
              </article>
            ))}
          </div>
        )}
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
