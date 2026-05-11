export type NodeType =
  | "Gene"
  | "Protein"
  | "Complex"
  | "Pathway"
  | "Disease"
  | "Drug"
  | "Metabolite"
  | "Compartment"
  | "Variant"
  | "Hypothesis";

export type GraphNode = {
  id: string;
  name: string;
  type: NodeType;
  level: number;
  category: string;
  properties: Record<string, string | number | boolean>;
  color: string;
  val: number;
};

export type GraphLink = {
  source: string;
  target: string;
  predicate: string;
  evidence?: string;
  confidence?: number;
  contradiction?: boolean;
};

export type GraphData = {
  nodes: GraphNode[];
  links: GraphLink[];
};

export type AgentTraceItem = {
  agent: string;
  role: string;
  latencyMs: number;
  status: "complete" | "skipped" | "retry";
};

export type Citation = {
  marker: string;
  href: string;
  label: string;
};

export type PaperRecord = {
  id: string;
  title: string;
  journal: string;
  year: number;
  status: "indexed" | "processing" | "needs-review";
  chunks: number;
  entities: string[];
  triples: number;
};
