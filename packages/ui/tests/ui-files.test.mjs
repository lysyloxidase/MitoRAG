import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = new URL("..", import.meta.url).pathname;

function read(path) {
  return readFileSync(join(root, path), "utf8");
}

test("chat renders clickable citation markers and agent trace", () => {
  const chat = read("src/components/chat-interface.tsx");
  const citations = read("src/components/citation-link.tsx");
  assert.match(chat, /AgentTracePanel/);
  assert.match(chat, /ContradictionBadge/);
  assert.match(citations, /pubmed\.ncbi\.nlm\.nih\.gov/);
});

test("KG explorer uses 3D force graph and molecular levels", () => {
  const kg = read("src/components/kg-explorer.tsx");
  const data = read("src/lib/mock-data.ts");
  assert.match(kg, /react-force-graph-3d/);
  assert.match(data, /OXPHOS \/ ETC/);
  assert.match(data, /mPTP = ATP synthase/);
});

test("paper library includes drag-and-drop upload flow", () => {
  const papers = read("src/components/paper-library.tsx");
  assert.match(papers, /onDrop/);
  assert.match(papers, /\/ingest\/upload/);
});
