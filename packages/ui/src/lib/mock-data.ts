import type { AgentTraceItem, GraphData, GraphLink, GraphNode, NodeType, PaperRecord } from "./types";

export const NODE_COLORS: Record<NodeType, string> = {
  Gene: "#47a3ff",
  Protein: "#56d364",
  Complex: "#ff9f1c",
  Pathway: "#a78bfa",
  Disease: "#ff5d73",
  Drug: "#4dd6d6",
  Metabolite: "#f9d65c",
  Compartment: "#94a3b8",
  Variant: "#ff7ab6",
  Hypothesis: "#ff4242"
};

export const MOLECULAR_LEVELS = [
  { id: 1, name: "Whole Mitochondrion", category: "Compartment" },
  { id: 2, name: "OXPHOS / ETC", category: "OXPHOS" },
  { id: 3, name: "TCA Cycle", category: "Metabolism" },
  { id: 4, name: "Fatty Acid Beta-Oxidation", category: "Metabolism" },
  { id: 5, name: "Dynamics", category: "Dynamics" },
  { id: 6, name: "Import", category: "Import" },
  { id: 7, name: "Apoptosis", category: "Apoptosis" },
  { id: 8, name: "Diseases", category: "Disease" },
  { id: 9, name: "Signaling", category: "Signaling" },
  { id: 10, name: "Therapeutics", category: "Therapeutics" }
];

export const SUGGESTED_QUESTIONS = [
  "How many subunits does Complex I have?",
  "What causes MELAS syndrome?",
  "How does PINK1/Parkin mitophagy work?",
  "Which drugs target Complex I or mitophagy?",
  "What is disputed about the mPTP?"
];

export const AGENT_TRACE: AgentTraceItem[] = [
  { agent: "router", role: "Classified mechanistic disease query", latencyMs: 84, status: "complete" },
  { agent: "planner", role: "Split into KG, local, and internet sub-queries", latencyMs: 921, status: "complete" },
  { agent: "local_rag", role: "Retrieved local paper chunks", latencyMs: 241, status: "complete" },
  { agent: "web_rag", role: "Searched PubMed, S2, Europe PMC, bioRxiv", latencyMs: 3310, status: "complete" },
  { agent: "kg_cypher", role: "Queried Neo4j pathway context", latencyMs: 118, status: "complete" },
  { agent: "entity_linker", role: "Normalized genes, drugs, diseases, variants", latencyMs: 93, status: "complete" },
  { agent: "reranker", role: "RRF fusion plus BGE rerank", latencyMs: 451, status: "complete" },
  { agent: "mitophysiology", role: "Checked OXPHOS and mitophagy mechanisms", latencyMs: 5880, status: "complete" },
  { agent: "disease_therapeutics", role: "Checked disease and therapy claims", latencyMs: 5240, status: "complete" },
  { agent: "verifier", role: "CoVe claim verification and contradictions", latencyMs: 6140, status: "complete" },
  { agent: "synthesizer", role: "Generated cited answer", latencyMs: 7620, status: "complete" },
  { agent: "citation_auditor", role: "Validated PMID and DOI markers", latencyMs: 420, status: "complete" }
];

export const SAMPLE_ANSWER =
  "Complex I is NADH:ubiquinone oxidoreductase, a 45-subunit inner-membrane complex with seven mtDNA-encoded ND subunits including MT-ND4 [PMID:33174596]. Pathogenic variants such as m.11778G>A in MT-ND4 are linked to LHON, while m.3243A>G in MT-TL1 is a canonical MELAS variant [PMID:25613900]. For mitophagy, PINK1 accumulation recruits Parkin to damaged mitochondria, amplifying ubiquitin signaling and organelle clearance [PMID:20510199]. The molecular identity of the mPTP remains disputed: one model centers ATP synthase dimers [PMID:37336870], while synthase-null evidence supports non-ATP-synthase pore opening [PMID:37607939].";

export const PAPERS: PaperRecord[] = [
  {
    id: "PMID:33174596",
    title: "Respiratory complex I structure and disease context",
    journal: "Nature Reviews Molecular Cell Biology",
    year: 2020,
    status: "indexed",
    chunks: 86,
    entities: ["Complex I", "MT-ND4", "OXPHOS"],
    triples: 18
  },
  {
    id: "PMID:25613900",
    title: "Clinical and molecular features of MELAS",
    journal: "Mitochondrion",
    year: 2015,
    status: "indexed",
    chunks: 42,
    entities: ["MELAS", "m.3243A>G", "MT-TL1"],
    triples: 11
  },
  {
    id: "PMID:37336870",
    title: "ATP synthase models of permeability transition",
    journal: "Cell Death Differentiation",
    year: 2023,
    status: "needs-review",
    chunks: 31,
    entities: ["mPTP", "ATP synthase", "ANT"],
    triples: 7
  }
];

const coreNodes: GraphNode[] = [
  node("matrix", "Matrix", "Compartment", 1, "Compartment", 9),
  node("imm", "Inner membrane", "Compartment", 1, "Compartment", 8),
  node("ims", "Intermembrane space", "Compartment", 1, "Compartment", 7),
  node("omm", "Outer membrane", "Compartment", 1, "Compartment", 7),
  node("complex-i", "Complex I", "Complex", 2, "OXPHOS", 12),
  node("complex-ii", "Complex II", "Complex", 2, "OXPHOS", 9),
  node("complex-iii", "Complex III", "Complex", 2, "OXPHOS", 10),
  node("complex-iv", "Complex IV", "Complex", 2, "OXPHOS", 10),
  node("complex-v", "Complex V", "Complex", 2, "OXPHOS", 10),
  node("coq10", "CoQ10", "Metabolite", 2, "OXPHOS", 7),
  node("cytc", "Cytochrome c", "Protein", 2, "OXPHOS", 7),
  node("mt-nd4", "MT-ND4", "Gene", 8, "Disease", 8),
  node("mt-tl1", "MT-TL1", "Gene", 8, "Disease", 8),
  node("m11778", "m.11778G>A", "Variant", 8, "Disease", 7),
  node("m3243", "m.3243A>G", "Variant", 8, "Disease", 7),
  node("lhon", "LHON", "Disease", 8, "Disease", 8),
  node("melas", "MELAS", "Disease", 8, "Disease", 8),
  node("pink1", "PINK1", "Gene", 5, "Dynamics", 7),
  node("parkin", "Parkin", "Gene", 5, "Dynamics", 7),
  node("mfn1", "MFN1", "Protein", 5, "Dynamics", 6),
  node("mfn2", "MFN2", "Protein", 5, "Dynamics", 6),
  node("opa1", "OPA1", "Protein", 5, "Dynamics", 6),
  node("drp1", "DRP1", "Protein", 5, "Dynamics", 6),
  node("tom", "TOM complex", "Complex", 6, "Import", 8),
  node("tim23", "TIM23", "Complex", 6, "Import", 7),
  node("tim22", "TIM22", "Complex", 6, "Import", 7),
  node("mcu", "MCU complex", "Complex", 6, "Import", 7),
  node("bcl2", "BCL-2", "Protein", 7, "Apoptosis", 7),
  node("bax", "BAX", "Protein", 7, "Apoptosis", 7),
  node("mptp-atp", "mPTP = ATP synthase", "Hypothesis", 7, "Apoptosis", 8),
  node("mptp-ant", "mPTP = ANT", "Hypothesis", 7, "Apoptosis", 8),
  node("idebenone", "Idebenone", "Drug", 10, "Therapeutics", 8),
  node("mitoq", "MitoQ", "Drug", 10, "Therapeutics", 7),
  node("urolithin-a", "Urolithin A", "Drug", 10, "Therapeutics", 7)
];

const coreLinks: GraphLink[] = [
  link("complex-i", "coq10", "electron_flow", "NADH electrons enter CoQ pool"),
  link("coq10", "complex-iii", "electron_flow"),
  link("complex-iii", "cytc", "electron_flow"),
  link("cytc", "complex-iv", "electron_flow"),
  link("complex-i", "ims", "pumps_protons"),
  link("complex-iii", "ims", "pumps_protons"),
  link("complex-iv", "ims", "pumps_protons"),
  link("mt-nd4", "complex-i", "subunit_of", "[PMID:33174596] ND4 is a Complex I subunit"),
  link("m11778", "lhon", "causes"),
  link("m11778", "mt-nd4", "associated_with"),
  link("m3243", "melas", "causes"),
  link("m3243", "mt-tl1", "associated_with"),
  link("pink1", "parkin", "activates", "[PMID:20510199] PINK1 recruits Parkin"),
  link("tom", "tim23", "imports_matrix_proteins"),
  link("tom", "tim22", "imports_carriers"),
  link("bax", "cytc", "releases"),
  link("mptp-atp", "mptp-ant", "contradicts", "[PMID:37336870] vs [PMID:37607939]", true),
  link("idebenone", "complex-i", "bypasses"),
  link("mitoq", "matrix", "targets"),
  link("urolithin-a", "pink1", "modulates")
];

const levelNames = [
  ["OMM", "IMM", "IMS", "Matrix"],
  ["NDUFS", "SDH", "UQCRC", "COX", "ATP5"],
  ["CS", "ACO2", "IDH3", "OGDH", "SUCLG", "SDH", "FH", "MDH2"],
  ["CPT1", "CPT2", "ACADM", "HADH", "ACAA2", "ACAT1"],
  ["MFN", "OPA1", "DRP1", "FIS1", "MFF", "PINK1", "PRKN", "TFAM"],
  ["TOMM", "TIMM", "SAMM", "MIA40", "ERV1", "MCU"],
  ["BCL2", "BAX", "BAK", "APAF1", "CASP9", "ANT", "VDAC"],
  ["MELAS", "LHON", "Leigh", "MERRF", "NARP"],
  ["ATF4", "ATF5", "CHOP", "HIF1A", "NFE2L2", "FGF21", "GDF15"],
  ["Idebenone", "CoQ10", "MitoQ", "Elamipretide", "Urolithin A", "NMN", "NR"]
];

export function buildGraphData(levelFilter: number | "all" = "all"): GraphData {
  const nodes = [...coreNodes];
  const links = [...coreLinks];
  for (let level = 1; level <= 10; level += 1) {
    const names = levelNames[level - 1] ?? ["Node"];
    for (let index = 0; index < 116; index += 1) {
      const type = typeForLevel(level, index);
      const id = `l${level}-${index}`;
      const name = `${names[index % names.length]}-${index + 1}`;
      nodes.push(node(id, name, type, level, MOLECULAR_LEVELS[level - 1].category, 2 + (index % 4)));
      const anchor = anchorForLevel(level);
      links.push(link(anchor, id, predicateForType(type), `Seeded level ${level} relation`));
      if (index > 0) {
        links.push(link(`l${level}-${index - 1}`, id, "near"));
      }
    }
  }

  if (levelFilter === "all") {
    return { nodes, links };
  }

  const levelNodeIds = new Set(
    nodes.filter((item) => item.level === levelFilter).map((item) => item.id)
  );
  const filteredNodes = nodes.filter(
    (item) => item.level === levelFilter || connectedToLevel(item.id, links, levelNodeIds)
  );
  const visible = new Set(filteredNodes.map((item) => item.id));
  return {
    nodes: filteredNodes,
    links: links.filter((item) => visible.has(item.source) && visible.has(item.target))
  };
}

export const DASHBOARD_STATS = {
  nodes: 1538,
  edges: 5284,
  papers: 128,
  triples: 914,
  retrievalMs: 1420,
  webSearchMs: 3810,
  querySeconds: 74,
  ingestionSeconds: 22
};

export const RECENT_QUERIES = [
  "How does Complex I contribute to ROS generation?",
  "What drugs target mitophagy?",
  "Which MELAS variants have heteroplasmy thresholds?",
  "What is disputed about mPTP composition?"
];

export const INGESTION_LOG = [
  "Ingested PMID:33174596: +18 triples, +11 new entities, 0 contradictions",
  "Ingested PMID:37336870: +7 triples, +2 new entities, 1 contradiction detected",
  "Indexed 86 chunks into PubMedBERT + Nomic vector stores",
  "Updated KG level 8 disease subgraph"
];

function node(
  id: string,
  name: string,
  type: NodeType,
  level: number,
  category: string,
  val: number
): GraphNode {
  return {
    id,
    name,
    type,
    level,
    category,
    val,
    color: NODE_COLORS[type],
    properties: {
      level,
      category,
      confidence: 0.82 + ((id.length + name.length) % 12) / 100
    }
  };
}

function link(
  source: string,
  target: string,
  predicate: string,
  evidence?: string,
  contradiction = false
): GraphLink {
  return {
    source,
    target,
    predicate,
    evidence,
    contradiction,
    confidence: contradiction ? 0.95 : 0.82
  };
}

function typeForLevel(level: number, index: number): NodeType {
  const cycle: NodeType[] = ["Gene", "Protein", "Complex", "Pathway", "Metabolite"];
  if (level === 1) return "Compartment";
  if (level === 8) return index % 3 === 0 ? "Disease" : index % 3 === 1 ? "Variant" : "Gene";
  if (level === 10) return index % 2 === 0 ? "Drug" : "Protein";
  return cycle[index % cycle.length];
}

function anchorForLevel(level: number): string {
  const anchors: Record<number, string> = {
    1: "matrix",
    2: "complex-i",
    3: "matrix",
    4: "matrix",
    5: "pink1",
    6: "tom",
    7: "bax",
    8: "melas",
    9: "matrix",
    10: "idebenone"
  };
  return anchors[level] ?? "matrix";
}

function predicateForType(type: NodeType): string {
  if (type === "Drug") return "targets";
  if (type === "Disease" || type === "Variant") return "associated_with";
  if (type === "Metabolite") return "produces";
  return "participates_in";
}

function connectedToLevel(id: string, links: GraphLink[], levelNodeIds: Set<string>): boolean {
  return links.some(
    (item) =>
      (item.source === id && levelNodeIds.has(item.target)) ||
      (item.target === id && levelNodeIds.has(item.source))
  );
}
