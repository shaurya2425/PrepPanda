import { Link, useNavigate } from "react-router";
import { Brain, ArrowRight, AlertTriangle, BookOpen, Flame, Target, Clock, TrendingUp, ArrowLeft } from "lucide-react";
import { ThemeToggle } from "../ui/ThemeToggle";

export function DashboardPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-primary)' }}>
      {/* Navigation */}
      <nav className="sticky top-0 z-50 glass">
        <div className="w-full px-6 lg:px-12 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-95"
              style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)' }}
              title="Back to Home"
            >
              <ArrowLeft className="w-4 h-4" style={{ color: 'var(--text-primary)' }} />
            </button>
            <Link to="/" className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{
                background: 'var(--gradient-primary)',
                boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)',
              }}>
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="font-extrabold text-xl tracking-tight" style={{ color: 'var(--text-primary)' }}>
                PrepPanda
              </span>
            </Link>
          </div>
          
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link 
              to="/admin"
              className="px-5 py-2.5 rounded-xl text-[15px] font-semibold transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
              style={{
                background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
              }}
            >
              <span className="flex items-center gap-2">
                Admin
              </span>
            </Link>
            <Link 
              to="/library"
              className="px-5 py-2.5 rounded-xl text-[15px] font-semibold transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
              style={{
                background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
              }}
            >
              <span className="flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                Browse Library
              </span>
            </Link>
            <div 
              className="w-9 h-9 rounded-xl flex items-center justify-center cursor-pointer transition-all duration-200 hover:scale-105"
              style={{ background: 'var(--gradient-primary)' }}
            >
              <span className="text-white font-bold text-sm">S</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="px-6 lg:px-12 py-10">
        {/* Greeting */}
        <div className="mb-10 animate-fade-up">
          <h1 className="text-4xl lg:text-5xl font-extrabold mb-2 tracking-tight" style={{ color: 'var(--text-primary)' }}>
            Good afternoon, <span className="gradient-text">Shaurya</span>
          </h1>
          <p className="text-lg" style={{ color: 'var(--text-secondary)' }}>
            Let's make today count. Here's your learning overview.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 animate-fade-up" style={{ animationDelay: '0.1s' }}>
          {[
            { icon: Target, label: "Accuracy", value: "85%", color: "#10B981", bg: "rgba(16, 185, 129, 0.1)" },
            { icon: Clock, label: "Study Time", value: "2h 45m", color: "#3B82F6", bg: "rgba(59, 130, 246, 0.1)" },
            { icon: Flame, label: "Day Streak", value: "12", color: "#F59E0B", bg: "rgba(245, 158, 11, 0.1)" },
            { icon: TrendingUp, label: "Questions", value: "24", color: "#8B5CF6", bg: "rgba(139, 92, 246, 0.1)" },
          ].map((stat, i) => {
            const Icon = stat.icon;
            return (
              <div key={i}
                className="p-6 rounded-2xl border transition-all duration-200 hover:scale-[1.02] cursor-default"
                style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)' }}>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: stat.bg }}>
                    <Icon className="w-5 h-5" style={{ color: stat.color }} />
                  </div>
                </div>
                <div className="text-3xl font-extrabold mb-0.5" style={{ color: stat.color }}>{stat.value}</div>
                <div className="text-[15px] font-medium" style={{ color: 'var(--text-muted)' }}>{stat.label}</div>
              </div>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left Column */}
          <div className="lg:col-span-3 space-y-6">
            {/* Continue Learning */}
            <div 
              className="group p-7 rounded-3xl border cursor-pointer transition-all duration-300 hover:scale-[1.005] animate-fade-up"
              style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)', animationDelay: '0.2s' }}
              onClick={() => navigate('/study/chemical-reactions')}
              onMouseEnter={(e) => { e.currentTarget.style.boxShadow = 'var(--shadow-glow)'; e.currentTarget.style.borderColor = 'var(--accent-primary)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; e.currentTarget.style.borderColor = 'var(--border)'; }}
            >
              <div className="flex items-start justify-between mb-5">
                <div className="flex-1">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold mb-3" style={{
                    background: 'var(--accent-glow)', color: 'var(--accent-primary)',
                  }}>
                    <BookOpen className="w-3 h-3" />
                    Continue Learning
                  </div>
                  <h3 className="text-2xl font-bold mb-1.5" style={{ color: 'var(--text-primary)' }}>
                    Chemical Reactions and Equations
                  </h3>
                  <p className="text-[15px]" style={{ color: 'var(--text-secondary)' }}>
                    Class 10 · Science · Chapter 1
                  </p>
                </div>
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 transition-transform duration-300 group-hover:translate-x-1"
                  style={{ background: 'var(--gradient-primary)', boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)' }}>
                  <ArrowRight className="w-5 h-5 text-white" />
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex-1 h-2.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-tertiary)' }}>
                  <div className="h-full rounded-full transition-all duration-500" style={{ background: 'var(--gradient-primary)', width: '65%' }} />
                </div>
                <span className="text-[15px] font-bold" style={{ color: 'var(--accent-primary)' }}>65%</span>
              </div>
            </div>

            {/* Today's Progress */}
            <div className="p-7 rounded-3xl border animate-fade-up"
              style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)', animationDelay: '0.3s' }}>
              <h2 className="text-xl font-bold mb-5" style={{ color: 'var(--text-primary)' }}>Today's Progress</h2>
              <div className="space-y-3">
                {[
                  { title: "Completed Quiz: Balancing Equations", time: "2 hours ago", icon: "✅", score: "8/10" },
                  { title: "Read Notes: Types of Reactions", time: "3 hours ago", icon: "📚", score: null },
                  { title: "AI Chat: Redox Reactions", time: "4 hours ago", icon: "💬", score: null },
                ].map((activity, i) => (
                  <div key={i} className="flex items-center gap-4 p-4 rounded-2xl transition-all duration-200 hover:scale-[1.005] cursor-default"
                    style={{ background: 'var(--bg-tertiary)' }}>
                    <span className="text-xl">{activity.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-[15px] truncate" style={{ color: 'var(--text-primary)' }}>{activity.title}</div>
                      <div className="text-sm" style={{ color: 'var(--text-muted)' }}>{activity.time}</div>
                    </div>
                    {activity.score && (
                      <span className="text-sm font-bold px-3 py-1 rounded-lg" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent-success)' }}>
                        {activity.score}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Accuracy Chart */}
            <div className="p-7 rounded-3xl border animate-fade-up"
              style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)', animationDelay: '0.2s' }}>
              <h2 className="text-xl font-bold mb-5" style={{ color: 'var(--text-primary)' }}>Accuracy Trend</h2>
              <div className="flex items-end gap-2 h-32 mb-4">
                {[60, 72, 65, 80, 75, 85, 90].map((h, i) => (
                  <div key={i} className="flex-1 rounded-t-lg transition-all duration-300 hover:opacity-80 cursor-default" style={{
                    height: `${h}%`, background: i === 6 ? 'var(--gradient-primary)' : 'var(--bg-tertiary)', opacity: i === 6 ? 1 : 0.6,
                  }} />
                ))}
              </div>
              <div className="flex justify-between text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span>
                <span className="font-bold" style={{ color: 'var(--accent-primary)' }}>Today</span>
              </div>
            </div>

            {/* Weak Topics */}
            <div className="p-7 rounded-3xl border animate-fade-up"
              style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)', animationDelay: '0.3s' }}>
              <div className="flex items-center gap-2 mb-5">
                <AlertTriangle className="w-4 h-4" style={{ color: 'var(--accent-warning)' }} />
                <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Needs Practice</h2>
              </div>
              <div className="space-y-3">
                {[
                  { name: "Balancing Equations", subject: "Chemistry", mastery: 52 },
                  { name: "Organic Nomenclature", subject: "Chemistry", mastery: 48 },
                  { name: "Thermodynamics", subject: "Physics", mastery: 55 },
                ].map((topic, i) => (
                  <div key={i} className="p-4 rounded-2xl transition-all duration-200 hover:scale-[1.01] cursor-default"
                    style={{ background: 'var(--bg-tertiary)' }}>
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <div className="font-semibold text-[15px]" style={{ color: 'var(--text-primary)' }}>{topic.name}</div>
                        <div className="text-sm" style={{ color: 'var(--text-muted)' }}>{topic.subject}</div>
                      </div>
                      <span className="text-xs font-bold px-2 py-0.5 rounded-md" style={{
                        background: 'rgba(245, 158, 11, 0.1)', color: 'var(--accent-warning)',
                      }}>{topic.mastery}%</span>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                      <div className="h-full rounded-full" style={{ width: `${topic.mastery}%`, background: 'var(--accent-warning)' }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
