import { useState, useEffect } from "react";
import {
  LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  CartesianGrid, AreaChart, Area, BarChart, Bar
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

export function AnalyticsTab({ title, chapterId }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (chapterId) {
      fetchAnalytics();
    }
  }, [chapterId]);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.analysis.getChapterPatterns(chapterId);
      setReport(data);
    } catch (err) {
      setError(err.message || "Failed to fetch analytics");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full w-full flex items-center justify-center">
        <div className="w-8 h-8 border-4 rounded-full animate-spin" style={{ borderColor: "var(--border)", borderTopColor: "var(--accent-primary)" }} />
        <span className="ml-3 font-semibold" style={{ color: "var(--text-secondary)" }}>Crunching numbers…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-500">
          {error}
        </div>
      </div>
    );
  }

  if (!report) return null;

  const { summary, year_frequency, marks_distribution, exam_breakdown, topic_hotspots, repetition_clusters, difficulty_curve } = report;

  return (
    <div className="h-full overflow-y-auto custom-scrollbar bg-slate-50/50 dark:bg-slate-900/50" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-7xl mx-auto p-6 lg:p-10 space-y-8">
        
        {/* Header */}
        <div>
          <h2 className="text-3xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>Analytics & Insights</h2>
          <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Data-driven patterns for {title}</p>
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
                <div className="text-3xl font-extrabold" style={{ color: s.color }}>{s.value}</div>
              </div>
            );
          })}
        </div>

        {/* Row 1: Year frequency + Marks distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 p-6 rounded-2xl border" style={cardStyle}>
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
              <TrendingUp className="w-5 h-5 text-indigo-500" />
              Year-wise Question Frequency
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={year_frequency}>
                <defs>
                  <linearGradient id="colorFreq" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: "var(--text-muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="value" stroke="#6366f1" fill="url(#colorFreq)" strokeWidth={3} name="Questions" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="p-6 rounded-2xl border flex flex-col" style={cardStyle}>
            <h3 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>Marks Weightage</h3>
            <div className="flex-1 min-h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={marks_distribution} dataKey="value" nameKey="label" cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={5} label={({ label, percent }) => `${label} (${(percent * 100).toFixed(0)}%)`}>
                    {marks_distribution.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Row 2: Exam breakdown & Difficulty */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="p-6 rounded-2xl border" style={cardStyle}>
            <h3 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>Exam Board Breakdown</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={exam_breakdown}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: "var(--text-muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(0,0,0,0.05)' }} />
                <Bar dataKey="value" name="Questions" radius={[6, 6, 0, 0]}>
                  {exam_breakdown.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {difficulty_curve.length > 0 && (
            <div className="p-6 rounded-2xl border" style={cardStyle}>
              <h3 className="text-lg font-bold mb-4" style={{ color: "var(--text-primary)" }}>Difficulty Curve (Avg Marks / Year)</h3>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={difficulty_curve}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="year" tick={{ fill: "var(--text-muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  <Line type="monotone" dataKey="avg_marks" stroke="#f59e0b" strokeWidth={3} name="Avg Marks" dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Row 3: Hotspots and Repetitions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Topic hotspots table */}
          {topic_hotspots.length > 0 && (
            <div className="p-6 rounded-2xl border" style={cardStyle}>
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
                <Flame className="w-5 h-5 text-red-500" />
                Topic Hotspots
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ borderBottom: "2px solid var(--border)" }}>
                      {["Section", "Freq", "Avg Marks", "Trend"].map((h) => (
                        <th key={h} className="py-3 px-3 text-left font-bold" style={{ color: "var(--text-muted)" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {topic_hotspots.slice(0, 8).map((t, i) => (
                      <tr key={i} className="transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50" style={{ borderBottom: "1px solid var(--border)" }}>
                        <td className="py-3 px-3 font-semibold" style={{ color: "var(--text-primary)" }}>{t.section_title}</td>
                        <td className="py-3 px-3">
                          <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-indigo-500/10 text-indigo-500">{t.frequency}</span>
                        </td>
                        <td className="py-3 px-3 font-medium" style={{ color: "var(--text-secondary)" }}>{t.avg_marks || "—"}</td>
                        <td className="py-3 px-3">
                          <span className={`px-2.5 py-1 rounded-md text-xs font-bold ${t.trend === "rising" ? "text-emerald-500 bg-emerald-500/10" : t.trend === "declining" ? "text-red-500 bg-red-500/10" : "text-amber-500 bg-amber-500/10"}`}>
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

          {/* Repetition clusters */}
          {repetition_clusters.length > 0 && (
            <div className="p-6 rounded-2xl border" style={cardStyle}>
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
                <Repeat className="w-5 h-5 text-cyan-500" />
                Repeated Topics
              </h3>
              <div className="space-y-4">
                {repetition_clusters.slice(0, 5).map((r, i) => (
                  <div key={i} className="p-4 rounded-xl border border-transparent hover:border-cyan-500/20 transition-all" style={{ background: "var(--bg-primary)" }}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-[15px]" style={{ color: "var(--text-primary)" }}>{r.topic}</span>
                      <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-cyan-500/10 text-cyan-500">
                        {r.year_count} years · {r.question_count} Qs
                      </span>
                    </div>
                    <p className="text-sm font-medium mb-1" style={{ color: "var(--text-secondary)" }}>Years: {r.years.join(", ")}</p>
                    {r.sample_questions[0] && (
                      <p className="text-sm italic mt-2 line-clamp-2" style={{ color: "var(--text-muted)" }}>"{r.sample_questions[0]}"</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
