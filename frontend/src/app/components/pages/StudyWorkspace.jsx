import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { Brain, ArrowLeft, FileText, MessageSquare, BookOpen, GitBranch, ClipboardCheck } from "lucide-react";
import { ThemeToggle } from "../ui/ThemeToggle";
import { PDFTab } from "../tabs/PDFTab";
import { ChatTab } from "../tabs/ChatTab";
import { NotesTab } from "../tabs/NotesTab";
import { MindmapTab } from "../tabs/MindmapTab";
import { QuizTab } from "../tabs/QuizTab";

const tabs = [
  { id: 'pdf', label: 'PDF', icon: FileText },
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'notes', label: 'Notes', icon: BookOpen },
  { id: 'mindmap', label: 'Mindmap', icon: GitBranch },
  { id: 'quiz', label: 'Quiz', icon: ClipboardCheck },
];

export function StudyWorkspace() {
  const [activeTab, setActiveTab] = useState('chat');
  const navigate = useNavigate();
  const { chapterId } = useParams();

  const mockChapters = {
    '1': { title: 'Chemical Reactions and Equations', meta: 'Class 10 · Chemistry · Chapter 1' },
    '2': { title: 'Acids, Bases and Salts', meta: 'Class 10 · Chemistry · Chapter 2' },
    '3': { title: 'Metals and Non-metals', meta: 'Class 10 · Chemistry · Chapter 3' },
    '4': { title: 'Carbon and its Compounds', meta: 'Class 10 · Chemistry · Chapter 4' },
    '5': { title: 'Periodic Classification of Elements', meta: 'Class 10 · Chemistry · Chapter 5' },
    '6': { title: 'Life Processes', meta: 'Class 10 · Biology · Chapter 6' },
  };

  const chapterInfo = mockChapters[chapterId] || { title: `Chapter ${chapterId}`, meta: `Class 10 · Subject · Chapter ${chapterId}` };

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
              <div className="font-bold text-[16px]" style={{ color: 'var(--text-primary)' }}>
                {chapterInfo.title}
              </div>
              <div className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                {chapterInfo.meta}
              </div>
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
          <div className="flex items-center gap-1 py-1.5">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className="px-6 py-2.5 rounded-xl flex items-center gap-2 transition-all duration-200 relative"
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
        {activeTab === 'pdf' && <PDFTab title={chapterInfo.title} />}
        {activeTab === 'chat' && <ChatTab title={chapterInfo.title} />}
        {activeTab === 'notes' && <NotesTab title={chapterInfo.title} />}
        {activeTab === 'mindmap' && <MindmapTab title={chapterInfo.title} />}
        {activeTab === 'quiz' && <QuizTab title={chapterInfo.title} />}
      </div>
    </div>
  );
}
