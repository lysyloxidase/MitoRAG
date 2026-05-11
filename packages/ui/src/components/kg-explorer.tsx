"use client";

import dynamic from "next/dynamic";
import { Filter, LocateFixed, Search } from "lucide-react";
import { type ComponentType, useEffect, useMemo, useRef, useState } from "react";
import type {
  ForceGraph3DProps,
  ForceGraphLink,
  ForceGraphMethods,
  ForceGraphNode
} from "react-force-graph-3d";

import { buildGraphData, MOLECULAR_LEVELS, NODE_COLORS } from "@/lib/mock-data";
import type { GraphLink, GraphNode } from "@/lib/types";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
  loading: () => <div className="grid h-full place-items-center text-muted">Loading 3D graph...</div>
}) as ComponentType<ForceGraph3DProps>;

const categories = [
  "all",
  "OXPHOS",
  "Metabolism",
  "Dynamics",
  "Import",
  "Apoptosis",
  "Disease",
  "Signaling",
  "Therapeutics"
];

export function KGExplorer() {
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [level, setLevel] = useState<number | "all">("all");
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [controversy, setControversy] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphLink | null>(null);
  const [size, setSize] = useState({ width: 960, height: 680 });

  useEffect(() => {
    const element = wrapperRef.current;
    if (!element) return;
    const resize = () =>
      setSize({
        width: Math.max(360, element.clientWidth),
        height: Math.max(520, element.clientHeight)
      });
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const graphData = useMemo(() => {
    const raw = buildGraphData(level);
    const nodes =
      category === "all" ? raw.nodes : raw.nodes.filter((node) => node.category === category);
    const visible = new Set(nodes.map((node) => node.id));
    return {
      nodes,
      links: raw.links.filter((link) => visible.has(link.source) && visible.has(link.target))
    };
  }, [category, level]);

  const highlighted = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return new Set<string>();
    return new Set(
      graphData.nodes
        .filter((node) => node.name.toLowerCase().includes(term) || node.id.includes(term))
        .map((node) => node.id)
    );
  }, [graphData.nodes, search]);

  function centerSearchResult() {
    const term = search.trim().toLowerCase();
    const match = graphData.nodes.find(
      (node) => node.name.toLowerCase().includes(term) || node.id.includes(term)
    );
    if (!match) return;
    setSelectedNode(match);
    graphRef.current?.cameraPosition({ x: 0, y: 0, z: 180 }, match, 900);
  }

  return (
    <main className="grid min-h-[calc(100vh-3.5rem)] grid-rows-[auto_1fr]">
      <section className="border-b border-line bg-[#0e151c] px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex min-w-64 flex-1 items-center gap-2 rounded border border-line bg-[#111b24] px-3 py-2">
            <Search size={16} />
            <input
              className="w-full bg-transparent text-sm outline-none"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search gene, protein, disease, drug..."
              value={search}
            />
          </label>
          <button
            className="grid h-10 w-10 place-items-center rounded border border-line bg-[#111b24] hover:border-gene"
            onClick={centerSearchResult}
            title="Center search result"
            type="button"
          >
            <LocateFixed size={16} />
          </button>
          <label className="flex items-center gap-2 rounded border border-line bg-[#111b24] px-3 py-2 text-sm">
            <Filter size={16} />
            <select
              className="bg-transparent outline-none"
              onChange={(event) => setCategory(event.target.value)}
              value={category}
            >
              {categories.map((item) => (
                <option className="bg-[#111b24]" key={item} value={item}>
                  {item === "all" ? "All categories" : item}
                </option>
              ))}
            </select>
          </label>
          <select
            className="h-10 rounded border border-line bg-[#111b24] px-3 text-sm outline-none"
            onChange={(event) =>
              setLevel(event.target.value === "all" ? "all" : Number(event.target.value))
            }
            value={level}
          >
            <option value="all">All molecular levels</option>
            {MOLECULAR_LEVELS.map((item) => (
              <option key={item.id} value={item.id}>
                L{item.id} - {item.name}
              </option>
            ))}
          </select>
          <button
            className={`h-10 rounded border px-3 text-sm ${
              controversy
                ? "border-[#ff4242] bg-[#3a1518] text-[#ffb3b8]"
                : "border-line bg-[#111b24] text-muted"
            }`}
            onClick={() => setControversy((value) => !value)}
            type="button"
          >
            Controversy view
          </button>
          <div className="ml-auto text-sm text-muted">
            {graphData.nodes.length} nodes / {graphData.links.length} edges
          </div>
        </div>
      </section>

      <section className="grid min-h-0 grid-cols-1 xl:grid-cols-[1fr_360px]">
        <div className="kg-canvas min-h-[620px] bg-[#060a0f]" ref={wrapperRef}>
          <ForceGraph3D
            backgroundColor="#060a0f"
            cooldownTicks={120}
            d3AlphaDecay={0.026}
            d3VelocityDecay={0.23}
            graphData={graphData}
            height={size.height}
            linkColor={(link) => edgeColor(link as GraphLink, controversy)}
            linkDirectionalParticleSpeed={0.004}
            linkDirectionalParticles={(link) => ((link as GraphLink).predicate === "electron_flow" ? 4 : 0)}
            linkOpacity={0.64}
            linkWidth={(link) => ((link as GraphLink).contradiction ? 4 : 1.4)}
            nodeColor={(node) => nodeColor(node as GraphNode, highlighted)}
            nodeLabel={(node) => `${(node as GraphNode).type}: ${(node as GraphNode).name}`}
            nodeVal={(node) => (node as GraphNode).val}
            onLinkClick={(link) => {
              setSelectedEdge(normalizeLink(link));
              setSelectedNode(null);
            }}
            onNodeClick={(node) => {
              setSelectedNode(node as GraphNode);
              setSelectedEdge(null);
            }}
            ref={graphRef}
            width={size.width}
          />
        </div>

        <aside className="border-l border-line bg-[#0e151c] p-5">
          <h2 className="mb-4 font-semibold">Inspector</h2>
          {selectedNode ? <NodePanel node={selectedNode} /> : null}
          {selectedEdge ? <EdgePanel edge={selectedEdge} /> : null}
          {!selectedNode && !selectedEdge ? (
            <div className="space-y-4 text-sm text-muted">
              <p>Click a node to inspect properties or an edge to inspect evidence.</p>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(NODE_COLORS).map(([type, color]) => (
                  <div className="flex items-center gap-2" key={type}>
                    <span className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
                    {type}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </aside>
      </section>
    </main>
  );
}

function NodePanel({ node }: { node: GraphNode }) {
  return (
    <div className="space-y-4">
      <div>
        <div className="text-sm text-muted">{node.type}</div>
        <h3 className="text-xl font-semibold">{node.name}</h3>
      </div>
      <dl className="space-y-2 text-sm">
        {Object.entries(node.properties).map(([key, value]) => (
          <div className="flex justify-between gap-4 border-b border-line py-2" key={key}>
            <dt className="text-muted">{key}</dt>
            <dd>{String(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function EdgePanel({ edge }: { edge: GraphLink }) {
  return (
    <div className="space-y-4">
      <div>
        <div className="text-sm text-muted">Edge</div>
        <h3 className="text-xl font-semibold">{edge.predicate}</h3>
      </div>
      <p className="text-sm text-muted">
        {edge.source} to {edge.target}
      </p>
      <div className="rounded border border-line bg-[#111c25] p-3 text-sm">
        {edge.evidence ?? "Seeded KG relation with no paper-derived evidence yet."}
      </div>
    </div>
  );
}

function nodeColor(node: GraphNode, highlighted: Set<string>): string {
  if (highlighted.has(node.id)) return "#ffffff";
  return node.color;
}

function edgeColor(edge: GraphLink, controversy: boolean): string {
  if (edge.contradiction || controversy) return "#ff4242";
  if (edge.predicate === "electron_flow") return "#f9d65c";
  return "rgba(148, 163, 184, 0.78)";
}

function normalizeLink(link: ForceGraphLink): GraphLink {
  return {
    source: endpointId(link.source),
    target: endpointId(link.target),
    predicate: typeof link.predicate === "string" ? link.predicate : "related_to",
    evidence: typeof link.evidence === "string" ? link.evidence : undefined,
    confidence: typeof link.confidence === "number" ? link.confidence : undefined,
    contradiction: Boolean(link.contradiction)
  };
}

function endpointId(value: ForceGraphLink["source"]): string {
  if (typeof value === "string" || typeof value === "number") return String(value);
  return String((value as ForceGraphNode | undefined)?.id ?? "unknown");
}
