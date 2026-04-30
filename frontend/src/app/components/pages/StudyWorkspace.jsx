import { useState, useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { Brain, ArrowLeft, FileText, MessageSquare, BookOpen, GitBranch, ClipboardCheck, FileQuestion, Loader2 } from "lucide-react";
import { ThemeToggle } from "../ui/ThemeToggle";
import { PDFTab } from "../tabs/PDFTab";
import { ChatTab } from "../tabs/ChatTab";
import { NotesTab } from "../tabs/NotesTab";
import { MindmapTab } from "../tabs/MindmapTab";
import { QuizTab } from "../tabs/QuizTab";
import { PYQTab } from "../tabs/PYQTab";
import { api } from "@/lib/api";

const tabs = [
  { id: 'pdf', label: 'PDF', icon: FileText },
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'notes', label: 'Notes', icon: BookOpen },
  { id: 'mindmap', label: 'Mindmap', icon: GitBranch },
  { id: 'quiz', label: 'Quiz', icon: ClipboardCheck },
  { id: 'pyq', label: 'PYQ', icon: FileQuestion },
];

export function StudyWorkspace() {
  const [activeTab, setActiveTab] = useState('chat');
  const navigate = useNavigate();
  const { chapterId } = useParams();

  const [chapter, setChapter] = useState(null);
  const [book, setBook] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchChapterAndBook = async () => {
      try {
        const chapterData = await api.catalog.getChapter(chapterId);
        setChapter(chapterData);
        if (chapterData?.book_id) {
          const bookData = await api.catalog.getBook(chapterData.book_id);
          setBook(bookData);
        }
      } catch (err) {
        console.error("Failed to fetch chapter/book info:", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchChapterAndBook();
  }, [chapterId]);

  return (
    <div className="h-screen flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      {/* Top Nav */}
      <nav className="border-b flex-shrink-0 glass" style={{ borderColor: 'var(--border)' }}>
        <div className="px-6 lg:px-12 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/library')}
              className="w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-95"
              style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)' }}
              title="Back to Library"
            >
              <ArrowLeft className="w-4 h-4" style={{ color: 'var(--text-primary)' }} />
            </button>
            <div>
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-muted" />
                  <span className="text-sm text-muted">Loading chapter...</span>
                </div>
              ) : (
                <>
                  <div className="font-bold text-[16px]" style={{ color: 'var(--text-primary)' }}>
                    {chapter?.title || `Chapter ${chapterId}`}
                  </div>
                  <div className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                    {book ? `Class ${book.grade} · ${book.subject} · Chapter ${chapter?.chapter_number}` : 'Unknown Book'}
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <div className="w-9 h-9 rounded-xl flex items-center justify-center cursor-pointer transition-all duration-200 hover:scale-105"
              style={{ background: 'var(--gradient-primary)' }}>
              <span className="text-white font-bold text-sm">S</span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center justify-center border-t px-4" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-1 py-1.5 overflow-x-auto no-scrollbar max-w-full">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className="px-6 py-2.5 rounded-xl flex items-center gap-2 transition-all duration-200 relative whitespace-nowrap"
                  style={{
                    backgroundColor: isActive ? 'var(--accent-glow)' : 'transparent',
                    color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)',
                    fontWeight: isActive ? 700 : 500,
                  }}>
                  <Icon className="w-4 h-4" />
                  <span className="text-[15px]">{tab.label}</span>
                  {isActive && (
                    <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full" style={{ background: 'var(--gradient-primary)' }} />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'pdf' && <PDFTab title={chapter?.title} chapterId={chapterId} />}
        {activeTab === 'chat' && <ChatTab title={chapter?.title} chapterId={chapterId} />}
        {activeTab === 'notes' && <NotesTab title={chapter?.title} chapterId={chapterId} />}
        {activeTab === 'mindmap' && <MindmapTab title={chapter?.title} chapterId={chapterId} />}
        {activeTab === 'quiz' && <QuizTab title={chapter?.title} chapterId={chapterId} />}
        {activeTab === 'pyq' && <PYQTab title={chapter?.title} chapterId={chapterId} />}
      </div>
    </div>
  );
}
