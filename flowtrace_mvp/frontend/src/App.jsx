import { useCallback, useMemo, useState } from "react";
import { Background, Controls, MarkerType, MiniMap, ReactFlow } from "@xyflow/react";
import dagre from "dagre";
import "@xyflow/react/dist/style.css";

import CodeNode from "./components/CodeNode.jsx";
import FlowEdge from "./components/FlowEdge.jsx";
import GroupNode from "./components/GroupNode.jsx";
import InspectorPanel from "./components/InspectorPanel.jsx";

const API_URL = "http://localhost:8000/api/graph";
const NODE_TYPES = { codeNode: CodeNode, groupNode: GroupNode };
const EDGE_TYPES = { flowEdge: FlowEdge };
const SAMPLE_CODE = `segments = [{"start": "00:00", "text": "Today I built a tool but it failed first."}, {"start": "00:12", "text": "Then I found the bug in the data flow."}, {"start": "00:30", "text": "This can help debug AI generated code faster."}]
clips = []
for segment in segments:
    text = segment["text"].lower()
    if "bug" in text or "failed" in text:
        score = 3
    elif "ai" in text or "debug" in text:
        score = 2
    else:
        score = 1
    if score >= 2:
        clips.append({"start": segment["start"], "score": score})
print(clips)
`;

function errorText(errorValue) {
  if (!errorValue) return null;
  if (typeof errorValue === "string") return errorValue;
  return [errorValue.type, errorValue.message].filter(Boolean).join(": ") || JSON.stringify(errorValue);
}

function findGraphEdgeById(graphModel, edgeId) {
  return graphModel?.edges?.find((edge) => edge.id === edgeId) ?? null;
}

function layoutWithDagre(nodes, edges) {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "TB", nodesep: 48, ranksep: 72 });
  nodes.forEach((node) => graph.setNode(node.id, { width: node.type === "groupNode" ? 300 : 280, height: 110 }));
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  dagre.layout(graph);
  return nodes.map((node) => {
    const { x, y } = graph.node(node.id) ?? { x: 0, y: 0 };
    return { ...node, position: { x: x - 140, y: y - 55 } };
  });
}

function buildReactFlowElements(graphModel, selectedEdge, expandedGroups, onEdgeClick, onToggleGroup) {
  if (!graphModel) return { nodes: [], edges: [] };
  const groupNodes = (graphModel.groups ?? []).map((group) => ({
    id: group.id,
    type: "groupNode",
    data: { ...group, isExpanded: expandedGroups.has(group.id), onToggle: onToggleGroup },
    position: { x: 0, y: 0 },
  }));
  const codeNodes = (graphModel.nodes ?? []).map((node) => ({
    id: node.id,
    type: "codeNode",
    data: node,
    position: { x: 0, y: 0 },
  }));
  const nodes = layoutWithDagre([...groupNodes, ...codeNodes], graphModel.edges ?? []);
  const edges = (graphModel.edges ?? []).map((edge) => ({
    id: edge.id,
    type: "flowEdge",
    source: edge.source,
    target: edge.target,
    markerEnd: { type: MarkerType.ArrowClosed },
    data: { ...edge, isHighlighted: selectedEdge?.id === edge.id, onEdgeClick },
  }));
  return { nodes, edges };
}

export default function App() {
  const [code, setCode] = useState(SAMPLE_CODE);
  const [graphModel, setGraphModel] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [expandedGroups, setExpandedGroups] = useState(() => new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stdout, setStdout] = useState("");

  const toggleGroup = useCallback((groupId) => {
    setExpandedGroups((current) => {
      const next = new Set(current);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  }, []);

  const handleEdgeClick = useCallback(
    (edgeId) => setSelectedEdge(findGraphEdgeById(graphModel, edgeId)),
    [graphModel],
  );

  const { nodes: rfNodes, edges: rfEdges } = useMemo(
    () => buildReactFlowElements(graphModel, selectedEdge, expandedGroups, handleEdgeClick, toggleGroup),
    [graphModel, selectedEdge, expandedGroups, handleEdgeClick, toggleGroup],
  );

  async function runTrace() {
    setLoading(true);
    setError(null);
    setSelectedEdge(null);
    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      const payload = await response.json();
      setGraphModel(payload.graph ?? null);
      setStdout(payload.stdout ?? "");
      setError(errorText(payload.error));
    } catch {
      setError("Backend not reachable. Start FastAPI on http://localhost:8000");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="top-bar">
        <h1>FlowTrace</h1>
        <button type="button" onClick={runTrace} disabled={loading}>
          Run Trace
        </button>
        {loading ? <span className="top-bar__status">Running trace...</span> : null}
      </header>
      <main className="workspace">
        <aside className="code-panel">
          <textarea value={code} onChange={(event) => setCode(event.target.value)} spellCheck="false" />
        </aside>
        <section className="graph-panel">
          {error ? <div className="app-message app-message--error">{error}</div> : null}
          {stdout ? <pre className="stdout-panel">{stdout}</pre> : null}
          {graphModel && rfNodes.length === 0 ? <div className="app-message">No graph nodes returned.</div> : null}
          {graphModel ? (
            <ReactFlow nodes={rfNodes} edges={rfEdges} nodeTypes={NODE_TYPES} edgeTypes={EDGE_TYPES} fitView>
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          ) : (
            <div className="empty-state">Paste or edit code, then run a trace.</div>
          )}
        </section>
        <InspectorPanel edge={selectedEdge} onClose={() => setSelectedEdge(null)} />
      </main>
    </div>
  );
}
