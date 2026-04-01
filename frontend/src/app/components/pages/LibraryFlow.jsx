import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { Brain, ArrowLeft, ChevronRight, BookOpen } from "lucide-react";
import { ThemeToggle } from "../ui/ThemeToggle";

const classes = [
  { id: '9', name: 'Class 9', icon: '9️⃣', desc: '4 subjects' },
  { id: '10', name: 'Class 10', icon: '🔟', desc: '4 subjects' },
  { id: '11', name: 'Class 11', icon: '1️⃣1️⃣', desc: '4 subjects' },
  { id: '12', name: 'Class 12', icon: '1️⃣2️⃣', desc: '4 subjects' },
];

const subjects = [
  { id: 'physics', name: 'Physics', icon: '⚛️', color: '#3B82F6', chapters: '15 chapters' },
  { id: 'chemistry', name: 'Chemistry', icon: '🧪', color: '#22D3EE', chapters: '16 chapters' },
  { id: 'biology', name: 'Biology', icon: '🧬', color: '#10B981', chapters: '13 chapters' },
  { id: 'mathematics', name: 'Mathematics', icon: '📐', color: '#F59E0B', chapters: '14 chapters' },
];

const chapters = [
  { id: '1', name: 'Chemical Reactions and Equations', progress: 65 },
  { id: '2', name: 'Acids, Bases and Salts', progress: 0 },
  { id: '3', name: 'Metals and Non-metals', progress: 30 },
  { id: '4', name: 'Carbon and its Compounds', progress: 0 },
  { id: '5', name: 'Periodic Classification of Elements', progress: 0 },
  { id: '6', name: 'Life Processes', progress: 0 },
];

export function LibraryFlow() {
  const navigate = useNavigate();
  const [step, setStep] = useState('class');
  const [selectedClass, setSelectedClass] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('');

  const handleClassSelect = (classId) => {
    setSelectedClass(classId);
    setStep('subject');
  };

  const handleSubjectSelect = (subjectId) => {
    setSelectedSubject(subjectId);
    setStep('chapter');
  };

  const handleBack = () => {
    if (step === 'subject') { setStep('class'); setSelectedClass(''); }
    else if (step === 'chapter') { setStep('subject'); setSelectedSubject(''); }
  };

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-primary)' }}>
      {/* Navigation */}
      <nav className="sticky top-0 z-50 glass border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="w-full px-6 lg:px-12 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={step === 'class' ? () => navigate('/dashboard') : handleBack}
              className="w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-95"
              style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)' }}
              title={step === 'class' ? 'Back to Dashboard' : 'Go Back'}
            >
              <ArrowLeft className="w-4 h-4" style={{ color: 'var(--text-primary)' }} />
            </button>
            <Link to="/dashboard" className="flex items-center gap-2.5">
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
          
          {/* Breadcrumb */}
          <div className="hidden md:flex items-center gap-2 text-[15px] font-medium" style={{ color: 'var(--text-muted)' }}>
            <span className={step === 'class' ? 'font-bold' : 'cursor-pointer hover:opacity-80'} 
              style={{ color: step === 'class' ? 'var(--accent-primary)' : 'var(--text-muted)' }}
              onClick={() => { setStep('class'); setSelectedClass(''); setSelectedSubject(''); }}>
              Class
            </span>
            {selectedClass && (
              <>
                <ChevronRight className="w-4 h-4" />
                <span className={step === 'subject' ? 'font-bold' : 'cursor-pointer hover:opacity-80'}
                  style={{ color: step === 'subject' ? 'var(--accent-primary)' : 'var(--text-muted)' }}
                  onClick={() => { setStep('subject'); setSelectedSubject(''); }}>
                  Class {selectedClass}
                </span>
              </>
            )}
            {selectedSubject && (
              <>
                <ChevronRight className="w-4 h-4" />
                <span className="font-bold" style={{ color: 'var(--accent-primary)' }}>
                  Chemistry
                </span>
              </>
            )}
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <div className="w-9 h-9 rounded-xl flex items-center justify-center cursor-pointer transition-all duration-200 hover:scale-105"
              style={{ background: 'var(--gradient-primary)' }}>
              <span className="text-white font-bold text-sm">S</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Content */}
      <div className="px-6 lg:px-12 py-12">
        {/* Class Selection */}
        {step === 'class' && (
          <div className="animate-fade-up">
            <div className="mb-12">
              <h1 className="text-5xl lg:text-6xl font-extrabold mb-4 tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Select your <span className="gradient-text">class</span>
              </h1>
              <p className="text-xl" style={{ color: 'var(--text-secondary)' }}>
                Choose the class you want to study
              </p>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
              {classes.map((cls) => (
                <button
                  key={cls.id}
                  onClick={() => handleClassSelect(cls.id)}
                  className="group p-10 rounded-3xl border text-center transition-all duration-300 hover:scale-[1.03] active:scale-[0.98]"
                  style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)' }}
                  onMouseEnter={(e) => { e.currentTarget.style.boxShadow = 'var(--shadow-glow)'; e.currentTarget.style.borderColor = 'var(--accent-primary)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; e.currentTarget.style.borderColor = 'var(--border)'; }}
                >
                  <div className="text-6xl mb-5 transition-transform duration-300 group-hover:scale-110">{cls.icon}</div>
                  <div className="text-2xl font-extrabold mb-1" style={{ color: 'var(--text-primary)' }}>{cls.name}</div>
                  <div className="text-[17px] font-medium" style={{ color: 'var(--text-muted)' }}>{cls.desc}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Subject Selection */}
        {step === 'subject' && (
          <div className="animate-fade-up">
            <div className="mb-12">
              <h1 className="text-5xl lg:text-6xl font-extrabold mb-4 tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Choose a <span className="gradient-text">subject</span>
              </h1>
              <p className="text-xl" style={{ color: 'var(--text-secondary)' }}>
                Class {selectedClass} · Select your subject to explore chapters
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {subjects.map((subject) => (
                <button
                  key={subject.id}
                  onClick={() => handleSubjectSelect(subject.id)}
                  className="group p-8 rounded-3xl border transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] flex items-center gap-6 text-left"
                  style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)' }}
                  onMouseEnter={(e) => { e.currentTarget.style.boxShadow = `0 8px 32px ${subject.color}25`; e.currentTarget.style.borderColor = subject.color + '50'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; e.currentTarget.style.borderColor = 'var(--border)'; }}
                >
                  <div className="w-20 h-20 rounded-2xl flex items-center justify-center text-4xl flex-shrink-0 transition-transform duration-300 group-hover:scale-110"
                    style={{ backgroundColor: subject.color + '15' }}>
                    {subject.icon}
                  </div>
                  <div className="flex-1">
                    <div className="text-2xl font-extrabold mb-1" style={{ color: 'var(--text-primary)' }}>
                      {subject.name}
                    </div>
                    <div className="text-[18px] font-medium" style={{ color: 'var(--text-muted)' }}>{subject.chapters}</div>
                  </div>
                  <ChevronRight className="w-6 h-6 transition-transform duration-200 group-hover:translate-x-1" style={{ color: 'var(--text-muted)' }} />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Chapter Selection */}
        {step === 'chapter' && (
          <div className="animate-fade-up">
            <div className="mb-10">
              <h1 className="text-5xl lg:text-6xl font-extrabold mb-4 tracking-tight" style={{ color: 'var(--text-primary)' }}>
                <span className="gradient-text">Chemistry</span> Chapters
              </h1>
              <p className="text-xl" style={{ color: 'var(--text-secondary)' }}>
                Class {selectedClass} · Select a chapter to start learning
              </p>
            </div>

            {/* Full Subject CTA */}
            <div className="mb-8">
              <button className="w-full p-8 rounded-3xl text-left transition-all duration-200 hover:scale-[1.005] active:scale-[0.998] relative overflow-hidden"
                style={{ background: 'var(--gradient-primary)', boxShadow: 'var(--shadow-glow)' }}>
                <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at 80% 50%, rgba(255,255,255,0.1) 0%, transparent 60%)' }} />
                <div className="relative flex items-center gap-5">
                  <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.15)' }}>
                    <BookOpen className="w-8 h-8 text-white" />
                  </div>
                  <div>
                    <div className="text-2xl font-extrabold text-white mb-1">Prepare Full Subject</div>
                    <div className="text-[18px] text-white/80 font-medium">Get a complete AI-driven study plan for Chemistry</div>
                  </div>
                </div>
              </button>
            </div>

            {/* Chapter List */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {chapters.map((chapter) => (
                <Link
                  key={chapter.id}
                  to={`/study/${chapter.id}`}
                  className="group p-7 rounded-3xl border transition-all duration-200 hover:scale-[1.01]"
                  style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)' }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--accent-primary)'; e.currentTarget.style.boxShadow = 'var(--shadow-md)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; }}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="text-xs font-bold mb-2 px-2.5 py-1 rounded-lg inline-block" style={{
                        background: 'var(--accent-glow)', color: 'var(--accent-primary)',
                      }}>
                        Chapter {chapter.id}
                      </div>
                      <h3 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                        {chapter.name}
                      </h3>
                    </div>
                    <ChevronRight className="w-5 h-5 flex-shrink-0 mt-1 transition-transform duration-200 group-hover:translate-x-1" style={{ color: 'var(--text-muted)' }} />
                  </div>

                  {chapter.progress > 0 ? (
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-base font-medium" style={{ color: 'var(--text-muted)' }}>Progress</span>
                        <span className="text-base font-bold" style={{ color: 'var(--accent-primary)' }}>{chapter.progress}%</span>
                      </div>
                      <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-tertiary)' }}>
                        <div className="h-full rounded-full" style={{ background: 'var(--gradient-primary)', width: `${chapter.progress}%` }} />
                      </div>
                    </div>
                  ) : (
                    <div className="text-base font-medium" style={{ color: 'var(--text-muted)' }}>Not started yet</div>
                  )}
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
