import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { Brain, Mail, Lock, ArrowLeft } from "lucide-react";
import { ThemeToggle } from "../ui/ThemeToggle";

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    navigate("/dashboard");
  };

  const inputStyle = {
    background: 'var(--bg-tertiary)',
    borderColor: 'var(--border)',
    color: 'var(--text-primary)',
  };

  const handleFocus = (e) => {
    e.target.style.borderColor = 'var(--accent-primary)';
    e.target.style.boxShadow = '0 0 0 3px var(--accent-glow)';
  };

  const handleBlur = (e) => {
    e.target.style.borderColor = 'var(--border)';
    e.target.style.boxShadow = 'none';
  };

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--bg-primary)' }}>
      {/* Left Side */}
      <div className="hidden lg:flex lg:w-[45%] items-center justify-center p-16 relative overflow-hidden"
        style={{ background: 'var(--gradient-primary)' }}>
        <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at 30% 30%, rgba(255,255,255,0.15) 0%, transparent 50%)' }} />
        <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at 70% 80%, rgba(0,0,0,0.1) 0%, transparent 50%)' }} />
        <div className="relative text-center text-white">
          <div className="w-20 h-20 rounded-3xl flex items-center justify-center mx-auto mb-8" style={{
            background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(10px)' }}>
            <Brain className="w-10 h-10" />
          </div>
          <h2 className="text-4xl font-extrabold mb-4 tracking-tight">Welcome back</h2>
          <p className="text-lg opacity-90 max-w-sm mx-auto leading-relaxed">
            Continue your learning journey. Your progress is waiting for you.
          </p>
        </div>
      </div>

      {/* Right Side */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 relative">
        <div className="absolute top-5 left-5 flex items-center gap-2">
          <button onClick={() => navigate('/')}
            className="w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-95"
            style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)' }}
            title="Back to Home">
            <ArrowLeft className="w-4 h-4" style={{ color: 'var(--text-primary)' }} />
          </button>
        </div>
        <div className="absolute top-5 right-5">
          <ThemeToggle />
        </div>
        
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-2.5 mb-10 lg:hidden justify-center">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'var(--gradient-primary)' }}>
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="font-extrabold text-xl" style={{ color: 'var(--text-primary)' }}>PrepPanda</span>
          </div>

          <div className="mb-8">
            <h1 className="text-3xl font-extrabold mb-2 tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Log in
            </h1>
            <p className="text-[16px]" style={{ color: 'var(--text-secondary)' }}>
              Don't have an account?{" "}
              <Link to="/signup" className="font-bold" style={{ color: 'var(--accent-primary)' }}>Sign up</Link>
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-[15px] font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Email</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px]" style={{ color: 'var(--text-muted)' }} />
                <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full h-12 pl-12 pr-4 rounded-xl border outline-none transition-all duration-200 text-[15px]"
                  style={inputStyle} onFocus={handleFocus} onBlur={handleBlur} required />
              </div>
            </div>
            <div>
              <label htmlFor="password" className="block text-[15px] font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px]" style={{ color: 'var(--text-muted)' }} />
                <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full h-12 pl-12 pr-4 rounded-xl border outline-none transition-all duration-200 text-[15px]"
                  style={inputStyle} onFocus={handleFocus} onBlur={handleBlur} required />
              </div>
            </div>
            <div className="flex items-center justify-between text-[15px]">
              <label className="flex items-center gap-2 cursor-pointer font-medium" style={{ color: 'var(--text-secondary)' }}>
                <input type="checkbox" className="rounded accent-[var(--accent-primary)]" /> Remember me
              </label>
              <a href="#" className="font-semibold" style={{ color: 'var(--accent-primary)' }}>Forgot password?</a>
            </div>
            <button type="submit"
              className="w-full h-12 rounded-xl font-bold text-[16px] transition-all duration-200 hover:scale-[1.01] active:scale-[0.99]"
              style={{ background: 'var(--gradient-primary)', color: '#FFFFFF', boxShadow: '0 4px 16px rgba(37, 99, 235, 0.3)' }}>
              Log in
            </button>
          </form>

          <div className="mt-8">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t" style={{ borderColor: 'var(--border)' }} />
              </div>
              <div className="relative flex justify-center">
                <span className="px-4 text-sm font-medium" style={{ background: 'var(--bg-primary)', color: 'var(--text-muted)' }}>Or continue with</span>
              </div>
            </div>
            <div className="mt-6 grid grid-cols-2 gap-3">
              {['Google', 'GitHub'].map((p) => (
                <button key={p}
                  className="h-11 rounded-xl border font-semibold text-[15px] transition-all duration-200 hover:scale-[1.01] active:scale-[0.99]"
                  style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
