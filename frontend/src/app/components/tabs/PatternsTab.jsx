import { useState, useEffect } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  CartesianGrid, AreaChart, Area,
} from "recharts";
import { api } from "../../../lib/api";
import { TrendingUp, BarChart3, Target, Repeat, Flame, BookOpen } from "lucide-react";

const COLORS = [
  "#6366f1", "#06b6d4", "#f59e0b", "#ef4444", "#10b981",
  "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#3b82f6",
];

const cardStyle = {
  background: "var(--bg-tertiary)",
  borderColor: "var(--border)",
  boxShadow: "var(--shadow-sm)",
};

const tooltipStyle = {
  backgroundColor: "var(--bg-primary)",
  border: "1px solid var(--border)",
  borderRadius: 12,
  color: "var(--text-primary)",
};

export function PatternsTab({ books }) {
  const [selectedBook, setSelectedBook] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (selectedBook) fetchPatterns();
  }, [selectedBook]);

  const fetchPatterns = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.analysis.getBookPatterns(selectedBook);
      setReport(data);
    } catch (err) {
      setError(err.message || "Failed to fetch pattern data");
    } finally {
      setLoading(false);
    }
  };

  if (!selectedBook) {
    return (
      <div>
        <h2 className="text-2xl font-bold mb-6" style={{ color: "var(--text-primary)" }}>
          PYQ Pattern Analysis
        </h2>
        <select
          value={selectedBook}
          onChange={(e) => setSelectedBook(e.target.value)}
          className="w-full max-w-sm px-4 py-3 rounded-xl border focus:outline-none"
          style={{ background: "var(--bg-tertiary)", borderColor: "var(--border)", color: "var(--text-primary)" }}
        >
          <option value="">Select a book to analyse</option>
          {books.map((b) => (
            <option key={b.book_id} value={b.book_id}>
              {b.title}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-4 rounded-full animate-spin" style={{ borderColor: "var(--border)", borderTopColor: "var(--accent-primary)" }} />
        <span className="ml-3 font-semibold" style={{ color: "var(--text-secondary)" }}>Crunching numbers…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-500">
        {error}
      </div>
    );
  }

  if (!report) return null;

  const { summary, year_frequency, chapter_frequency, marks_distribution, exam_breakdown, year_chapter_heatmap, topic_hotspots, repetition_clusters, difficulty_curve, chapter_coverage } = report;

  return (
    <div className="space-y-6">
      {/* Book picker + header */}
      <div className="flex flex-wrap items-center gap-4">
        <select
          value={selectedBook}
          onChange={(e) => setSelectedBook(e.target.value)}
          className="px-4 py-2.5 rounded-xl border focus:outline-none"
          style={{ background: "var(--bg-tertiary)", borderColor: "var(--border)", color: "var(--text-primary)" }}
        >
          {books.map((b) => (
            <option key={b.book_id} value={b.book_id}>{b.title}</option>
          ))}
        </select>
        <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          {report.book_title}
        </h2>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: Target, label: "Total PYQs", value: summary.total_questions, color: "#6366f1" },
          { icon: BookOpen, label: "Year Span", value: summary.year_span, color: "#06b6d4" },
          { icon: BarChart3, label: "Avg Marks", value: summary.avg_marks, color: "#f59e0b" },
          { icon: Flame, label: "Topics Hit", value: summary.unique_topics_hit, color: "#ef4444" },
        ].map((s, i) => {
          const Icon = s.icon;
          return (
            <div key={i} className="p-5 rounded-2xl border" style={cardStyle}>
              <div className="flex items-center gap-2 mb-2">
                <Icon className="w-4 h-4" style={{ color: s.color }} />
                <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{s.label}</span>
              </div>
              <div className="text-2xl font-extrabold" style={{ color: s.color }}>{s.value}</div>
            </div>
          );
        })}
      </div>

      {/* Row 1: Year frequency + Marks distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 p-6 rounded-2xl border" style={cardStyle}>
          <h3 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>
            <TrendingUp className="w-4 h-4 inline mr-2" style={{ color: "#6366f1" }} />
            Year-wise Question Frequency
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={year_frequency}>
              <defs>
                <linearGradient id="yearGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="label" tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
              <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Area type="monotone" dataKey="value" stroke="#6366f1" fill="url(#yearGrad)" strokeWidth={2} name="Questions" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="p-6 rounded-2xl border" style={cardStyle}>
          <h3 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>Marks Distribution</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={marks_distribution} dataKey="value" nameKey="label" cx="50%" cy="50%" innerRadius={50} outerRadius={90} paddingAngle={4} label={({ label }) => label}>
                {marks_distribution.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 2: Chapter frequency + Exam breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl border" style={cardStyle}>
          <h3 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>Chapter-wise Frequency</h3>
          <ResponsiveContainer width="100%" height={Math.max(200, chapter_frequency.length * 36)}>
            <BarChart data={chapter_frequency} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
              <YAxis dataKey="label" type="category" width={160} tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="value" name="Questions" radius={[0, 6, 6, 0]}>
                {chapter_frequency.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="p-6 rounded-2xl border" style={cardStyle}>
          <h3 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>Exam Board Breakdown</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={exam_breakdown}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="label" tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
              <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="value" name="Questions" radius={[6, 6, 0, 0]}>
                {exam_breakdown.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 3: Difficulty curve */}
      {difficulty_curve.length > 0 && (
        <div className="p-6 rounded-2xl border" style={cardStyle}>
          <h3 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>Difficulty Curve (Avg Marks / Year)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={difficulty_curve}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="year" tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
              <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend />
              <Line type="monotone" dataKey="avg_marks" stroke="#f59e0b" strokeWidth={2} name="Avg Marks" dot={{ r: 4 }} />
              <Line type="monotone" dataKey="question_count" stroke="#6366f1" strokeWidth={2} name="Question Count" dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Row 4: Topic hotspots table */}
      {topic_hotspots.length > 0 && (
        <div className="p-6 rounded-2xl border" style={cardStyle}>
          <h3 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>
            <Flame className="w-4 h-4 inline mr-2" style={{ color: "#ef4444" }} />
            Topic Hotspots
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "2px solid var(--border)" }}>
                  {["Section", "Chapter", "Freq", "Avg Marks", "Years", "Trend"].map((h) => (
                    <th key={h} className="py-2 px-3 text-left font-bold" style={{ color: "var(--text-muted)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {topic_hotspots.slice(0, 15).map((t, i) => (
                  <tr key={i} className="transition-colors" style={{ borderBottom: "1px solid var(--border)" }}>
                    <td className="py-2.5 px-3 font-semibold" style={{ color: "var(--text-primary)" }}>{t.section_title}</td>
                    <td className="py-2.5 px-3 text-xs" style={{ color: "var(--text-secondary)" }}>Ch {t.chapter_number}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded-full text-xs font-bold" style={{ background: "rgba(99,102,241,0.15)", color: "#6366f1" }}>{t.frequency}</span>
                    </td>
                    <td className="py-2.5 px-3" style={{ color: "var(--text-secondary)" }}>{t.avg_marks || "—"}</td>
                    <td className="py-2.5 px-3 text-xs" style={{ color: "var(--text-muted)" }}>{t.years.join(", ")}</td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${t.trend === "rising" ? "text-green-400 bg-green-500/15" : t.trend === "declining" ? "text-red-400 bg-red-500/15" : "text-yellow-400 bg-yellow-500/15"}`}>
                        {t.trend}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Row 5: Repetition clusters */}
      {repetition_clusters.length > 0 && (
        <div className="p-6 rounded-2xl border" style={cardStyle}>
          <h3 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>
            <Repeat className="w-4 h-4 inline mr-2" style={{ color: "#06b6d4" }} />
            Repeated Topics ({repetition_clusters.length})
          </h3>
          <div className="space-y-3">
            {repetition_clusters.slice(0, 10).map((r, i) => (
              <div key={i} className="p-4 rounded-xl" style={{ background: "var(--bg-primary)" }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold" style={{ color: "var(--text-primary)" }}>{r.topic}</span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-bold" style={{ background: "rgba(6,182,212,0.15)", color: "#06b6d4" }}>
                    {r.year_count} years · {r.question_count} Qs
                  </span>
                </div>
                <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>{r.chapter_title} — Years: {r.years.join(", ")}</p>
                {r.sample_questions[0] && (
                  <p className="text-xs italic mt-1 truncate" style={{ color: "var(--text-secondary)" }}>"{r.sample_questions[0]}"</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Row 6: Chapter coverage */}
      <div className="p-6 rounded-2xl border" style={cardStyle}>
        <h3 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>Chapter Coverage</h3>
        <div className="flex items-center gap-6 mb-4">
          <div>
            <span className="text-3xl font-extrabold" style={{ color: "#10b981" }}>{chapter_coverage.coverage_pct}%</span>
            <span className="text-sm ml-2" style={{ color: "var(--text-muted)" }}>
              ({chapter_coverage.covered}/{chapter_coverage.total_chapters} chapters)
            </span>
          </div>
          <div className="flex-1 h-3 rounded-full overflow-hidden" style={{ background: "var(--bg-primary)" }}>
            <div className="h-full rounded-full" style={{ width: `${chapter_coverage.coverage_pct}%`, background: "linear-gradient(90deg, #10b981, #06b6d4)" }} />
          </div>
        </div>
        {chapter_coverage.uncovered_chapters?.length > 0 && (
          <div>
            <p className="text-xs font-bold mb-2" style={{ color: "var(--text-muted)" }}>UNCOVERED CHAPTERS:</p>
            <div className="flex flex-wrap gap-2">
              {chapter_coverage.uncovered_chapters.map((c, i) => (
                <span key={i} className="px-2 py-1 rounded-lg text-xs" style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444" }}>
                  Ch {c.chapter_number}: {c.title}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
