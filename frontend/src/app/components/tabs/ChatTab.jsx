import { useState, useRef, useEffect } from "react";
import { Send, Sparkles } from "lucide-react";

export function ChatTab({ title = 'this chapter' }) {
  const [messages, setMessages] = useState([
    {
      id: '1',
      type: 'ai',
      content: `Hi! I'm your AI study companion for ${title}. What would you like to explore?`,
      cards: [
        { emoji: '📌', title: 'Quick Start', content: 'Ask me to explain any concept from this chapter' },
        { emoji: '❓', title: 'Practice', content: 'Request practice problems to test your understanding' },
      ]
    }
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    const userMessage = { id: Date.now().toString(), type: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);
    setTimeout(() => {
      const aiMessage = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: "Great question! Let me explain that for you:",
        cards: [
          { emoji: '📚', title: 'Concept', content: 'A chemical reaction involves the transformation of reactants into products through the breaking and forming of chemical bonds.' },
          { emoji: '💡', title: 'Example', content: 'For instance, when magnesium burns in air: 2Mg + O₂ → 2MgO' },
        ]
      };
      setMessages(prev => [...prev, aiMessage]);
      setIsTyping(false);
    }, 1500);
  };

  return (
    <div className="h-full flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      {/* Messages */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-3xl mx-auto px-6 py-8">
          <div className="space-y-6">
            {messages.map((message) => (
              <div key={message.id} className="animate-fade-up">
                {message.type === 'user' ? (
                  <div className="flex justify-end">
                    <div className="max-w-[80%] px-5 py-3.5 rounded-2xl rounded-tr-md text-[17px]" style={{
                      background: 'var(--gradient-primary)',
                      color: '#FFFFFF',
                      boxShadow: '0 2px 8px rgba(37, 99, 235, 0.25)',
                    }}>
                      {message.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-start">
                    <div className="max-w-[85%]">
                      <div className="flex items-start gap-3 mb-3">
                        <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0" style={{
                          background: 'var(--gradient-primary)',
                          boxShadow: '0 2px 8px rgba(37, 99, 235, 0.3)',
                        }}>
                          <Sparkles className="w-4 h-4 text-white" />
                        </div>
                        <div className="flex-1 pt-1 text-[17px]" style={{ color: 'var(--text-primary)' }}>
                          {message.content}
                        </div>
                      </div>
                      
                      {message.cards && (
                        <div className="ml-11 space-y-2.5">
                          {message.cards.map((card, idx) => (
                            <div key={idx} className="p-4 rounded-2xl border transition-all duration-200 hover:scale-[1.005]" style={{
                              background: 'var(--gradient-card)',
                              borderColor: 'var(--border)',
                            }}>
                              <div className="flex items-start gap-3">
                                <span className="text-xl flex-shrink-0">{card.emoji}</span>
                                <div className="flex-1">
                                  <div className="font-semibold text-base mb-1" style={{ color: 'var(--text-primary)' }}>{card.title}</div>
                                  <div className="text-base leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{card.content}</div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            {isTyping && (
              <div className="flex justify-start animate-fade-in">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: 'var(--gradient-primary)' }}>
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <div className="px-5 py-3 rounded-2xl flex items-center gap-1.5" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--accent-primary)', animationDelay: '0ms' }} />
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--accent-primary)', animationDelay: '150ms' }} />
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--accent-primary)', animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      {/* Input */}
      <div className="border-t p-4" style={{ borderColor: 'var(--border)' }}>
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-3 px-5 py-3 rounded-2xl border transition-all duration-200" style={{
            background: 'var(--bg-secondary)',
            borderColor: 'var(--border)',
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent-primary)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-glow)'; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none'; }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask me anything about this chapter..."
              className="flex-1 bg-transparent outline-none border-none text-[17px]"
              style={{ color: 'var(--text-primary)' }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 active:scale-90 disabled:opacity-30"
              style={{
                background: input.trim() ? 'var(--gradient-primary)' : 'var(--bg-tertiary)',
                color: '#FFFFFF',
                boxShadow: input.trim() ? '0 2px 8px rgba(37, 99, 235, 0.3)' : 'none',
              }}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
