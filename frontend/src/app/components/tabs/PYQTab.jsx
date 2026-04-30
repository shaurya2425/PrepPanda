import { useState, useEffect } from "react";
import { FileQuestion, Loader2, Award, Calendar, Sparkles, TrendingUp, AlertTriangle, BookOpen, BrainCircuit } from "lucide-react";
import { api } from "@/lib/api";

export function PYQTab({ title, chapterId }) {
  const [pyqs, setPyqs] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        // Fetch standard PYQs
        const data = await api.catalog.listChapterPyqs(chapterId, { limit: 100 });
        setPyqs(data.items || []);
        setTotal(data.total || 0);

        // Fetch Analysis
        try {
          const analysisData = await api.analysis.getChapterAnalysis(chapterId, { top_k: 3 });
          setAnalysis(analysisData);
        } catch (analysisErr) {
          console.error("Failed to fetch analysis:", analysisErr);
        }

      } catch (err) {
        console.error("Failed to fetch PYQs:", err);
      } finally {
        setIsLoading(false);
      }
    };
    if (chapterId) fetchData();
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

          {/* Trends Section */}
          {analysis && analysis.trends && analysis.trends.length > 0 && (
            <div className="mb-12">
              <div className="flex items-center gap-3 mb-6">
                <TrendingUp className="w-6 h-6" style={{ color: 'var(--accent-primary)' }} />
                <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Topic Trends</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysis.trends.slice(0, 4).map((trend, idx) => (
                  <div key={idx} className="p-5 rounded-2xl border glass flex flex-col justify-between"
                    style={{ borderColor: 'var(--border)' }}>
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <div className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider ${
                          trend.trend === 'rising' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' :
                          trend.trend === 'consistent' ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400' :
                          'bg-gray-500/10 text-gray-600 dark:text-gray-400'
                        }`}>
                          {trend.trend}
                        </div>
                        <div className="text-sm font-bold text-muted">
                          {trend.zone.frequency} PYQs
                        </div>
                      </div>
                      <div className="font-semibold text-[15px] mb-2" style={{ color: 'var(--text-primary)' }}>
                        {trend.zone.section_titles.length > 0 ? trend.zone.section_titles.join(', ') : `Zone ${trend.zone.zone_range}`}
                      </div>
                    </div>
                    <div className="text-xs font-medium mt-3 flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
                      <Calendar className="w-3.5 h-3.5" />
                      Years: {trend.zone.years_seen.join(', ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Analysis Section */}
          {analysis && analysis.predictions && analysis.predictions.length > 0 && (
            <div className="mb-12">
              <div className="flex items-center gap-3 mb-6">
                <Sparkles className="w-6 h-6" style={{ color: 'var(--accent-primary)' }} />
                <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>AI Predicted Questions</h2>
              </div>
              <div className="space-y-6">
                {analysis.predictions.map((pred, idx) => (
                  <div key={idx} className="relative p-8 rounded-3xl border transition-all duration-300 hover:scale-[1.01] overflow-hidden"
                    style={{ background: 'rgba(124, 58, 237, 0.03)', borderColor: 'rgba(124, 58, 237, 0.2)', boxShadow: '0 4px 20px rgba(124, 58, 237, 0.05)' }}>
                    
                    {/* Glowing background blob */}
                    <div className="absolute top-0 right-0 w-64 h-64 bg-violet-500 rounded-full mix-blend-multiply filter blur-3xl opacity-5 pointer-events-none transform translate-x-1/2 -translate-y-1/2" />

                    {/* Header */}
                    <div className="flex items-center gap-4 mb-6 pb-4 border-b" style={{ borderColor: 'rgba(124, 58, 237, 0.1)' }}>
                      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold bg-violet-500/10 text-violet-600 dark:text-violet-400">
                        <BrainCircuit className="w-4 h-4" />
                        PREDICTION {idx + 1}
                      </div>
                      {pred.confidence && (
                        <div className="flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                          <TrendingUp className="w-4 h-4" />
                          {Math.round(pred.confidence * 100)}% Confidence
                        </div>
                      )}
                      {pred.marks && (
                        <div className="ml-auto text-sm font-bold text-violet-600/70 dark:text-violet-400/70">
                          {pred.marks} Mark{pred.marks > 1 ? 's' : ''}
                        </div>
                      )}
                    </div>

                    {/* Question text */}
                    <div className="text-[18px] font-bold leading-relaxed mb-6 whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>
                      {pred.question}
                    </div>

                    {/* Reasoning */}
                    <div className="p-5 rounded-2xl bg-white/50 dark:bg-black/20 border border-violet-500/10 mb-4">
                      <div className="text-xs font-bold uppercase tracking-wider mb-2 flex items-center gap-2 text-violet-600/70 dark:text-violet-400/70">
                        <AlertTriangle className="w-3.5 h-3.5" /> AI Reasoning
                      </div>
                      <div className="text-[15px] leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                        {pred.reasoning}
                      </div>
                    </div>

                    {/* Source mapping details */}
                    {pred.source_zone && (
                      <div className="flex flex-wrap items-center gap-3 mt-4 text-xs font-medium text-violet-600/60 dark:text-violet-400/60">
                        <div className="flex items-center gap-1.5">
                          <BookOpen className="w-3.5 h-3.5" />
                          Based on Zone: {pred.source_zone.zone_range}
                        </div>
                        {pred.source_zone.frequency && (
                          <div className="flex items-center gap-1.5">
                            · {pred.source_zone.frequency} PYQ hits
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Regular PYQs */}
          <div className="flex items-center gap-3 mb-6">
            <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Previous Exam Questions</h2>
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
