import { useState } from "react";
import { Sparkles, Loader2, AlertCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function NotesTab({ title = 'this chapter', chapterId = "1" }) {
  const [isGenerated, setIsGenerated] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [notesContent, setNotesContent] = useState("");
  const [error, setError] = useState(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const response = await fetch("http://localhost:8000/api/generate/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chapterId: chapterId, prompt: "" })
      });
      
      if (!response.ok) {
        throw new Error("Backend connection failed.");
      }
      
      const data = await response.json();
      setNotesContent(data.content);
      setIsGenerated(true);
    } catch (err) {
      console.error(err);
      setError("Failed to connect to AI Backend. Ensure the FastAPI server is running with API keys.");
      // Fallback for visual testing without backend
      setTimeout(() => {
        setNotesContent(`# ${title}\n\n*The backend server is either offline or missing API keys.* \n\n**Please configure your FastAPI backend.**`);
        setIsGenerated(true);
      }, 500);
    } finally {
      setIsGenerating(false);
    }
  };

  if (!isGenerated) {
    return (
      <div className="h-full flex items-center justify-center p-6" style={{ background: 'var(--bg-primary)' }}>
        <div className="max-w-md w-full p-10 rounded-3xl border text-center glass animate-fade-up" style={{ borderColor: 'var(--border)', boxShadow: 'var(--shadow-lg)' }}>
          <div className="w-20 h-20 mx-auto rounded-3xl flex items-center justify-center mb-6" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)' }}>
            <Sparkles className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
          </div>
          <h2 className="text-2xl font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Generate Notes</h2>
          <p className="text-[17px] mb-8 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Let AI create comprehensive, easy-to-understand notes for <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</span>.
          </p>
          <button 
            onClick={handleGenerate} disabled={isGenerating}
            className="w-full h-14 rounded-2xl text-[17px] font-bold flex items-center justify-center gap-2 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
            style={{ background: 'var(--gradient-primary)', color: '#FFFFFF', boxShadow: 'var(--shadow-glow)' }}>
            {isGenerating ? <><Loader2 className="w-5 h-5 animate-spin" /> Generating Notes...</> : <><Sparkles className="w-5 h-5" /> Generate Notes</>}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="space-y-8 animate-fade-up">
          {error && (
            <div className="p-4 mb-6 rounded-2xl flex items-start gap-3 border shadow-sm" style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)' }}>
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: 'var(--accent-warning)' }} />
              <div className="text-[15px] font-medium" style={{ color: 'var(--text-primary)' }}>
                {error}
              </div>
            </div>
          )}

          <div className="prose prose-lg dark:prose-invert max-w-none prose-headings:font-bold prose-a:text-blue-500">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {notesContent}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
