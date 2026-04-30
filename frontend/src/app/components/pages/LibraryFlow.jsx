import { useState, useEffect, useMemo } from "react";
import { Link, useNavigate } from "react-router";
import { Brain, ArrowLeft, ChevronRight, BookOpen, Loader2 } from "lucide-react";
import { ThemeToggle } from "../ui/ThemeToggle";
import { api } from "@/lib/api";

const getSubjectIcon = (subject) => {
  const s = subject.toLowerCase();
  if (s.includes('physics')) return '⚛️';
  if (s.includes('chemistry')) return '🧪';
  if (s.includes('biology')) return '🧬';
  if (s.includes('math')) return '📐';
  return '📚';
};

const getSubjectColor = (subject) => {
  const s = subject.toLowerCase();
  if (s.includes('physics')) return '#3B82F6';
  if (s.includes('chemistry')) return '#22D3EE';
  if (s.includes('biology')) return '#10B981';
  if (s.includes('math')) return '#F59E0B';
  return '#8B5CF6';
};

export function LibraryFlow() {
  const navigate = useNavigate();
  const [step, setStep] = useState('class');
  
  const [books, setBooks] = useState([]);
  const [isLoadingBooks, setIsLoadingBooks] = useState(true);
  
  const [chapters, setChapters] = useState([]);
  const [isLoadingChapters, setIsLoadingChapters] = useState(false);

  const [selectedGrade, setSelectedGrade] = useState(null);
  const [selectedBook, setSelectedBook] = useState(null);

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        const data = await api.catalog.listBooks();
        setBooks(data);
      } catch (err) {
        console.error("Failed to fetch books:", err);
      } finally {
        setIsLoadingBooks(false);
      }
    };
    fetchBooks();
  }, []);

  const uniqueGrades = useMemo(() => {
    const grades = [...new Set(books.map(b => b.grade))].sort((a, b) => a - b);
    return grades.map(g => ({
      id: g,
      name: `Class ${g}`,
      icon: `${g}️⃣`,
      desc: `${books.filter(b => b.grade === g).length} subjects`
    }));
  }, [books]);

  const subjectsForGrade = useMemo(() => {
    if (!selectedGrade) return [];
    return books.filter(b => b.grade === selectedGrade).map(b => ({
      id: b.book_id,
      name: b.subject.charAt(0).toUpperCase() + b.subject.slice(1),
      title: b.title,
      icon: getSubjectIcon(b.subject),
      color: getSubjectColor(b.subject),
      chapters: `${b.chapter_count} chapters`
    }));
  }, [books, selectedGrade]);

  const handleClassSelect = (gradeId) => {
    setSelectedGrade(gradeId);
    setStep('subject');
  };

  const handleSubjectSelect = async (bookId) => {
    const book = books.find(b => b.book_id === bookId);
    setSelectedBook(book);
    setStep('chapter');
    
    setIsLoadingChapters(true);
    try {
      const data = await api.catalog.listChapters(bookId);
      setChapters(data);
    } catch (err) {
      console.error("Failed to fetch chapters:", err);
    } finally {
      setIsLoadingChapters(false);
    }
  };

  const handleBack = () => {
    if (step === 'subject') { setStep('class'); setSelectedGrade(null); }
    else if (step === 'chapter') { setStep('subject'); setSelectedBook(null); setChapters([]); }
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
              onClick={() => { setStep('class'); setSelectedGrade(null); setSelectedBook(null); }}>
              Class
            </span>
            {selectedGrade && (
              <>
                <ChevronRight className="w-4 h-4" />
                <span className={step === 'subject' ? 'font-bold' : 'cursor-pointer hover:opacity-80'}
                  style={{ color: step === 'subject' ? 'var(--accent-primary)' : 'var(--text-muted)' }}
                  onClick={() => { setStep('subject'); setSelectedBook(null); }}>
                  Class {selectedGrade}
                </span>
              </>
            )}
            {selectedBook && (
              <>
                <ChevronRight className="w-4 h-4" />
                <span className="font-bold" style={{ color: 'var(--accent-primary)' }}>
                  {selectedBook.subject.charAt(0).toUpperCase() + selectedBook.subject.slice(1)}
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

            {isLoadingBooks ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-10 h-10 animate-spin" style={{ color: 'var(--accent-primary)' }} />
              </div>
            ) : uniqueGrades.length === 0 ? (
              <div className="text-center py-20">
                <p className="text-xl" style={{ color: 'var(--text-muted)' }}>No classes available yet.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                {uniqueGrades.map((cls) => (
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
            )}
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
                Class {selectedGrade} · Select your subject to explore chapters
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {subjectsForGrade.map((subject) => (
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
                    <div className="text-[14px] font-medium opacity-70 mb-1" style={{ color: 'var(--text-secondary)' }}>{subject.title}</div>
                    <div className="text-[18px] font-medium" style={{ color: 'var(--text-muted)' }}>{subject.chapters}</div>
                  </div>
                  <ChevronRight className="w-6 h-6 transition-transform duration-200 group-hover:translate-x-1" style={{ color: 'var(--text-muted)' }} />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Chapter Selection */}
        {step === 'chapter' && selectedBook && (
          <div className="animate-fade-up">
            <div className="mb-10">
              <h1 className="text-5xl lg:text-6xl font-extrabold mb-4 tracking-tight" style={{ color: 'var(--text-primary)' }}>
                <span className="gradient-text">{selectedBook.subject.charAt(0).toUpperCase() + selectedBook.subject.slice(1)}</span> Chapters
              </h1>
              <p className="text-xl" style={{ color: 'var(--text-secondary)' }}>
                Class {selectedGrade} · {selectedBook.title}
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
                    <div className="text-[18px] text-white/80 font-medium">Get a complete AI-driven study plan for {selectedBook.subject}</div>
                  </div>
                </div>
              </button>
            </div>

            {/* Chapter List */}
            {isLoadingChapters ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-10 h-10 animate-spin" style={{ color: 'var(--accent-primary)' }} />
              </div>
            ) : chapters.length === 0 ? (
              <div className="text-center py-20">
                <p className="text-xl" style={{ color: 'var(--text-muted)' }}>No chapters ingested yet.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {chapters.map((chapter) => (
                  <Link
                    key={chapter.chapter_id}
                    to={`/study/${chapter.chapter_id}`}
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
                          Chapter {chapter.chapter_number}
                        </div>
                        <h3 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                          {chapter.title}
                        </h3>
                      </div>
                      <ChevronRight className="w-5 h-5 flex-shrink-0 mt-1 transition-transform duration-200 group-hover:translate-x-1" style={{ color: 'var(--text-muted)' }} />
                    </div>

                    <div className="flex gap-4 mt-4">
                       <span className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>{chapter.chunk_count} chunks</span>
                       <span className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>{chapter.image_count} images</span>
                       <span className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>{chapter.pyq_count} PYQs</span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
