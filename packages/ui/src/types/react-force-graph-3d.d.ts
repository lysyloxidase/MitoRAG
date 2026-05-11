declare module "react-force-graph-3d" {
  import type { ComponentType, MutableRefObject } from "react";

  export type ForceGraphNode = {
    id?: string | number;
    name?: string;
    color?: string;
    val?: number;
    x?: number;
    y?: number;
    z?: number;
    [key: string]: unknown;
  };

  export type ForceGraphLink = {
    source?: string | number | ForceGraphNode;
    target?: string | number | ForceGraphNode;
    color?: string;
    [key: string]: unknown;
  };

  export type ForceGraphMethods = {
    cameraPosition: (
      position: { x?: number; y?: number; z?: number },
      lookAt?: ForceGraphNode,
      transitionMs?: number
    ) => void;
    zoomToFit: (transitionMs?: number, padding?: number) => void;
  };

  export type ForceGraph3DProps = {
    ref?: MutableRefObject<ForceGraphMethods | undefined>;
    graphData: { nodes: ForceGraphNode[]; links: ForceGraphLink[] };
    width?: number;
    height?: number;
    backgroundColor?: string;
    nodeColor?: (node: ForceGraphNode) => string;
    nodeLabel?: (node: ForceGraphNode) => string;
    nodeVal?: (node: ForceGraphNode) => number;
    linkColor?: (link: ForceGraphLink) => string;
    linkOpacity?: number;
    linkWidth?: (link: ForceGraphLink) => number;
    linkDirectionalParticles?: (link: ForceGraphLink) => number;
    linkDirectionalParticleSpeed?: number;
    onNodeClick?: (node: ForceGraphNode) => void;
    onLinkClick?: (link: ForceGraphLink) => void;
    cooldownTicks?: number;
    d3AlphaDecay?: number;
    d3VelocityDecay?: number;
  };

  const ForceGraph3D: ComponentType<ForceGraph3DProps>;
  export default ForceGraph3D;
}
