import { useState, useEffect } from "react";
import { FileQuestion, Loader2, Award, Calendar } from "lucide-react";
import { api } from "@/lib/api";

export function PYQTab({ title, chapterId }) {
  const [pyqs, setPyqs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const fetchPyqs = async () => {
      try {
        // Fetch up to 100 PYQs for the chapter
        const data = await api.catalog.listChapterPyqs(chapterId, { limit: 100 });
        setPyqs(data.items || []);
        setTotal(data.total || 0);
      } catch (err) {
        console.error("Failed to fetch PYQs:", err);
      } finally {
        setIsLoading(false);
      }
    };
    if (chapterId) fetchPyqs();
  }, [chapterId]);

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <Loader2 className="w-10 h-10 animate-spin" style={{ color: 'var(--accent-primary)' }} />
      </div>
    );
  }

  if (pyqs.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center">
        <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-6 glass" style={{ borderColor: 'var(--border)' }}>
          <FileQuestion className="w-10 h-10" style={{ color: 'var(--text-muted)' }} />
        </div>
        <h2 className="text-2xl font-bold mb-3" style={{ color: 'var(--text-primary)' }}>No PYQs Found</h2>
        <p className="text-[17px] text-muted max-w-md" style={{ color: 'var(--text-secondary)' }}>
          There are no previous year questions mapped to this chapter yet.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto custom-scrollbar p-6 lg:p-10">
      <div className="max-w-4xl mx-auto">
        <div className="mb-10 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-extrabold mb-3" style={{ color: 'var(--text-primary)' }}>
              Previous Year Questions
            </h1>
            <p className="text-lg" style={{ color: 'var(--text-secondary)' }}>
              {title} · {total} Questions
            </p>
          </div>
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center glass shadow-sm" style={{ borderColor: 'var(--border)' }}>
            <FileQuestion className="w-8 h-8" style={{ color: 'var(--accent-primary)' }} />
          </div>
        </div>

        <div className="space-y-6">
          {pyqs.map((pyq, idx) => (
            <div key={pyq.pyq_id} className="p-8 rounded-3xl border glass transition-all duration-300 hover:scale-[1.01]"
              style={{ borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)' }}>
              
              {/* Meta header */}
              <div className="flex items-center gap-4 mb-6 pb-4 border-b" style={{ borderColor: 'var(--border)' }}>
                <div className="px-3 py-1.5 rounded-lg text-xs font-bold" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}>
                  Q{idx + 1}
                </div>
                {pyq.year && (
                  <div className="flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-lg" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10B981' }}>
                    <Calendar className="w-4 h-4" />
                    {pyq.year}
                  </div>
                )}
                {pyq.exam && (
                  <div className="flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-lg" style={{ background: 'var(--accent-glow)', color: 'var(--accent-primary)' }}>
                    <Award className="w-4 h-4" />
                    {pyq.exam.toUpperCase()}
                  </div>
                )}
                {pyq.marks && (
                  <div className="ml-auto text-sm font-bold" style={{ color: 'var(--text-muted)' }}>
                    {pyq.marks} Mark{pyq.marks > 1 ? 's' : ''}
                  </div>
                )}
              </div>

              {/* Question */}
              <div className="text-[17px] font-semibold leading-relaxed mb-6 whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>
                {pyq.question}
              </div>

              {/* Answer (if any) */}
              {pyq.answer && (
                <div className="p-5 rounded-2xl border" style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)' }}>
                  <div className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>
                    Answer / Explanation
                  </div>
                  <div className="text-[15px] leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                    {pyq.answer}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
