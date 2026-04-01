import { useState, useMemo } from "react";
import { Plus, Minus, Sparkles, Loader2 } from "lucide-react";

const baseMindmapStructure = [
  { id: '2', label: 'Key Concepts', x: 250, y: 180, status: 'strong', children: [
    { id: '2a', label: 'Definition 1', x: 150, y: 120, status: 'strong' },
    { id: '2b', label: 'Definition 2', x: 200, y: 80, status: 'medium' },
    { id: '2c', label: 'Exceptions', x: 250, y: 50, status: 'weak' },
  ]},
  { id: '3', label: 'Applications', x: 550, y: 180, status: 'medium', children: [
    { id: '3a', label: 'Real-world', x: 650, y: 120, status: 'strong' },
    { id: '3b', label: 'Theory', x: 680, y: 80, status: 'weak' },
  ]},
  { id: '4', label: 'Formulas', x: 300, y: 420, status: 'strong' },
  { id: '5', label: 'Examples', x: 500, y: 420, status: 'weak' },
];

const getStatusColor = (status) => {
  switch (status) {
    case 'strong': return '#10B981';
    case 'weak': return '#EF4444';
    case 'medium': return '#F59E0B';
    default: return '#3B82F6';
  }
};

export function MindmapTab({ title = 'this chapter' }) {
  const [isGenerated, setIsGenerated] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const rootData = useMemo(() => {
    return { id: '1', label: title, x: 400, y: 300, children: baseMindmapStructure };
  }, [title]);

  const [zoom, setZoom] = useState(1);
  const [selectedNode, setSelectedNode] = useState(null);

  const handleGenerate = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      setIsGenerated(true);
    }, 2000);
  };

  const renderNode = (node) => {
    const isSelected = selectedNode === node.id;
    const color = getStatusColor(node.status);
    return (
      <g key={node.id}>
        {node.children?.map(child => (
          <line key={`line-${node.id}-${child.id}`} x1={node.x} y1={node.y} x2={child.x} y2={child.y}
            stroke="var(--border)" strokeWidth="2" opacity="0.4" />
        ))}
        <g onClick={() => setSelectedNode(node.id)} style={{ cursor: 'pointer' }}>
          <rect x={node.x - 65} y={node.y - 20} width="130" height="40" rx="20"
            fill="var(--bg-secondary)" stroke={color} strokeWidth={isSelected ? "3" : "2"}
            style={{ filter: isSelected ? `drop-shadow(0 0 16px ${color}60)` : 'none' }} />
          <text x={node.x} y={node.y + 5} textAnchor="middle" fill="var(--text-primary)"
            fontSize="13" fontWeight={node.id === '1' ? "700" : "500"} fontFamily="Inter, sans-serif">
            {node.label}
          </text>
        </g>
        {node.children?.map(child => renderNode(child))}
      </g>
    );
  };

  if (!isGenerated) {
    return (
      <div className="h-full flex items-center justify-center p-6" style={{ background: 'var(--bg-primary)' }}>
        <div className="max-w-md w-full p-10 rounded-3xl border text-center glass animate-fade-up" style={{ borderColor: 'var(--border)', boxShadow: 'var(--shadow-lg)' }}>
          <div className="w-20 h-20 mx-auto rounded-3xl flex items-center justify-center mb-6" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)' }}>
            <Sparkles className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
          </div>
          <h2 className="text-2xl font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Generate Mindmap</h2>
          <p className="text-[17px] mb-8 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Let AI build a visual connections map for <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</span>.
          </p>
          <button 
            onClick={handleGenerate} disabled={isGenerating}
            className="w-full h-14 rounded-2xl text-[17px] font-bold flex items-center justify-center gap-2 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
            style={{ background: 'var(--gradient-primary)', color: '#FFFFFF', boxShadow: 'var(--shadow-glow)' }}>
            {isGenerating ? <><Loader2 className="w-5 h-5 animate-spin" /> Generating Mindmap...</> : <><Sparkles className="w-5 h-5" /> Generate Mindmap</>}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full relative flex items-center justify-center" style={{ background: 'var(--bg-primary)' }}>
      {/* Zoom Controls */}
      <div className="absolute top-6 right-6 z-10 flex gap-2">
        {[[Plus, () => setZoom(Math.min(zoom + 0.1, 2))], [Minus, () => setZoom(Math.max(zoom - 0.1, 0.5))]].map(([Icon, fn], i) => (
          <button key={i} onClick={fn} className="w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 hover:scale-105"
            style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
            <Icon className="w-4 h-4" style={{ color: 'var(--text-primary)' }} />
          </button>
        ))}
      </div>

      <svg width="800" height="500" viewBox="0 0 800 500" style={{ transform: `scale(${zoom})`, transition: 'transform 0.3s' }}>
        <defs>
          <pattern id="dots" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1" fill="var(--border)" opacity="0.3" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dots)" />
        {renderNode(rootData)}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-6 left-6 z-10">
        <div className="p-4 rounded-2xl glass" style={{ boxShadow: 'var(--shadow-md)' }}>
          <div className="text-xs font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Understanding Level</div>
          <div className="space-y-2">
            {[['#10B981', 'Strong'], ['#F59E0B', 'Medium'], ['#EF4444', 'Weak']].map(([color, label]) => (
              <div key={label} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
