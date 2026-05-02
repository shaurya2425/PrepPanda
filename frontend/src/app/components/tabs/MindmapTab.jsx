import { useState, useEffect, useCallback, useMemo } from "react";
import { Sparkles, Loader2, Maximize, PanelRightClose, PanelRightOpen, Image as ImageIcon } from "lucide-react";
import { api } from "@/lib/api";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Handle,
  Position,
  Panel
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";

const getStatusColor = (tag) => {
  const t = (tag || "").toLowerCase();
  if (t === "core_concept") return "#10B981"; // Green
  if (t === "definition") return "#F59E0B"; // Yellow
  if (t === "example" || t === "application") return "#3B82F6"; // Blue
  return "#8B5CF6"; // Purple for detail/other
};

// ─────────────────────────────────────────────────────────────────────────────
// Custom Node Component
// ─────────────────────────────────────────────────────────────────────────────
const CustomNode = ({ data, selected }) => {
  const color = getStatusColor(data.tag);
  
  return (
    <div
      className="relative px-5 py-3 rounded-2xl shadow-sm transition-all duration-200 glass"
      style={{
        border: `2px solid ${color}`,
        background: "var(--bg-secondary)",
        boxShadow: selected ? `0 0 0 4px ${color}33, var(--shadow-md)` : "var(--shadow-sm)",
        transform: selected ? "scale(1.02)" : "scale(1)",
        minWidth: "180px",
        maxWidth: "280px"
      }}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3 border-2" style={{ background: color, borderColor: 'var(--bg-primary)' }} />
      
      {data.tag && data.depth > 0 && (
        <div className="text-[10px] font-bold uppercase tracking-widest mb-1.5 opacity-80 flex justify-between items-center" style={{ color }}>
          <span>{data.tag.replace("_", " ")}</span>
          {data.figureCount > 0 && (
            <span className="flex items-center gap-1 opacity-70">
              <ImageIcon className="w-3 h-3" /> {data.figureCount}
            </span>
          )}
        </div>
      )}
      
      <div className={`text-sm font-semibold leading-snug ${data.depth === 0 ? "text-base font-extrabold" : ""}`} style={{ color: "var(--text-primary)" }}>
        {data.label}
      </div>

      {data.hasChildren && (
        <button
          className="absolute -bottom-3 left-1/2 transform -translate-x-1/2 w-5 h-5 rounded-full flex items-center justify-center text-white font-bold text-xs cursor-pointer hover:scale-110 transition-transform z-10 shadow-sm"
          style={{ background: color, border: '2px solid var(--bg-primary)' }}
          onClick={(e) => {
            e.stopPropagation();
            data.onToggleCollapse(data.id);
          }}
        >
          {data.isCollapsed ? '+' : '−'}
        </button>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 border-2" style={{ background: color, borderColor: 'var(--bg-primary)', opacity: data.isCollapsed ? 0 : 1 }} />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

// ─────────────────────────────────────────────────────────────────────────────
// Dagre Auto-Layout
// ─────────────────────────────────────────────────────────────────────────────
const getLayoutedElements = (nodes, edges, direction = "TB") => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 250;
  const nodeHeight = 80;

  dagreGraph.setGraph({ rankdir: direction, nodesep: 60, ranksep: 100 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    // Shift slightly so the anchor is top-left rather than center
    node.targetPosition = Position.Top;
    node.sourcePosition = Position.Bottom;
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
  });

  return { nodes, edges };
};


export function MindmapTab({ title = "this chapter", chapterId }) {
  const [isGenerated, setIsGenerated] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodeData, setSelectedNodeData] = useState(null);
  const [isSidePanelOpen, setIsSidePanelOpen] = useState(true);

  const [rawNodesData, setRawNodesData] = useState([]);
  const [collapsedNodes, setCollapsedNodes] = useState(new Set());

  useEffect(() => {
    if (rawNodesData.length === 0) return;

    const childrenMap = {};
    rawNodesData.forEach(n => {
      if (n.parent_id !== null && n.parent_id !== undefined) {
        const pid = String(n.parent_id);
        if (!childrenMap[pid]) childrenMap[pid] = [];
        childrenMap[pid].push(String(n.id));
      }
    });

    const visibleNodeIds = new Set();
    const rootNodes = rawNodesData.filter(n => n.parent_id === null || n.parent_id === undefined);
    rootNodes.forEach(n => visibleNodeIds.add(String(n.id)));

    const queue = [...rootNodes.map(n => String(n.id))];
    while (queue.length > 0) {
      const currentId = queue.shift();
      if (!collapsedNodes.has(currentId)) {
        const children = childrenMap[currentId] || [];
        children.forEach(childId => {
          visibleNodeIds.add(childId);
          queue.push(childId);
        });
      }
    }

    const rfNodes = rawNodesData
      .filter(n => visibleNodeIds.has(String(n.id)))
      .map(n => {
        const idStr = String(n.id);
        const hasChildren = (childrenMap[idStr] || []).length > 0;
        return {
          id: idStr,
          type: "custom",
          data: {
            id: idStr,
            label: n.label,
            tag: n.tag,
            depth: n.depth,
            detail: n.detail,
            figureCount: n.figure_ids ? n.figure_ids.length : 0,
            raw: n,
            hasChildren,
            isCollapsed: collapsedNodes.has(idStr),
            onToggleCollapse: (nodeId) => {
              setCollapsedNodes(prev => {
                const next = new Set(prev);
                if (next.has(nodeId)) {
                  next.delete(nodeId);
                } else {
                  next.add(nodeId);
                }
                return next;
              });
            }
          },
          position: { x: 0, y: 0 }
        };
      });

    const rfEdges = [];
    rawNodesData.forEach(n => {
      if (n.parent_id !== null && n.parent_id !== undefined && visibleNodeIds.has(String(n.id)) && visibleNodeIds.has(String(n.parent_id))) {
        rfEdges.push({
          id: `e-${n.parent_id}-${n.id}`,
          source: String(n.parent_id),
          target: String(n.id),
          type: "smoothstep",
          animated: true,
          style: { stroke: getStatusColor(n.tag), strokeWidth: 2, opacity: 0.6 }
        });
      }
    });

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rfNodes, rfEdges, "TB");

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [rawNodesData, collapsedNodes, setNodes, setEdges]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const data = await api.mindmap.getFlat(chapterId);
      if (data && data.nodes) {
        setRawNodesData(data.nodes);
        const allIds = new Set(data.nodes.map(n => String(n.id)));
        setCollapsedNodes(allIds);
        setIsGenerated(true);
      }
    } catch (err) {
      console.error("Mindmap generation failed:", err);
      setError("Failed to generate mindmap. Please ensure the chapter has been fully ingested.");
    } finally {
      setIsGenerating(false);
    }
  };

  const onNodeClick = useCallback((event, node) => {
    setSelectedNodeData(node.data);
    setIsSidePanelOpen(true);
  }, []);

  if (!isGenerated) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6" style={{ background: "var(--bg-primary)" }}>
        <div className="max-w-md w-full p-10 rounded-3xl border text-center glass animate-fade-up" style={{ borderColor: "var(--border)", boxShadow: "var(--shadow-lg)" }}>
          <div className="w-20 h-20 mx-auto rounded-3xl flex items-center justify-center mb-6" style={{ background: "var(--bg-tertiary)", border: "1px solid var(--border)" }}>
            <Sparkles className="w-10 h-10" style={{ color: "var(--accent-primary)" }} />
          </div>
          <h2 className="text-2xl font-bold mb-3" style={{ color: "var(--text-primary)" }}>Visual Mindmap</h2>
          <p className="text-[17px] mb-8 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            Automatically extract an interactive semantic map for <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{title}</span>.
          </p>

          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-sm font-medium">
              {error}
            </div>
          )}

          <button
            onClick={handleGenerate} disabled={isGenerating}
            className="w-full h-14 rounded-2xl text-[17px] font-bold flex items-center justify-center gap-2 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
            style={{ background: "var(--gradient-primary)", color: "#FFFFFF", boxShadow: "var(--shadow-glow)" }}>
            {isGenerating ? <><Loader2 className="w-5 h-5 animate-spin" /> Analyzing Chapter...</> : <><Sparkles className="w-5 h-5" /> Generate Concept Map</>}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full relative flex" style={{ background: "var(--bg-primary)" }}>
      {/* React Flow Canvas */}
      <div className="flex-1 h-full relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.1}
          maxZoom={2}
          attributionPosition="bottom-left"
          proOptions={{ hideAttribution: true }}
        >
          <Background color="var(--border)" gap={20} size={1} />
          <Controls 
            className="glass !border-[var(--border)] !rounded-xl !shadow-md overflow-hidden" 
            position="top-right" 
          />
          <Panel position="bottom-left" className="m-6">
            <div className="p-4 rounded-2xl glass border" style={{ boxShadow: "var(--shadow-lg)", borderColor: "var(--border)" }}>
              <div className="text-xs font-bold mb-3 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Semantic Tags</div>
              <div className="space-y-2.5">
                {[
                  ["#10B981", "Core Concept"],
                  ["#F59E0B", "Definition"],
                  ["#3B82F6", "Example / App"],
                  ["#8B5CF6", "Detail"]
                ].map(([color, label]) => (
                  <div key={label} className="flex items-center gap-3">
                    <div className="w-3.5 h-3.5 rounded-full shadow-sm" style={{ backgroundColor: color, border: "2px solid var(--bg-primary)" }} />
                    <span className="text-xs font-semibold" style={{ color: "var(--text-secondary)" }}>{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </Panel>
        </ReactFlow>
      </div>

      {/* Side Panel for Node Detail */}
      <div 
        className={`h-full border-l glass transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col relative ${isSidePanelOpen && selectedNodeData ? "w-[360px]" : "w-0 opacity-0 overflow-hidden"}`} 
        style={{ borderColor: "var(--border)" }}
      >
        <button 
          onClick={() => setIsSidePanelOpen(false)}
          className="absolute top-4 right-4 p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-muted transition-colors"
        >
          <PanelRightClose className="w-5 h-5" />
        </button>

        {selectedNodeData && (
          <>
            <div className="p-7 border-b pr-14" style={{ borderColor: "var(--border)" }}>
              <div className="text-[10px] font-extrabold mb-3 px-2.5 py-1 rounded-lg inline-block uppercase tracking-widest" style={{
                background: `${getStatusColor(selectedNodeData.tag)}15`, color: getStatusColor(selectedNodeData.tag),
              }}>
                {selectedNodeData.tag ? selectedNodeData.tag.replace("_", " ") : "Concept"}
              </div>
              <h3 className="text-xl font-bold leading-snug" style={{ color: "var(--text-primary)" }}>
                {selectedNodeData.label}
              </h3>
            </div>
            
            <div className="p-7 flex-1 overflow-y-auto custom-scrollbar">
              <div className="text-sm font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>Summary</div>
              {selectedNodeData.detail ? (
                <div className="text-[15px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  {selectedNodeData.detail}
                </div>
              ) : (
                <div className="text-[15px] italic" style={{ color: "var(--text-muted)" }}>
                  No detailed summary available.
                </div>
              )}
              
              {selectedNodeData.figureCount > 0 && (
                <div className="mt-8 p-4 rounded-2xl bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/5">
                  <div className="flex items-center gap-2 font-bold text-sm mb-1" style={{ color: "var(--text-primary)" }}>
                    <ImageIcon className="w-4 h-4" style={{ color: "var(--accent-primary)" }} />
                    Associated Figures
                  </div>
                  <div className="text-xs" style={{ color: "var(--text-secondary)" }}>
                    This concept references {selectedNodeData.figureCount} figure{selectedNodeData.figureCount !== 1 ? 's' : ''} in the textbook.
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
      
      {/* Open panel button (when closed but a node is selected) */}
      {!isSidePanelOpen && selectedNodeData && (
        <button 
          onClick={() => setIsSidePanelOpen(true)}
          className="absolute top-6 right-6 p-3 rounded-2xl glass border shadow-md hover:bg-black/5 dark:hover:bg-white/10 transition-colors z-10"
          style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
        >
          <PanelRightOpen className="w-5 h-5" />
        </button>
      )}
    </div>
  );
}
