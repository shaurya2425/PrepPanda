import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router";
import { Brain, ArrowLeft, BookOpen, FileText, Trash2, Plus, Upload, BarChart3 } from "lucide-react";
import { api } from "../../../lib/api";
import { ThemeToggle } from "../ui/ThemeToggle";
import { PatternsTab } from "../tabs/PatternsTab";

export function AdminPage() {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState("books");
  
  // Data state
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Modals state
  const [isBookModalOpen, setIsBookModalOpen] = useState(false);
  const [isPYQModalOpen, setIsPYQModalOpen] = useState(false);

  useEffect(() => {
    // Check if auth token exists and is valid
    const checkAuth = async () => {
      const auth = localStorage.getItem("adminAuth");
      if (auth) {
        try {
          await api.admin.verify();
          setIsAuthenticated(true);
        } catch (err) {
          localStorage.removeItem("adminAuth");
          setIsAuthenticated(false);
        }
      }
    };
    checkAuth();
  }, []);

  const fetchBooks = async () => {
    try {
      setLoading(true);
      const data = await api.catalog.listBooks();
      setBooks(data);
    } catch (err) {
      setError(err.message || "Failed to fetch books");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchBooks();
    }
  }, [isAuthenticated]);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  if (!isAuthenticated) {
    return <AdminLogin onLogin={handleLoginSuccess} />;
  }

  const handleDeleteBook = async (bookId) => {
    if (!window.confirm("Are you sure you want to delete this book? This will cascade to chapters and PYQs.")) return;
    try {
      await api.books.delete(bookId);
      await fetchBooks();
    } catch (err) {
      alert("Failed to delete: " + err.message);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-primary)' }}>
      {/* Navigation */}
      <nav className="sticky top-0 z-50 glass">
        <div className="w-full px-6 lg:px-12 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/dashboard')}
              className="w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 hover:scale-105"
              style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)' }}
            >
              <ArrowLeft className="w-4 h-4" style={{ color: 'var(--text-primary)' }} />
            </button>
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'var(--gradient-primary)' }}>
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="font-extrabold text-xl tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Admin Panel
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="px-6 lg:px-12 py-10 max-w-7xl mx-auto">
        {/* Tabs */}
        <div className="flex gap-4 mb-8">
          <button 
            className={`px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all ${activeTab === 'books' ? 'scale-[1.02]' : 'opacity-70 hover:opacity-100'}`}
            style={{ background: activeTab === 'books' ? 'var(--gradient-primary)' : 'var(--bg-tertiary)', color: activeTab === 'books' ? '#fff' : 'var(--text-primary)' }}
            onClick={() => setActiveTab("books")}
          >
            <BookOpen className="w-5 h-5" /> Books
          </button>
          <button 
            className={`px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all ${activeTab === 'pyqs' ? 'scale-[1.02]' : 'opacity-70 hover:opacity-100'}`}
            style={{ background: activeTab === 'pyqs' ? 'var(--gradient-primary)' : 'var(--bg-tertiary)', color: activeTab === 'pyqs' ? '#fff' : 'var(--text-primary)' }}
            onClick={() => setActiveTab("pyqs")}
          >
            <FileText className="w-5 h-5" /> PYQs
          </button>
          <button 
            className={`px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all ${activeTab === 'patterns' ? 'scale-[1.02]' : 'opacity-70 hover:opacity-100'}`}
            style={{ background: activeTab === 'patterns' ? 'var(--gradient-primary)' : 'var(--bg-tertiary)', color: activeTab === 'patterns' ? '#fff' : 'var(--text-primary)' }}
            onClick={() => setActiveTab("patterns")}
          >
            <BarChart3 className="w-5 h-5" /> Analytics
          </button>
        </div>

        {error && (
          <div className="p-4 mb-6 rounded-xl border border-red-500/30 bg-red-500/10 text-red-500">
            {error}
          </div>
        )}

        {/* Tab Content */}
        {activeTab === "books" && (
          <div className="animate-fade-up">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Manage Books</h2>
              <button 
                onClick={() => setIsBookModalOpen(true)}
                className="px-4 py-2 rounded-xl flex items-center gap-2 font-bold text-white transition-all hover:scale-[1.02]"
                style={{ background: 'var(--gradient-primary)' }}
              >
                <Plus className="w-4 h-4" /> Add Book
              </button>
            </div>

            {loading ? (
              <div className="text-center py-10" style={{ color: 'var(--text-secondary)' }}>Loading...</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {books.map(book => (
                  <div key={book.book_id} className="p-6 rounded-2xl border" style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)' }}>
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>{book.title}</h3>
                        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>Grade {book.grade} • {book.subject}</p>
                      </div>
                      <button onClick={() => handleDeleteBook(book.book_id)} className="p-2 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <p className="text-sm font-semibold" style={{ color: 'var(--accent-primary)' }}>
                      {book.chapter_count} Chapters
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "patterns" && (
          <div className="animate-fade-up">
            <PatternsTab books={books} />
          </div>
        )}

        {activeTab === "pyqs" && (
          <div className="animate-fade-up">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Manage PYQs</h2>
              <button 
                onClick={() => setIsPYQModalOpen(true)}
                className="px-4 py-2 rounded-xl flex items-center gap-2 font-bold text-white transition-all hover:scale-[1.02]"
                style={{ background: 'var(--gradient-primary)' }}
              >
                <Upload className="w-4 h-4" /> Ingest PYQs
              </button>
            </div>
            <PYQList books={books} />
          </div>
        )}
      </div>

      {isBookModalOpen && (
        <AddBookModal onClose={() => setIsBookModalOpen(false)} onAdded={() => { setIsBookModalOpen(false); fetchBooks(); }} />
      )}
      
      {isPYQModalOpen && (
        <IngestPYQModal books={books} onClose={() => setIsPYQModalOpen(false)} />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function AdminLogin({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    // Create Basic Auth token
    const token = btoa(`${username}:${password}`);
    localStorage.setItem("adminAuth", token);

    try {
      await api.admin.verify();
      onLogin();
    } catch (err) {
      localStorage.removeItem("adminAuth");
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ background: 'var(--bg-primary)' }}>
      <div className="w-full max-w-md p-8 rounded-3xl border shadow-xl" style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'var(--gradient-primary)' }}>
            <Brain className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold" style={{ color: 'var(--text-primary)' }}>Admin Login</h1>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-500 text-sm font-semibold text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: 'var(--text-secondary)' }}>Username</label>
            <input 
              type="text" 
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              required
              className="w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500/50" 
              style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }} 
            />
          </div>
          <div>
            <label className="block text-sm font-bold mb-2" style={{ color: 'var(--text-secondary)' }}>Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required
              className="w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500/50" 
              style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }} 
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-3 mt-4 rounded-xl font-bold text-white transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
            style={{ background: 'var(--gradient-primary)' }}
          >
            {loading ? "Authenticating..." : "Login"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button 
            onClick={() => navigate('/dashboard')}
            className="text-sm font-semibold hover:underline"
            style={{ color: 'var(--text-secondary)' }}
          >
            &larr; Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}

function AddBookModal({ onClose, onAdded }) {
  const [title, setTitle] = useState("");
  const [grade, setGrade] = useState("");
  const [subject, setSubject] = useState("");
  const [loading, setLoading] = useState(false);

  // Chapters state for one-shot ingest
  const [chapters, setChapters] = useState([{ number: 1, title: "", file: null }]);

  const handleAddChapter = () => {
    setChapters([...chapters, { number: chapters.length + 1, title: "", file: null }]);
  };

  const handleChapterChange = (index, field, value) => {
    const newChapters = [...chapters];
    newChapters[index][field] = value;
    setChapters(newChapters);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const bookMeta = { title, grade: parseInt(grade), subject };
      
      // Separate metadata from files
      const chaptersMeta = chapters.map(c => ({ number: c.number, title: c.title }));
      const pdfFiles = chapters.map(c => c.file);
      
      if (pdfFiles.some(f => !f)) {
        alert("Please select a PDF file for all chapters.");
        setLoading(false);
        return;
      }

      await api.books.ingestBook(bookMeta, chaptersMeta, pdfFiles);
      onAdded();
    } catch (err) {
      alert("Failed to create book: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-3xl p-8 border" style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)' }}>
        <h2 className="text-2xl font-bold mb-6" style={{ color: 'var(--text-primary)' }}>Ingest New Book</h2>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>Title</label>
              <input type="text" required value={title} onChange={e => setTitle(e.target.value)} className="w-full px-4 py-3 rounded-xl border focus:outline-none" style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>Subject</label>
              <input type="text" required value={subject} onChange={e => setSubject(e.target.value)} className="w-full px-4 py-3 rounded-xl border focus:outline-none" style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>Grade</label>
              <input type="number" required min="1" max="12" value={grade} onChange={e => setGrade(e.target.value)} className="w-full px-4 py-3 rounded-xl border focus:outline-none" style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-4">
              <label className="block text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Chapters</label>
              <button type="button" onClick={handleAddChapter} className="text-sm font-bold flex items-center gap-1" style={{ color: 'var(--accent-primary)' }}>
                <Plus className="w-4 h-4" /> Add Chapter
              </button>
            </div>
            <div className="space-y-4">
              {chapters.map((chapter, i) => (
                <div key={i} className="flex gap-3 items-center p-4 rounded-xl border" style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)' }}>
                  <input type="number" min="1" required value={chapter.number} onChange={e => handleChapterChange(i, 'number', parseInt(e.target.value))} className="w-16 px-3 py-2 rounded-lg border text-center" placeholder="No." style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
                  <input type="text" required value={chapter.title} onChange={e => handleChapterChange(i, 'title', e.target.value)} className="flex-1 px-3 py-2 rounded-lg border" placeholder="Chapter Title" style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
                  <input type="file" accept="application/pdf" required onChange={e => handleChapterChange(i, 'file', e.target.files[0])} className="w-64 text-sm file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-8">
            <button type="button" onClick={onClose} className="px-5 py-2.5 rounded-xl font-semibold" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}>Cancel</button>
            <button type="submit" disabled={loading} className="px-5 py-2.5 rounded-xl font-bold text-white disabled:opacity-50" style={{ background: 'var(--gradient-primary)' }}>
              {loading ? "Ingesting..." : "Ingest Book"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function IngestPYQModal({ books, onClose }) {
  const [bookId, setBookId] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!bookId || !file) return;
    setLoading(true);
    try {
      const res = await api.pyqs.ingestFile(bookId, file);
      alert(`Successfully inserted ${res.inserted} PYQs. Skipped: ${res.skipped}`);
      onClose();
    } catch (err) {
      alert("Failed to ingest PYQs: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-3xl p-8 border" style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)' }}>
        <h2 className="text-2xl font-bold mb-6" style={{ color: 'var(--text-primary)' }}>Ingest PYQs</h2>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>Select Book</label>
            <select required value={bookId} onChange={e => setBookId(e.target.value)} className="w-full px-4 py-3 rounded-xl border focus:outline-none" style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
              <option value="">-- Choose Book --</option>
              {books.map(b => (
                <option key={b.book_id} value={b.book_id}>{b.title} (Grade {b.grade})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>PYQ Text File</label>
            <input type="file" accept=".txt" required onChange={e => setFile(e.target.files[0])} className="w-full px-4 py-3 rounded-xl border bg-white" style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)' }} />
            <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>Upload a plain text file following the ---Q block format.</p>
          </div>

          <div className="flex justify-end gap-3 mt-8">
            <button type="button" onClick={onClose} className="px-5 py-2.5 rounded-xl font-semibold" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}>Cancel</button>
            <button type="submit" disabled={loading} className="px-5 py-2.5 rounded-xl font-bold text-white disabled:opacity-50" style={{ background: 'var(--gradient-primary)' }}>
              {loading ? "Ingesting..." : "Upload PYQs"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function PYQList({ books }) {
  const [selectedBook, setSelectedBook] = useState("");
  const [pyqs, setPyqs] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedBook) fetchPyqs();
  }, [selectedBook]);

  const fetchPyqs = async () => {
    setLoading(true);
    try {
      const data = await api.catalog.listBookPyqs(selectedBook, { limit: 50 });
      setPyqs(data.items || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this PYQ?")) return;
    try {
      await api.pyqs.delete(id);
      fetchPyqs();
    } catch (err) {
      alert("Error deleting: " + err.message);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <select 
          value={selectedBook} 
          onChange={e => setSelectedBook(e.target.value)} 
          className="w-full max-w-sm px-4 py-3 rounded-xl border focus:outline-none" 
          style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
        >
          <option value="">Select a book to view PYQs</option>
          {books.map(b => (
            <option key={b.book_id} value={b.book_id}>{b.title}</option>
          ))}
        </select>
      </div>

      {loading && <div className="text-center py-8">Loading...</div>}
      
      {!loading && selectedBook && pyqs.length === 0 && (
        <div className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>No PYQs found for this book.</div>
      )}

      <div className="space-y-4">
        {pyqs.map(pyq => (
          <div key={pyq.pyq_id} className="p-5 rounded-2xl border" style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)' }}>
            <div className="flex justify-between items-start gap-4 mb-3">
              <div className="flex gap-2">
                <span className="px-2 py-1 text-xs font-bold rounded" style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#3B82F6' }}>
                  {pyq.year || "N/A"}
                </span>
                {pyq.marks && (
                  <span className="px-2 py-1 text-xs font-bold rounded" style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#F59E0B' }}>
                    {pyq.marks} Marks
                  </span>
                )}
              </div>
              <button onClick={() => handleDelete(pyq.pyq_id)} className="p-1.5 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500/20">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
            <p className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Q: {pyq.question}</p>
            {pyq.answer && (
              <p className="text-sm border-l-2 pl-3" style={{ color: 'var(--text-secondary)', borderColor: 'var(--border)' }}>
                {pyq.answer}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
