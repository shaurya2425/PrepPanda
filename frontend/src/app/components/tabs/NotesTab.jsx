import { useState } from "react";
import { Sparkles, Loader2, AlertCircle, CheckCircle2, BookOpen, GitCommit, Image as ImageIcon, Layout, Zap, Lightbulb, SplitSquareHorizontal, Download } from "lucide-react";

// ── PDF generation from blocks ─────────────────────────────────────
function generatePDF(blocks, title) {
  const renderBlock = (block) => {
    switch (block.type) {
      case 'concept': {
        const badge = block.importance === 'high' ? '<span style="background:#fee2e2;color:#dc2626;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;margin-left:8px">HIGH YIELD</span>' : '';
        return `<div style="border:1px solid #e2e8f0;border-radius:12px;padding:20px;margin-bottom:16px;background:${block.importance==='high'?'#fef2f2':'#f8fafc'}">
          <h3 style="margin:0 0 12px;font-size:17px;color:#0f172a">${block.title}${badge}</h3>
          <ul style="margin:0;padding-left:20px;color:#334155">${(block.content||[]).map(p => `<li style="margin-bottom:6px;line-height:1.6">${p}</li>`).join('')}</ul>
        </div>`;
      }
      case 'definition':
        return `<div style="border-left:4px solid #8b5cf6;background:#f5f3ff;border-radius:0 12px 12px 0;padding:16px 20px;margin-bottom:16px">
          <div style="font-size:11px;font-weight:700;color:#7c3aed;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Definition</div>
          <div style="font-size:17px;font-weight:700;color:#0f172a;margin-bottom:4px">${block.term}</div>
          <div style="color:#475569;font-style:italic;line-height:1.6">${block.definition}</div>
        </div>`;
      case 'process':
        return `<div style="border:1px solid #a7f3d0;background:#ecfdf5;border-radius:12px;padding:20px;margin-bottom:16px">
          <h3 style="margin:0 0 14px;font-size:17px;color:#065f46">⚙️ ${block.title}</h3>
          <ol style="margin:0;padding-left:20px;color:#334155">${(block.steps||[]).map(s => `<li style="margin-bottom:10px;line-height:1.5"><strong style="color:#047857">${s.title}</strong><br/><span style="color:#475569">${s.explanation}</span></li>`).join('')}</ol>
        </div>`;
      case 'diagram':
        return `<div style="border:1px solid #c7d2fe;background:#eef2ff;border-radius:12px;padding:20px;margin-bottom:16px">
          <h3 style="margin:0 0 8px;font-size:17px;color:#3730a3">📊 ${block.title}</h3>
          <p style="color:#475569;font-style:italic;margin:0 0 10px">${block.visual_hint||''}</p>
          ${block.labels?.length ? `<div style="margin-bottom:8px">${block.labels.map(l => `<span style="display:inline-block;background:#ddd6fe;color:#5b21b6;padding:3px 10px;border-radius:8px;font-size:12px;margin:2px 4px">${l}</span>`).join('')}</div>` : ''}
          <p style="color:#64748b;font-size:13px;margin:0"><strong>How to read:</strong> ${block.explanation||''}</p>
        </div>`;
      case 'comparison': {
        if (!block.items?.length) return '';
        const keys = Object.keys(block.items[0]).filter(k => k !== 'feature');
        return `<div style="border:1px solid #e2e8f0;border-radius:12px;padding:20px;margin-bottom:16px;overflow:hidden">
          <h3 style="margin:0 0 12px;font-size:17px;color:#0f172a">⚖️ ${block.title}</h3>
          <table style="width:100%;border-collapse:collapse;font-size:14px">
            <thead><tr style="background:#f1f5f9">
              <th style="text-align:left;padding:10px;border-bottom:2px solid #cbd5e1;color:#0891b2">Feature</th>
              ${keys.map(k => `<th style="text-align:left;padding:10px;border-bottom:2px solid #cbd5e1">${k}</th>`).join('')}
            </tr></thead>
            <tbody>${block.items.map(item => `<tr>
              <td style="padding:10px;border-bottom:1px solid #e2e8f0;font-weight:600;color:#0891b2">${item.feature}</td>
              ${keys.map(k => `<td style="padding:10px;border-bottom:1px solid #e2e8f0;color:#475569">${item[k]}</td>`).join('')}
            </tr>`).join('')}</tbody>
          </table>
        </div>`;
      }
      case 'exam_focus':
        return `<div style="border:2px solid #fbbf24;background:#fffbeb;border-radius:12px;padding:20px;margin-bottom:16px">
          <div style="font-size:15px;font-weight:800;color:#d97706;margin-bottom:10px">⚡ EXAM FOCUS / PYQ</div>
          <ul style="margin:0;padding-left:20px;color:#92400e">${(block.points||[]).map(p => `<li style="margin-bottom:6px;line-height:1.5;font-weight:500">${p}</li>`).join('')}</ul>
        </div>`;
      case 'memory_hook':
        return `<div style="border:1px solid #f9a8d4;background:#fdf2f8;border-radius:12px;padding:16px 20px;margin-bottom:16px">
          <div style="font-size:11px;font-weight:700;color:#db2777;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">💡 Memory Hook</div>
          <div style="color:#831843;font-size:16px;font-weight:500">${block.hook}</div>
        </div>`;
      case 'image':
        return `<div style="text-align:center;margin-bottom:16px">
          <img src="${block.url}" alt="${block.caption}" style="max-width:100%;border-radius:8px;border:1px solid #e2e8f0" />
          <div style="color:#64748b;font-size:13px;margin-top:6px">${block.caption}</div>
        </div>`;
      default:
        return '';
    }
  };

  const html = `<!DOCTYPE html>
<html><head>
  <meta charset="utf-8">
  <title>${title} — PrepPanda Notes</title>
  <style>
    @page { margin: 20mm 15mm; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 750px; margin: 0 auto; color: #0f172a; line-height: 1.6; }
    h1 { font-size: 26px; text-align: center; margin-bottom: 4px; }
    .subtitle { text-align: center; color: #64748b; font-size: 14px; margin-bottom: 30px; }
    .footer { text-align: center; color: #94a3b8; font-size: 11px; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 12px; }
  </style>
</head><body>
  <h1>${title}</h1>
  <div class="subtitle">Smart Notes — Generated by PrepPanda AI</div>
  ${blocks.map(renderBlock).join('')}
  <div class="footer">PrepPanda AI Notes • Generated ${new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</div>
</body></html>`;

  const win = window.open('', '_blank');
  if (!win) { alert('Please allow popups to download PDF.'); return; }
  win.document.write(html);
  win.document.close();
  // Small delay to ensure content renders before print dialog
  setTimeout(() => win.print(), 400);
}

const BlockConcept = ({ block }) => {
  const importanceColors = {
    high: "border-red-500/50 bg-red-500/10 text-red-400",
    medium: "border-blue-500/50 bg-blue-500/10 text-blue-400",
    low: "border-slate-500/50 bg-slate-500/10 text-slate-400",
  };
  const color = importanceColors[block.importance] || importanceColors.medium;

  return (
    <div className={`p-6 rounded-2xl border backdrop-blur-sm mb-6 shadow-lg transition-all hover:scale-[1.01] ${color.split(' ')[1]} border-white/10`}>
      <div className="flex items-center gap-3 mb-4">
        <div className={`p-2 rounded-xl ${color}`}>
          <Layout className="w-5 h-5" />
        </div>
        <h3 className="text-xl font-bold text-white tracking-wide">{block.title}</h3>
        {block.importance === 'high' && (
          <span className="ml-auto px-3 py-1 text-xs font-bold rounded-full bg-red-500/20 text-red-400 border border-red-500/30 shadow-[0_0_10px_rgba(239,68,68,0.3)]">HIGH YIELD</span>
        )}
      </div>
      <ul className="space-y-3">
        {block.content?.map((point, i) => (
          <li key={i} className="flex items-start gap-3 text-slate-200 leading-relaxed">
            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />
            <span>{point}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

const BlockDefinition = ({ block }) => (
  <div className="p-6 rounded-2xl border border-purple-500/30 bg-gradient-to-br from-purple-500/10 to-transparent mb-6 shadow-[0_4px_20px_-5px_rgba(168,85,247,0.15)] transition-all hover:scale-[1.01]">
    <div className="flex items-center gap-3 mb-3">
      <div className="p-2 rounded-xl bg-purple-500/20 text-purple-400">
        <BookOpen className="w-5 h-5" />
      </div>
      <h3 className="text-lg font-bold text-purple-300">DEFINITION</h3>
    </div>
    <div className="pl-14">
      <div className="text-xl font-bold text-white mb-2">{block.term}</div>
      <div className="text-slate-300 leading-relaxed text-lg italic border-l-2 border-purple-500/50 pl-4">{block.definition}</div>
    </div>
  </div>
);

const BlockProcess = ({ block }) => (
  <div className="p-6 rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/5 to-transparent mb-6 shadow-lg">
    <div className="flex items-center gap-3 mb-6">
      <div className="p-2 rounded-xl bg-emerald-500/20 text-emerald-400">
        <GitCommit className="w-5 h-5" />
      </div>
      <h3 className="text-xl font-bold text-white">{block.title}</h3>
    </div>
    <div className="space-y-0 relative before:absolute before:inset-0 before:ml-[23px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-emerald-500/50 before:to-transparent">
      {block.steps?.map((step, i) => (
        <div key={i} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active pb-8 last:pb-0">
          <div className="flex items-center justify-center w-12 h-12 rounded-full border-4 border-[#0F172A] bg-emerald-500 text-white font-bold shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow-[0_0_15px_rgba(16,185,129,0.5)] relative z-10">
            {step.step || i + 1}
          </div>
          <div className="w-[calc(100%-4rem)] md:w-[calc(50%-3rem)] p-5 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md transition-all group-hover:border-emerald-500/30 group-hover:bg-emerald-500/10">
            <h4 className="font-bold text-emerald-300 text-lg mb-2">{step.title}</h4>
            <p className="text-slate-300 leading-relaxed">{step.explanation}</p>
          </div>
        </div>
      ))}
    </div>
  </div>
);

const BlockDiagram = ({ block }) => (
  <div className="p-6 rounded-2xl border border-indigo-500/30 bg-indigo-500/5 mb-6 shadow-lg overflow-hidden relative">
    <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-3xl" />
    <div className="flex items-center gap-3 mb-4 relative z-10">
      <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400">
        <ImageIcon className="w-5 h-5" />
      </div>
      <h3 className="text-xl font-bold text-white">{block.title}</h3>
    </div>
    <div className="bg-[#0B1120] rounded-xl p-6 border border-white/5 mb-4 relative z-10">
      <div className="text-indigo-300 font-medium mb-3 flex items-center gap-2">
        <Sparkles className="w-4 h-4" /> Visual Hint
      </div>
      <p className="text-slate-300 italic mb-4">{block.visual_hint}</p>
      
      {block.labels && block.labels.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {block.labels.map((label, i) => (
            <span key={i} className="px-3 py-1.5 rounded-lg bg-indigo-500/20 text-indigo-300 text-sm font-medium border border-indigo-500/20">
              {label}
            </span>
          ))}
        </div>
      )}
    </div>
    <p className="text-slate-400 text-sm relative z-10"><span className="text-indigo-400 font-semibold">How to read:</span> {block.explanation}</p>
  </div>
);

const BlockComparison = ({ block }) => {
  if (!block.items || block.items.length === 0) return null;
  const itemZero = block.items[0];
  const keys = Object.keys(itemZero).filter(k => k !== 'feature');
  const keyA = keys[0] || 'A';
  const keyB = keys[1] || 'B';

  return (
    <div className="p-6 rounded-2xl border border-cyan-500/30 bg-cyan-500/5 mb-6 shadow-lg overflow-x-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-xl bg-cyan-500/20 text-cyan-400">
          <SplitSquareHorizontal className="w-5 h-5" />
        </div>
        <h3 className="text-xl font-bold text-white">{block.title}</h3>
      </div>
      <table className="w-full text-left border-collapse">
        <thead>
          <tr>
            <th className="p-4 border-b border-white/10 font-bold text-cyan-400 bg-white/5 rounded-tl-xl">Feature</th>
            <th className="p-4 border-b border-white/10 font-bold text-white bg-white/5">{keyA}</th>
            <th className="p-4 border-b border-white/10 font-bold text-white bg-white/5 rounded-tr-xl">{keyB}</th>
          </tr>
        </thead>
        <tbody>
          {block.items?.map((item, i) => (
            <tr key={i} className="hover:bg-white/5 transition-colors border-b border-white/5 last:border-0">
              <td className="p-4 font-medium text-cyan-300">{item.feature}</td>
              <td className="p-4 text-slate-300">{item[keyA]}</td>
              <td className="p-4 text-slate-300">{item[keyB]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const BlockExamFocus = ({ block }) => (
  <div className="p-6 rounded-2xl border-2 border-yellow-500/40 bg-gradient-to-r from-yellow-500/10 to-orange-500/5 mb-6 shadow-[0_0_20px_rgba(234,179,8,0.15)] transition-all hover:shadow-[0_0_30px_rgba(234,179,8,0.25)] relative overflow-hidden">
    <div className="absolute -right-10 -top-10 w-40 h-40 bg-yellow-500/20 blur-3xl rounded-full" />
    <div className="flex items-center gap-3 mb-4 relative z-10">
      <div className="p-2 rounded-xl bg-yellow-500/20 text-yellow-400 animate-pulse">
        <Zap className="w-6 h-6" />
      </div>
      <h3 className="text-xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-400">EXAM FOCUS / PYQ</h3>
    </div>
    <ul className="space-y-3 pl-2 relative z-10">
      {block.points?.map((point, i) => (
        <li key={i} className="flex items-start gap-3 text-slate-200">
          <CheckCircle2 className="w-5 h-5 text-yellow-500 shrink-0 mt-0.5" />
          <span className="text-[17px] font-medium">{point}</span>
        </li>
      ))}
    </ul>
  </div>
);

const BlockMemoryHook = ({ block }) => (
  <div className="p-5 rounded-2xl border border-pink-500/30 bg-pink-500/10 mb-6 flex gap-4 items-start shadow-lg">
    <div className="p-3 rounded-full bg-pink-500/20 text-pink-400 shrink-0">
      <Lightbulb className="w-6 h-6" />
    </div>
    <div>
      <h3 className="text-sm font-bold text-pink-400 uppercase tracking-wider mb-1">Memory Hook</h3>
      <p className="text-slate-200 text-lg font-medium">{block.hook}</p>
    </div>
  </div>
);

const BlockExample = ({ block }) => {
  const content = block.content || block.example || block.text || Object.values(block).join(" ");
  return (
    <div className="p-5 rounded-2xl border-l-4 border-l-blue-500 border-y border-r border-white/10 bg-blue-500/5 mb-6 pl-6 shadow-sm">
      <h3 className="text-sm font-bold text-blue-400 uppercase tracking-wider mb-2">Example</h3>
      <p className="text-slate-300 italic">{content}</p>
    </div>
  );
};

const BlockImage = ({ block }) => (
  <div className="rounded-2xl border border-white/10 overflow-hidden mb-6 shadow-lg bg-black/20">
    <img src={block.url} alt={block.caption} className="w-full object-contain max-h-[500px]" />
    {block.caption && (
      <div className="p-3 bg-white/5 backdrop-blur-md border-t border-white/10 text-center text-slate-300 text-sm">
        {block.caption}
      </div>
    )}
  </div>
);

export function NotesTab({ title = 'this chapter', chapterId = "1" }) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [blocks, setBlocks] = useState([]);
  const [batchCount, setBatchCount] = useState(0);
  const [error, setError] = useState(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    setBlocks([]);
    setBatchCount(0);
    setIsDone(false);

    try {
      const response = await fetch("http://localhost:8000/api/generate/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chapterId: chapterId, prompt: "" })
      });

      if (!response.ok) {
        throw new Error("Backend connection failed.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE lines from buffer
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // keep incomplete line in buffer

        for (const line of lines) {
          const trimmed = line.trim();

          // Handle "event: done"
          if (trimmed === "event: done") {
            setIsDone(true);
            setIsGenerating(false);
            continue;
          }

          // Handle "event: error"
          if (trimmed === "event: error") {
            continue; // next data line will have the error
          }

          // Handle data lines
          if (trimmed.startsWith("data: ")) {
            const jsonStr = trimmed.slice(6);
            try {
              const parsed = JSON.parse(jsonStr);

              // Check if it's an error event
              if (parsed.error) {
                setError(parsed.error);
                continue;
              }

              // Check if it's the done event payload
              if (parsed.total_blocks !== undefined) {
                continue;
              }

              // It's a batch of blocks — append them
              if (Array.isArray(parsed)) {
                setBlocks(prev => [...prev, ...parsed]);
                setBatchCount(prev => prev + 1);
              }
            } catch (e) {
              // ignore malformed lines
            }
          }
        }
      }

      setIsGenerating(false);
      setIsDone(true);

    } catch (err) {
      console.error(err);
      setError("Failed to connect to AI Backend. Ensure the FastAPI server is running with API keys.");
      setBlocks([
        { type: "concept", title: "Connection Error", content: ["The backend server is either offline or missing API keys.", "Please start the FastAPI server and try again."], importance: "high" }
      ]);
      setIsGenerating(false);
      setIsDone(true);
    }
  };

  // Initial state — show generate button
  if (blocks.length === 0 && !isGenerating) {
    return (
      <div className="h-full flex items-center justify-center p-6" style={{ background: 'var(--bg-primary)' }}>
        <div className="max-w-md w-full p-10 rounded-3xl border text-center glass animate-fade-up relative overflow-hidden" style={{ borderColor: 'var(--border)', boxShadow: 'var(--shadow-lg)' }}>
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-400 via-cyan-400 to-purple-500" />
          <div className="w-20 h-20 mx-auto rounded-3xl flex items-center justify-center mb-6 relative group" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)' }}>
            <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
            <Sparkles className="w-10 h-10 relative z-10" style={{ color: 'var(--accent-primary)' }} />
          </div>
          <h2 className="text-3xl font-extrabold mb-3 text-transparent bg-clip-text bg-gradient-to-b from-white to-slate-400">AI Smart Notes</h2>
          <p className="text-[17px] mb-8 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Generate structured, high-retention study notes optimized for <span className="font-semibold text-emerald-400">exam recall</span>.
          </p>
          <button 
            onClick={handleGenerate}
            className="w-full h-14 rounded-2xl text-[17px] font-bold flex items-center justify-center gap-2 transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] bg-gradient-to-r from-emerald-500 to-cyan-500 text-white shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)]">
            <Sparkles className="w-5 h-5" /> Generate Smart Notes
          </button>
        </div>
      </div>
    );
  }

  // Streaming / generated state
  return (
    <div className="h-full overflow-auto" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="space-y-2 animate-fade-up">
          {error && (
            <div className="p-4 mb-8 rounded-2xl flex items-start gap-3 border border-red-500/30 bg-red-500/10 shadow-lg">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-400" />
              <div className="text-[15px] font-medium text-slate-200">
                {error}
              </div>
            </div>
          )}

          <div className="mb-10 text-center">
            <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400 mb-4">{title}</h1>
            <p className="text-slate-400 font-medium text-lg">Smart Notes & High-Yield Concepts</p>
          </div>

          {/* Live progress indicator while streaming */}
          {isGenerating && (
            <div className="mb-8 p-4 rounded-2xl border border-emerald-500/30 bg-emerald-500/5 flex items-center gap-4">
              <Loader2 className="w-5 h-5 animate-spin text-emerald-400 shrink-0" />
              <div className="flex-1">
                <div className="text-emerald-300 font-semibold text-sm mb-1.5">
                  Generating notes — batch {batchCount} received ({blocks.length} blocks so far)
                </div>
                <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full animate-pulse" style={{ width: '100%' }} />
                </div>
              </div>
            </div>
          )}

          {/* Done indicator + Download */}
          {isDone && !isGenerating && blocks.length > 0 && (
            <div className="mb-8 p-4 rounded-2xl border border-emerald-500/30 bg-emerald-500/5 flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <span className="text-emerald-300 font-medium text-sm flex-1">
                Done — {blocks.length} blocks generated across {batchCount} batches
              </span>
              <button
                onClick={() => generatePDF(blocks, title)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/10 text-white text-sm font-semibold transition-all hover:scale-105 active:scale-95"
              >
                <Download className="w-4 h-4" />
                Download PDF
              </button>
            </div>
          )}

          <div className="space-y-2 pb-20">
            {blocks.map((block, index) => {
              switch (block.type) {
                case 'concept': return <BlockConcept key={index} block={block} />;
                case 'definition': return <BlockDefinition key={index} block={block} />;
                case 'process': return <BlockProcess key={index} block={block} />;
                case 'diagram': return <BlockDiagram key={index} block={block} />;
                case 'comparison': return <BlockComparison key={index} block={block} />;
                case 'exam_focus': return <BlockExamFocus key={index} block={block} />;
                case 'memory_hook': return <BlockMemoryHook key={index} block={block} />;
                case 'example': return <BlockExample key={index} block={block} />;
                case 'image': return <BlockImage key={index} block={block} />;
                default: 
                  return (
                    <div key={index} className="p-4 rounded-xl bg-white/5 border border-white/10 mb-4">
                      <pre className="text-xs text-slate-400 whitespace-pre-wrap">{JSON.stringify(block, null, 2)}</pre>
                    </div>
                  );
              }
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
