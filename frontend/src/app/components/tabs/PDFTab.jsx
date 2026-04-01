import { FileText, ZoomIn, ZoomOut } from "lucide-react";

export function PDFTab() {
  return (
    <div className="h-full flex flex-col items-center justify-center relative" style={{ background: 'var(--bg-primary)' }}>
      {/* Controls */}
      <div className="absolute top-6 right-6 flex items-center gap-2 z-10">
        {[ZoomOut, ZoomIn].map((Icon, i) => (
          <button key={i} className="w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 hover:scale-105"
            style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
            <Icon className="w-4 h-4" style={{ color: 'var(--text-primary)' }} />
          </button>
        ))}
      </div>

      <div className="max-w-4xl w-full mx-auto p-8">
        <div className="rounded-3xl border p-12 min-h-[600px]" style={{
          background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-md)',
        }}>
          <div className="text-center mb-12">
            <FileText className="w-14 h-14 mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>PDF viewer would be displayed here</p>
          </div>
          <div className="space-y-6" style={{ color: 'var(--text-primary)' }}>
            <h1 className="text-3xl font-bold tracking-tight">Chemical Reactions and Equations</h1>
            <h2 className="text-2xl font-bold mt-8">1.1 Introduction</h2>
            <p className="leading-relaxed text-[15px]" style={{ color: 'var(--text-secondary)' }}>
              A chemical reaction is a process in which one or more substances (reactants) are converted 
              into one or more different substances (products). Chemical reactions involve the breaking 
              of chemical bonds in the reactants and the formation of new chemical bonds in the products.
            </p>
            <h2 className="text-2xl font-bold mt-8">1.2 Types of Chemical Reactions</h2>
            <p className="leading-relaxed text-[15px]" style={{ color: 'var(--text-secondary)' }}>
              There are several types of chemical reactions including combination reactions, decomposition 
              reactions, displacement reactions, and double displacement reactions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
