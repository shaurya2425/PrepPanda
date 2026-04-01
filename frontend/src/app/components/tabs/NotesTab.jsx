import { useState } from "react";
import { Sparkles, Loader2 } from "lucide-react";

export function NotesTab({ title = 'this chapter' }) {
  const [isGenerated, setIsGenerated] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      setIsGenerated(true);
    }, 2000);
  };

  if (!isGenerated) {
    return (
      <div className="h-full flex items-center justify-center p-6" style={{ background: 'var(--bg-primary)' }}>
        <div className="max-w-md w-full p-10 rounded-3xl border text-center glass animate-fade-up" style={{ borderColor: 'var(--border)', boxShadow: 'var(--shadow-lg)' }}>
          <div className="w-20 h-20 mx-auto rounded-3xl flex items-center justify-center mb-6" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)' }}>
            <Sparkles className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
          </div>
          <h2 className="text-2xl font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Generate Notes</h2>
          <p className="text-[17px] mb-8 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Let AI create comprehensive, easy-to-understand notes for <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</span>.
          </p>
          <button 
            onClick={handleGenerate} disabled={isGenerating}
            className="w-full h-14 rounded-2xl text-[17px] font-bold flex items-center justify-center gap-2 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
            style={{ background: 'var(--gradient-primary)', color: '#FFFFFF', boxShadow: 'var(--shadow-glow)' }}>
            {isGenerating ? <><Loader2 className="w-5 h-5 animate-spin" /> Generating Notes...</> : <><Sparkles className="w-5 h-5" /> Generate Notes</>}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="space-y-8 animate-fade-up">
          <div>
            <h1 className="text-5xl font-bold mb-2 tracking-tight" style={{ color: 'var(--text-primary)' }}>
              {title}
            </h1>
            <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Auto-generated notes · Last updated 2 hours ago
            </div>
          </div>

          {/* Key Concepts */}
          <section>
            <h2 className="text-3xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Key Concepts</h2>
            
            <div className="p-6 rounded-2xl border-l-4 mb-4" style={{
              background: 'var(--accent-glow)',
              borderColor: 'var(--accent-primary)',
            }}>
              <div className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                💡 What is a Chemical Reaction?
              </div>
              <p className="leading-relaxed text-[17px]" style={{ color: 'var(--text-secondary)' }}>
                A process in which substances (reactants) are converted into different substances (products) 
                through breaking and forming of chemical bonds.
              </p>
            </div>

            <ul className="space-y-3 ml-2">
              {[
                "Reactants: Starting substances in a chemical reaction",
                "Products: New substances formed after the reaction",
                "Chemical bonds are broken in reactants and formed in products",
              ].map((item, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="w-1.5 h-1.5 rounded-full mt-2.5 flex-shrink-0" style={{ background: 'var(--accent-primary)' }} />
                  <span className="text-[17px]" style={{ color: 'var(--text-secondary)' }}>{item}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Types */}
          <section>
            <h2 className="text-3xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Types of Chemical Reactions</h2>
            <div className="space-y-4">
              {[
                { title: "1. Combination Reaction", desc: "Two or more substances combine to form a single product.", formula: "A + B → AB", example: "2Mg + O₂ → 2MgO" },
                { title: "2. Decomposition Reaction", desc: "A single compound breaks down into two or more simpler substances.", formula: "AB → A + B", example: "2H₂O → 2H₂ + O₂" },
                { title: "3. Displacement Reaction", desc: "One element displaces another element from its compound.", formula: "A + BC → AC + B", example: "Zn + CuSO₄ → ZnSO₄ + Cu" },
              ].map((type, i) => (
                <div key={i} className="p-6 rounded-2xl border" style={{
                  background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)',
                }}>
                  <h3 className="font-bold mb-2" style={{ color: 'var(--text-primary)' }}>{type.title}</h3>
                  <p className="mb-3 leading-relaxed text-[17px]" style={{ color: 'var(--text-secondary)' }}>{type.desc}</p>
                  <div className="p-3 rounded-xl font-mono text-base mb-2" style={{
                    background: 'var(--bg-tertiary)', color: 'var(--text-primary)',
                  }}>
                    {type.formula}
                  </div>
                  <div className="text-sm" style={{ color: 'var(--text-muted)' }}>Example: {type.example}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Important Points */}
          <section>
            <h2 className="text-3xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Important Points</h2>
            <div className="p-6 rounded-2xl border-l-4" style={{
              background: 'rgba(245, 158, 11, 0.06)', borderColor: 'var(--accent-warning)',
            }}>
              <ul className="space-y-3">
                {[
                  "Law of Conservation of Mass: Mass is neither created nor destroyed",
                  "Chemical equations must be balanced",
                  "Coefficients represent the number of molecules",
                ].map((point, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span>⭐</span>
                    <span className="text-[17px]" style={{ color: 'var(--text-secondary)' }}>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          {/* Visual */}
          <section>
            <h2 className="text-3xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Visual Summary</h2>
            <div className="p-14 rounded-2xl border text-center" style={{
              background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)',
            }}>
              <div className="text-5xl mb-4">📊</div>
              <p style={{ color: 'var(--text-muted)' }}>Diagram: Types of Chemical Reactions</p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
