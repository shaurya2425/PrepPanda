import { useState, useRef, useEffect } from "react";
import { FileText, Loader2, Send, Sparkles, X, MessageSquare, PanelRightOpen, PanelRightClose } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";

export function PDFTab({ title, chapterId, pdfUrl }) {
  const [isLoading, setIsLoading] = useState(true);
  const [isChatOpen, setIsChatOpen] = useState(true);
  
  // Chat State
  const [messages, setMessages] = useState([
    {
      id: '1',
      type: 'ai',
      content: `Hi! I'm your AI study companion for ${title || 'this chapter'}. What would you like to explore? Ask me anything, and I'll find the exact concept from the book!`,
      markdown: true
    }
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    
    const userMessage = { id: Date.now().toString(), type: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);
    
    try {
      // Call the SRS endpoint
      const response = await api.srs.ask(chapterId, userMessage.content);
      
      const aiMessage = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: response.markdown,
        markdown: true
      };
      
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: "Sorry, I ran into an error while trying to answer that. Please try again.",
        markdown: false
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  if (!chapterId) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center">
        <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-6 glass border">
          <FileText className="w-10 h-10 text-muted" />
        </div>
        <h2 className="text-2xl font-bold mb-3 text-primary">No Chapter Selected</h2>
        <p className="text-[17px] text-muted max-w-md">Please select a chapter to view its PDF.</p>
      </div>
    );
  }

  if (!pdfUrl) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center">
        <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-6 glass border">
          <FileText className="w-10 h-10 text-muted" />
        </div>
        <h2 className="text-2xl font-bold mb-3 text-primary">No PDF Available</h2>
        <p className="text-[17px] text-muted max-w-md">This chapter does not have a PDF document uploaded yet.</p>
      </div>
    );
  }

  const proxiedPdfUrl = api.catalog.getMediaProxyUrl(pdfUrl);

  return (
    <div className="h-full w-full flex relative overflow-hidden" style={{ background: 'var(--bg-primary)' }}>
      {/* PDF Section */}
      <div className={`flex-1 relative transition-all duration-300 ${isChatOpen ? 'mr-[400px]' : ''}`}>
        {isLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center z-10 glass">
            <Loader2 className="w-8 h-8 animate-spin text-accent mb-4" />
            <p className="text-muted font-medium">Loading PDF document...</p>
          </div>
        )}
        
        {/* Toggle Chat Button (when closed) */}
        {!isChatOpen && (
          <button 
            onClick={() => setIsChatOpen(true)}
            className="absolute top-6 right-6 z-20 w-10 h-10 rounded-xl flex items-center justify-center glass border hover:scale-105 transition-transform"
            style={{ borderColor: 'var(--border)' }}
            title="Open AI Chat"
          >
            <PanelRightOpen className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
          </button>
        )}
        
        <iframe 
          src={`${proxiedPdfUrl}#toolbar=0&navpanes=0`} 
          className="w-full h-full border-none flex-1"
          title={`PDF Viewer - ${title || 'Chapter'}`}
          onLoad={() => setIsLoading(false)}
          style={{ opacity: isLoading ? 0 : 1, transition: 'opacity 0.3s ease' }}
        />
      </div>

      {/* Chat Sidebar */}
      <div 
        className="absolute top-0 right-0 h-full w-[400px] border-l flex flex-col bg-background transition-transform duration-300 shadow-2xl"
        style={{ 
          borderColor: 'var(--border)', 
          transform: isChatOpen ? 'translateX(0)' : 'translateX(100%)',
          background: 'var(--bg-primary)'
        }}
      >
        {/* Chat Header */}
        <div className="h-14 border-b flex items-center justify-between px-5 shrink-0" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-violet-500" />
            <span className="font-semibold text-[15px]" style={{ color: 'var(--text-primary)' }}>PrepPanda AI</span>
          </div>
          <button 
            onClick={() => setIsChatOpen(false)}
            className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
          >
            <PanelRightClose className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 scroll-smooth">
          <div className="space-y-6">
            {messages.map((message) => (
              <div key={message.id} className="animate-fade-up">
                {message.type === 'user' ? (
                  <div className="flex justify-end">
                    <div className="max-w-[85%] px-4 py-2.5 rounded-2xl rounded-tr-md text-[15px]" style={{
                      background: 'var(--gradient-primary)',
                      color: '#FFFFFF',
                      boxShadow: '0 2px 8px rgba(37, 99, 235, 0.25)',
                    }}>
                      {message.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-start">
                    <div className="max-w-[95%]">
                      <div className="flex items-start gap-3">
                        <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5" style={{
                          background: 'var(--gradient-primary)',
                          boxShadow: '0 2px 8px rgba(37, 99, 235, 0.3)',
                        }}>
                          <Sparkles className="w-3.5 h-3.5 text-white" />
                        </div>
                        <div className="flex-1 text-[15px] leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                          {message.markdown ? (
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                p: ({node, ...props}) => <p className="mb-3 last:mb-0" {...props} />,
                                img: ({node, ...props}) => (
                                  <div className="my-4 p-2 rounded-xl border glass" style={{ borderColor: 'var(--border)' }}>
                                    <img 
                                      className="rounded-lg w-full object-contain max-h-[250px]" 
                                      loading="lazy"
                                      {...props}
                                      src={api.catalog.getMediaProxyUrl(props.src)}
                                    />
                                    {props.alt && (
                                      <p className="text-xs text-center mt-2 font-medium" style={{ color: 'var(--text-muted)' }}>
                                        {props.alt}
                                      </p>
                                    )}
                                  </div>
                                ),
                                ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-3 space-y-1" {...props} />,
                                ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-3 space-y-1" {...props} />,
                                li: ({node, ...props}) => <li {...props} />,
                                h3: ({node, ...props}) => <h3 className="font-bold text-lg mt-4 mb-2" {...props} />,
                                h4: ({node, ...props}) => <h4 className="font-semibold text-md mt-3 mb-1" {...props} />,
                                strong: ({node, ...props}) => <strong className="font-semibold text-violet-600 dark:text-violet-400" {...props} />,
                                blockquote: ({node, ...props}) => (
                                  <blockquote className="border-l-4 pl-3 my-3 italic border-violet-500/50 text-muted" {...props} />
                                ),
                              }}
                            >
                              {message.content}
                            </ReactMarkdown>
                          ) : (
                            message.content
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            {isTyping && (
              <div className="flex justify-start animate-fade-in">
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'var(--gradient-primary)' }}>
                    <Sparkles className="w-3.5 h-3.5 text-white" />
                  </div>
                  <div className="px-4 py-2.5 rounded-2xl flex items-center gap-1.5" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                    <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: 'var(--accent-primary)', animationDelay: '0ms' }} />
                    <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: 'var(--accent-primary)', animationDelay: '150ms' }} />
                    <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: 'var(--accent-primary)', animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Chat Input */}
        <div className="border-t p-4 shrink-0" style={{ borderColor: 'var(--border)', background: 'var(--bg-primary)' }}>
          <div className="flex items-center gap-3 px-4 py-2.5 rounded-2xl border transition-all duration-200" style={{
            background: 'var(--bg-secondary)',
            borderColor: 'var(--border)',
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent-glow)'; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none'; }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask a question..."
              className="flex-1 bg-transparent outline-none border-none text-[15px]"
              style={{ color: 'var(--text-primary)' }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isTyping}
              className="w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-200 active:scale-90 disabled:opacity-30 flex-shrink-0"
              style={{
                background: input.trim() ? 'var(--gradient-primary)' : 'var(--bg-tertiary)',
                color: '#FFFFFF',
                boxShadow: input.trim() ? '0 2px 8px rgba(37, 99, 235, 0.3)' : 'none',
              }}
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
