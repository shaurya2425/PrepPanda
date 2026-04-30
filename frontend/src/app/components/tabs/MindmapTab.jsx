import { useState, useEffect } from "react";
import { Plus, Minus, Sparkles, Loader2, Maximize } from "lucide-react";
import { api } from "@/lib/api";

const getStatusColor = (tag) => {
  const t = (tag || '').toLowerCase();
  if (t === 'core_concept') return '#10B981'; // Green
  if (t === 'definition') return '#F59E0B'; // Yellow
  if (t === 'example' || t === 'application') return '#3B82F6'; // Blue
  return '#8B5CF6'; // Purple for detail/other
};

// Simple recursive tree layout
function layoutTree(node, x = 400, y = 80, xOffset = 300) {
  const result = { 
    ...node, 
    x, 
    y,
    // default status for styling
    status: node.tag || 'concept'
  };

  if (node.children && node.children.length > 0) {
    const totalWidth = (node.children.length - 1) * xOffset;
    const startX = x - totalWidth / 2;
    result.children = node.children.map((child, idx) => 
      layoutTree(child, startX + idx * xOffset, y + 120, xOffset * 0.6)
    );
  }
  return result;
}

export function MindmapTab({ title = 'this chapter', chapterId }) {
  const [isGenerated, setIsGenerated] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [rootData, setRootData] = useState(null);
  const [error, setError] = useState(null);

  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const data = await api.mindmap.getTree(chapterId);
      if (data && data.tree) {
        // Apply layout to the semantic tree
        const laidOut = layoutTree(data.tree);
        setRootData(laidOut);
        setIsGenerated(true);
      }
    } catch (err) {
      console.error("Mindmap generation failed:", err);
      setError("Failed to generate mindmap. Please ensure the chapter has been fully ingested.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleMouseDown = (e) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const renderNode = (node) => {
    const isSelected = selectedNode?.id === node.id;
    const color = getStatusColor(node.tag);
    
    // Auto-wrap text roughly
    const label = node.label.length > 25 ? node.label.substring(0, 22) + '...' : node.label;

    return (
      <g key={node.id}>
        {node.children?.map(child => (
          <line key={`line-${node.id}-${child.id}`} x1={node.x} y1={node.y} x2={child.x} y2={child.y}
            stroke="var(--border)" strokeWidth="2" opacity="0.4" />
        ))}
        <g 
          onClick={(e) => { e.stopPropagation(); setSelectedNode(node); }} 
          style={{ cursor: 'pointer' }}
        >
          <rect x={node.x - 75} y={node.y - 25} width="150" height="50" rx="12"
            fill="var(--bg-secondary)" stroke={color} strokeWidth={isSelected ? "3" : "2"}
            style={{ filter: isSelected ? `drop-shadow(0 0 16px ${color}60)` : 'none' }} />
          
          <text x={node.x} y={node.y + 4} textAnchor="middle" fill="var(--text-primary)"
            fontSize="12" fontWeight={node.depth === 0 ? "700" : "500"} fontFamily="Inter, sans-serif">
            {label}
          </text>
          
          {node.tag && node.depth > 0 && (
            <text x={node.x} y={node.y - 32} textAnchor="middle" fill={color}
              fontSize="10" fontWeight="600" opacity="0.8">
              {node.tag.toUpperCase()}
            </text>
          )}
        </g>
        {node.children?.map(child => renderNode(child))}
      </g>
    );
  };

  if (!isGenerated) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6" style={{ background: 'var(--bg-primary)' }}>
        <div className="max-w-md w-full p-10 rounded-3xl border text-center glass animate-fade-up" style={{ borderColor: 'var(--border)', boxShadow: 'var(--shadow-lg)' }}>
          <div className="w-20 h-20 mx-auto rounded-3xl flex items-center justify-center mb-6" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)' }}>
            <Sparkles className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
          </div>
          <h2 className="text-2xl font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Visual Mindmap</h2>
          <p className="text-[17px] mb-8 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Automatically extract a hierarchical concept map for <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</span>.
          </p>
          
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-sm font-medium">
              {error}
            </div>
          )}

          <button 
            onClick={handleGenerate} disabled={isGenerating}
            className="w-full h-14 rounded-2xl text-[17px] font-bold flex items-center justify-center gap-2 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
            style={{ background: 'var(--gradient-primary)', color: '#FFFFFF', boxShadow: 'var(--shadow-glow)' }}>
            {isGenerating ? <><Loader2 className="w-5 h-5 animate-spin" /> Analyzing Chapter...</> : <><Sparkles className="w-5 h-5" /> Generate Concept Map</>}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full relative flex" style={{ background: 'var(--bg-primary)' }}>
      {/* SVG Canvas */}
      <div 
        className="flex-1 overflow-hidden cursor-grab active:cursor-grabbing relative"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={() => setSelectedNode(null)}
      >
        <svg width="100%" height="100%">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="1.5" fill="var(--border)" opacity="0.4" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {rootData && renderNode(rootData)}
          </g>
        </svg>
      </div>

      {/* Controls & Legend */}
      <div className="absolute top-6 right-6 z-10 flex flex-col gap-4">
        <div className="flex flex-col gap-2 p-2 rounded-2xl glass" style={{ boxShadow: 'var(--shadow-md)', borderColor: 'var(--border)' }}>
          <button onClick={() => setZoom(z => Math.min(z + 0.1, 2))} className="w-10 h-10 rounded-xl flex items-center justify-center transition-all hover:bg-black/5 dark:hover:bg-white/10">
            <Plus className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
          </button>
          <button onClick={() => { setZoom(1); setPan({x:0, y:0}); }} className="w-10 h-10 rounded-xl flex items-center justify-center transition-all hover:bg-black/5 dark:hover:bg-white/10">
            <Maximize className="w-4 h-4" style={{ color: 'var(--text-primary)' }} />
          </button>
          <button onClick={() => setZoom(z => Math.max(z - 0.1, 0.3))} className="w-10 h-10 rounded-xl flex items-center justify-center transition-all hover:bg-black/5 dark:hover:bg-white/10">
            <Minus className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
          </button>
        </div>
      </div>

      <div className="absolute bottom-6 left-6 z-10">
        <div className="p-5 rounded-3xl glass border" style={{ boxShadow: 'var(--shadow-lg)', borderColor: 'var(--border)' }}>
          <div className="text-sm font-bold mb-4 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Semantic Tags</div>
          <div className="space-y-3">
            {[
              ['#10B981', 'Core Concept'], 
              ['#F59E0B', 'Definition'], 
              ['#3B82F6', 'Example / App'],
              ['#8B5CF6', 'Detail']
            ].map(([color, label]) => (
              <div key={label} className="flex items-center gap-3">
                <div className="w-4 h-4 rounded-full shadow-sm" style={{ backgroundColor: color, border: '2px solid rgba(255,255,255,0.1)' }} />
                <span className="text-[13px] font-medium" style={{ color: 'var(--text-secondary)' }}>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Side Panel for Node Detail */}
      {selectedNode && (
        <div className="w-80 h-full border-l glass animate-slide-left flex flex-col" style={{ borderColor: 'var(--border)' }}>
          <div className="p-6 border-b" style={{ borderColor: 'var(--border)' }}>
            <div className="text-xs font-bold mb-2 px-2.5 py-1 rounded-lg inline-block uppercase tracking-wide" style={{
              background: 'var(--bg-tertiary)', color: getStatusColor(selectedNode.tag),
            }}>
              {selectedNode.tag ? selectedNode.tag.replace('_', ' ') : 'Concept'}
            </div>
            <h3 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
              {selectedNode.label}
            </h3>
          </div>
          <div className="p-6 flex-1 overflow-y-auto custom-scrollbar">
            {selectedNode.detail ? (
              <div className="text-[15px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                {selectedNode.detail}
              </div>
            ) : (
              <div className="text-sm italic" style={{ color: 'var(--text-muted)' }}>
                No detailed summary available for this node.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
