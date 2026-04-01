import { Link } from "react-router";
import { Brain, MessageSquare, BookOpen, GitBranch, Zap, ArrowRight, Sparkles, Star, ArrowLeft } from "lucide-react";
import { ThemeToggle } from "../ui/ThemeToggle";

const features = [
  {
    icon: MessageSquare,
    title: "AI Chat Tutor",
    description: "Context-aware AI that understands your syllabus and explains concepts like a personal tutor",
    color: "#3B82F6",
  },
  {
    icon: BookOpen,
    title: "Smart Notes",
    description: "Auto-generated revision notes with diagrams, formulas, and key takeaways",
    color: "#10B981",
  },
  {
    icon: GitBranch,
    title: "Mind Maps",
    description: "Visual concept maps that help you see the big picture and connect ideas",
    color: "#8B5CF6",
  },
  {
    icon: Zap,
    title: "Adaptive Quizzes",
    description: "Practice questions that adapt to your level and target your weak areas",
    color: "#F59E0B",
  },
];

const stats = [
  { value: "50K+", label: "Active Students" },
  { value: "95%", label: "Score Improvement" },
  { value: "10K+", label: "Questions" },
  { value: "4.9★", label: "App Rating" },
];

const testimonials = [
  {
    name: "Priya Sharma",
    role: "Class 12 · Physics",
    content: "PrepPanda helped me crack JEE Mains. The AI explanations are better than any coaching class I've attended.",
    avatar: "P",
    color: "#3B82F6",
  },
  {
    name: "Arjun Mehta",
    role: "Class 10 · Science",
    content: "Mind maps made organic chemistry click for me. Went from failing to topping my class in 3 months!",
    avatar: "A",
    color: "#10B981",
  },
  {
    name: "Sneha Patel",
    role: "Class 11 · Mathematics",
    content: "The quiz engine knows exactly where I'm weak. My score jumped from 65% to 94% in just two months.",
    avatar: "S",
    color: "#8B5CF6",
  },
];

export function LandingPage() {
  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-primary)' }}>
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass">
        <div className="w-full px-6 lg:px-12 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{
              background: 'var(--gradient-primary)',
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)',
            }}>
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="font-extrabold text-xl tracking-tight" style={{ color: 'var(--text-primary)' }}>
              PrepPanda
            </span>
          </div>
          
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              to="/login"
              className="px-5 py-2 text-[15px] font-medium transition-all duration-200 hover:opacity-80 rounded-lg"
              style={{ color: 'var(--text-secondary)' }}
            >
              Log in
            </Link>
            <Link
              to="/signup"
              className="px-6 py-2.5 rounded-xl text-[15px] font-semibold transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
              style={{
                background: 'var(--gradient-primary)',
                color: '#FFFFFF',
                boxShadow: '0 4px 16px rgba(37, 99, 235, 0.3)',
              }}
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-24 px-6 lg:px-12 overflow-hidden" style={{
        background: 'var(--gradient-hero)',
      }}>
        {/* Decorative orbs */}
        <div className="absolute top-20 left-[10%] w-80 h-80 rounded-full animate-pulse-glow" style={{
          background: 'radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%)',
        }} />
        <div className="absolute bottom-10 right-[12%] w-96 h-96 rounded-full animate-pulse-glow" style={{
          background: 'radial-gradient(circle, rgba(34,211,238,0.12) 0%, transparent 70%)',
          animationDelay: '2s',
        }} />

        <div className="relative max-w-7xl mx-auto">
          <div className="flex flex-col lg:flex-row items-center gap-16">
            {/* Hero Text */}
            <div className="flex-1 animate-fade-up">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8" style={{
                background: 'var(--accent-glow)',
                border: '1px solid var(--accent-primary)',
              }}>
                <Sparkles className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
                <span className="text-xs font-bold tracking-wide uppercase" style={{ color: 'var(--accent-primary)' }}>
                  Powered by AI
                </span>
              </div>
              
              <h1 className="text-6xl lg:text-8xl font-extrabold mb-6 leading-[1.05] tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Master
                <br />
                NCERT
                <br />
                <span className="gradient-text">with AI</span>
              </h1>
              
              <p className="text-lg lg:text-xl mb-10 max-w-xl leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                Your personal AI study companion. Understand concepts deeply, revise smartly, 
                and practice with adaptive quizzes — all in one beautiful workspace.
              </p>
              
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                <Link
                  to="/signup"
                  className="group inline-flex items-center gap-2.5 px-8 py-4 rounded-2xl text-lg font-bold transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
                  style={{
                    background: 'var(--gradient-primary)',
                    color: '#FFFFFF',
                    boxShadow: 'var(--shadow-glow)',
                  }}
                >
                  Start Learning Free
                  <ArrowRight className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-1" />
                </Link>
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl text-lg font-semibold transition-all duration-200 hover:scale-[1.02]"
                  style={{
                    background: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border)',
                    boxShadow: 'var(--shadow-sm)',
                  }}
                >
                  View Demo
                </Link>
              </div>
            </div>

            {/* Hero Visual */}
            <div className="flex-1 w-full max-w-lg animate-fade-up" style={{ animationDelay: '0.2s' }}>
              <div className="relative">
                <div className="rounded-3xl p-8 glass" style={{ boxShadow: 'var(--shadow-xl)' }}>
                  <div className="space-y-4">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'var(--gradient-primary)' }}>
                        <Brain className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <div className="font-bold text-[15px]" style={{ color: 'var(--text-primary)' }}>PrepPanda AI</div>
                        <div className="text-xs font-medium" style={{ color: 'var(--accent-success)' }}>● Online</div>
                      </div>
                    </div>
                    
                    <div className="p-4 rounded-2xl" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>
                      <p className="text-[15px]">Explain the difference between endothermic and exothermic reactions 🧪</p>
                    </div>
                    
                    <div className="p-4 rounded-2xl" style={{ background: 'var(--accent-glow)', border: '1px solid var(--accent-primary)' }}>
                      <p className="text-[15px] font-semibold mb-2" style={{ color: 'var(--accent-primary)' }}>
                        Great question! Here's a clear breakdown:
                      </p>
                      <p className="text-[15px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                        <strong style={{ color: 'var(--text-primary)' }}>Exothermic</strong> reactions release heat (ΔH &lt; 0). 
                        Think combustion: CH₄ + 2O₂ → CO₂ + 2H₂O + heat 🔥
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="absolute -top-4 -right-4 px-4 py-2 rounded-xl animate-float glass" style={{ boxShadow: 'var(--shadow-md)' }}>
                  <span className="text-sm font-bold" style={{ color: 'var(--accent-success)' }}>+32% Score ↑</span>
                </div>
                <div className="absolute -bottom-3 -left-3 px-4 py-2 rounded-xl animate-float glass" style={{ boxShadow: 'var(--shadow-md)', animationDelay: '3s' }}>
                  <span className="text-sm font-bold" style={{ color: 'var(--accent-primary)' }}>🎯 95% Accuracy</span>
                </div>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-24">
            {stats.map((stat, i) => (
              <div key={i} className="text-center p-6 rounded-2xl glass transition-all duration-200 hover:scale-[1.03] cursor-default" style={{ boxShadow: 'var(--shadow-sm)' }}>
                <div className="text-3xl font-extrabold mb-1 gradient-text">{stat.value}</div>
                <div className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-28 px-6 lg:px-12">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16 animate-fade-up">
            <h2 className="text-4xl lg:text-5xl font-extrabold mb-4 tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Everything you need to <span className="gradient-text">excel</span>
            </h2>
            <p className="text-lg max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
              Powerful AI-driven features designed for deep understanding, not just memorization
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div
                  key={index}
                  className="group p-8 rounded-3xl border transition-all duration-300 hover:scale-[1.01] cursor-default"
                  style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)' }}
                  onMouseEnter={(e) => { e.currentTarget.style.boxShadow = `0 8px 32px ${feature.color}20`; e.currentTarget.style.borderColor = feature.color + '40'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; e.currentTarget.style.borderColor = 'var(--border)'; }}
                >
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-5 transition-transform duration-300 group-hover:scale-110"
                    style={{ backgroundColor: feature.color + '15' }}>
                    <Icon className="w-7 h-7" style={{ color: feature.color }} />
                  </div>
                  <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>{feature.title}</h3>
                  <p className="text-[16px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-28 px-6 lg:px-12" style={{ background: 'var(--bg-secondary)' }}>
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl lg:text-5xl font-extrabold mb-4 tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Loved by <span className="gradient-text">students</span>
            </h2>
            <p className="text-lg" style={{ color: 'var(--text-secondary)' }}>
              Join thousands who are transforming their academic performance
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {testimonials.map((t, index) => (
              <div key={index} className="p-8 rounded-3xl border transition-all duration-200 hover:scale-[1.01]"
                style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)' }}>
                <div className="flex items-center gap-1 mb-5">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="w-4 h-4 fill-current" style={{ color: '#F59E0B' }} />
                  ))}
                </div>
                <p className="mb-6 leading-relaxed text-[16px]" style={{ color: 'var(--text-secondary)' }}>
                  "{t.content}"
                </p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm text-white" style={{ backgroundColor: t.color }}>
                    {t.avatar}
                  </div>
                  <div>
                    <div className="font-bold text-[15px]" style={{ color: 'var(--text-primary)' }}>{t.name}</div>
                    <div className="text-sm" style={{ color: 'var(--text-muted)' }}>{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-28 px-6 lg:px-12">
        <div className="max-w-4xl mx-auto text-center">
          <div className="p-14 lg:p-20 rounded-3xl relative overflow-hidden" style={{
            background: 'var(--gradient-primary)', boxShadow: 'var(--shadow-glow)',
          }}>
            <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at 30% 50%, rgba(255,255,255,0.1) 0%, transparent 60%)' }} />
            <div className="relative">
              <h2 className="text-3xl lg:text-5xl font-extrabold text-white mb-4 tracking-tight">Ready to ace your exams?</h2>
              <p className="text-lg text-white/80 mb-10 max-w-xl mx-auto">Start your free learning journey today. No credit card required.</p>
              <Link to="/signup"
                className="inline-flex items-center gap-2.5 px-10 py-4 rounded-2xl text-lg font-bold transition-all duration-200 hover:scale-[1.03] active:scale-[0.98]"
                style={{ background: '#FFFFFF', color: '#2563EB', boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }}>
                Get Started Free <ArrowRight className="w-5 h-5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-10 px-6 lg:px-12 border-t" style={{ borderColor: 'var(--border)' }}>
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'var(--gradient-primary)' }}>
                <Brain className="w-4 h-4 text-white" />
              </div>
              <span className="font-extrabold" style={{ color: 'var(--text-primary)' }}>PrepPanda</span>
            </div>
            <div className="flex items-center gap-8 text-[15px] font-medium" style={{ color: 'var(--text-muted)' }}>
              <a href="#" className="hover:opacity-70 transition-opacity">About</a>
              <a href="#" className="hover:opacity-70 transition-opacity">Features</a>
              <a href="#" className="hover:opacity-70 transition-opacity">Privacy</a>
              <a href="#" className="hover:opacity-70 transition-opacity">Terms</a>
            </div>
            <div className="text-sm" style={{ color: 'var(--text-muted)' }}>© 2026 PrepPanda</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
