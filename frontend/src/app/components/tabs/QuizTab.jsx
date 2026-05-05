import { useState } from "react";
import { CheckCircle2, XCircle, ArrowRight, ArrowLeft, Sparkles, Loader2, RefreshCw, LogOut, BarChart3, Target, TrendingUp, AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";

export function QuizTab({ title = 'this chapter', chapterId }) {
  // Phase: 'idle' | 'active' | 'review' | 'analysis'
  const [phase, setPhase] = useState('idle');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);

  const [quizData, setQuizData] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});   // { questionId: selectedIdx }
  const [analytics, setAnalytics] = useState(null);
  const [reviewIdx, setReviewIdx] = useState(0);

  const question = quizData[currentQuestion];

  const handleGenerate = async (forceNew = false) => {
    setIsGenerating(true);
    setError(null);
    try {
      const data = await api.quiz.generate(chapterId, { forceNew });
      if (data?.length > 0) {
        setQuizData(data);
        setCurrentQuestion(0);
        setAnswers({});
        setAnalytics(null);
        setPhase('active');
      } else {
        setError("Could not generate quiz from available content.");
      }
    } catch (err) {
      console.error("Quiz generation failed:", err);
      setError("Failed to generate quiz. Please make sure the chapter has been fully ingested.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerateAdaptive = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const data = await api.quiz.generateAdaptive(chapterId);
      if (data?.length > 0) {
        setQuizData(data);
        setCurrentQuestion(0);
        setAnswers({});
        setAnalytics(null);
        setPhase('active');
      } else {
        setError("Could not generate adaptive quiz.");
      }
    } catch (err) {
      console.error("Adaptive quiz generation failed:", err);
      setError("Failed to generate adaptive quiz.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleQuit = () => {
    setPhase('idle');
    setQuizData([]);
    setCurrentQuestion(0);
    setAnswers({});
    setAnalytics(null);
    setError(null);
  };

  const handleSelectAnswer = (idx) => {
    setAnswers(prev => ({ ...prev, [question.id]: idx }));
  };

  const handleSubmitQuiz = async () => {
    setIsGenerating(true);
    try {
      const answerList = quizData.map(q => ({
        question_id: q.id,
        selected: answers[q.id] ?? -1,
      }));
      const result = await api.quiz.submit(chapterId, answerList);
      setAnalytics(result);
      setPhase('analysis');
    } catch (err) {
      console.error("Quiz submit failed:", err);
      setError("Failed to submit quiz.");
    } finally {
      setIsGenerating(false);
    }
  };

  // ── IDLE SCREEN ──
  if (phase === 'idle') {
    return (
      <div className="h-full flex items-center justify-center p-6" style={{ background: 'var(--bg-primary)' }}>
        <div className="max-w-md w-full p-10 rounded-3xl border text-center glass animate-fade-up" style={{ borderColor: 'var(--border)', boxShadow: 'var(--shadow-lg)' }}>
          <div className="w-20 h-20 mx-auto rounded-3xl flex items-center justify-center mb-6" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)' }}>
            <Sparkles className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
          </div>
          <h2 className="text-2xl font-bold mb-3" style={{ color: 'var(--text-primary)' }}>Generate Adaptive Quiz</h2>
          <p className="text-[17px] mb-8 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Let AI create a custom quiz to test your mastery of <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</span>.
          </p>
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-sm font-medium">{error}</div>
          )}
          <button onClick={() => handleGenerate(false)} disabled={isGenerating}
            className="w-full h-14 rounded-2xl text-[17px] font-bold flex items-center justify-center gap-2 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
            style={{ background: 'var(--gradient-primary)', color: '#FFFFFF', boxShadow: 'var(--shadow-glow)' }}>
            {isGenerating ? <><Loader2 className="w-5 h-5 animate-spin" /> Generating Quiz...</> : <><Sparkles className="w-5 h-5" /> Generate Quiz</>}
          </button>
        </div>
      </div>
    );
  }

  // ── ACTIVE QUIZ ──
  if (phase === 'active') {
    const allAnswered = quizData.every(q => answers[q.id] !== undefined);
    const answeredCount = Object.keys(answers).length;
    return (
      <div className="h-full overflow-auto flex items-center justify-center p-6" style={{ background: 'var(--bg-primary)' }}>
        <div className="w-full max-w-3xl animate-fade-up">
          {/* Progress */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <span className="text-base font-medium" style={{ color: 'var(--text-secondary)' }}>
                Question {currentQuestion + 1} of {quizData.length}
              </span>
              <span className="text-sm font-semibold px-3 py-1 rounded-lg" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>
                {question?.topic}
              </span>
            </div>
            <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-tertiary)' }}>
              <div className="h-full rounded-full transition-all duration-500" style={{
                background: 'var(--gradient-primary)',
                width: `${((currentQuestion + 1) / quizData.length) * 100}%`
              }} />
            </div>
            <div className="flex gap-1.5 mt-3">
              {quizData.map((q, i) => (
                <button key={q.id} onClick={() => setCurrentQuestion(i)}
                  className="flex-1 h-2 rounded-full transition-all duration-200"
                  style={{
                    background: answers[q.id] !== undefined
                      ? 'var(--accent-primary)' : i === currentQuestion
                      ? 'var(--text-muted)' : 'var(--bg-tertiary)',
                    opacity: i === currentQuestion ? 1 : 0.7,
                  }} />
              ))}
            </div>
          </div>

          {/* Question Card */}
          <div className="p-8 rounded-3xl border mb-6" style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)' }}>
            <h2 className="text-2xl font-bold mb-8 leading-relaxed" style={{ color: 'var(--text-primary)' }}>
              {question?.question}
            </h2>
            <div className="space-y-3">
              {question?.options.map((option, index) => {
                const isSelected = answers[question.id] === index;
                return (
                  <button key={index} onClick={() => handleSelectAnswer(index)}
                    className="w-full text-left p-5 rounded-2xl border transition-all duration-200 hover:scale-[1.005]"
                    style={{
                      background: isSelected ? 'var(--gradient-primary)' : 'var(--gradient-card)',
                      borderColor: isSelected ? 'transparent' : 'var(--border)',
                      color: isSelected ? '#FFFFFF' : 'var(--text-primary)',
                      boxShadow: isSelected ? '0 4px 16px rgba(37, 99, 235, 0.3)' : 'var(--shadow-sm)',
                    }}>
                    <div className="flex items-center gap-4">
                      <div className="w-8 h-8 rounded-full border-2 flex items-center justify-center flex-shrink-0" style={{
                        borderColor: isSelected ? 'rgba(255,255,255,0.5)' : 'var(--border)',
                      }}>
                        {isSelected && <div className="w-3 h-3 rounded-full bg-white" />}
                      </div>
                      <span className="flex-1 text-[17px]">{option}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Navigation */}
          <div className="flex gap-3">
            <button onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
              disabled={currentQuestion === 0}
              className="h-14 px-6 rounded-2xl text-base font-semibold flex items-center gap-2 border transition-all duration-200 disabled:opacity-30"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)', background: 'var(--bg-secondary)' }}>
              <ChevronLeft className="w-5 h-5" /> Prev
            </button>
            {currentQuestion < quizData.length - 1 ? (
              <button onClick={() => setCurrentQuestion(currentQuestion + 1)}
                className="flex-1 h-14 rounded-2xl text-lg font-semibold flex items-center justify-center gap-2 transition-all duration-200"
                style={{ background: 'var(--gradient-primary)', color: '#FFFFFF', boxShadow: '0 4px 16px rgba(37, 99, 235, 0.3)' }}>
                Next <ChevronRight className="w-5 h-5" />
              </button>
            ) : (
              <button onClick={handleSubmitQuiz}
                disabled={!allAnswered || isGenerating}
                className="flex-1 h-14 rounded-2xl text-lg font-bold flex items-center justify-center gap-2 transition-all duration-200 disabled:opacity-40"
                style={{ background: allAnswered ? 'linear-gradient(135deg, #10b981, #059669)' : 'var(--bg-tertiary)', color: '#FFFFFF', boxShadow: allAnswered ? '0 4px 16px rgba(16, 185, 129, 0.4)' : 'none' }}>
                {isGenerating ? <><Loader2 className="w-5 h-5 animate-spin" /> Evaluating...</> : <><CheckCircle2 className="w-5 h-5" /> Submit Quiz ({answeredCount}/{quizData.length})</>}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ── ANALYSIS SCREEN ──
  if (phase === 'analysis' && analytics) {
    const { score, total, accuracy, strengths, weak_topics, insights, per_question, attempt_number } = analytics;
    const scoreColor = accuracy >= 80 ? '#10b981' : accuracy >= 50 ? '#f59e0b' : '#ef4444';
    return (
      <div className="h-full overflow-auto p-6" style={{ background: 'var(--bg-primary)' }}>
        <div className="w-full max-w-3xl mx-auto animate-fade-up space-y-6">

          {/* Score Card */}
          <div className="p-8 rounded-3xl border text-center" style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-md)' }}>
            <div className="text-6xl font-black mb-2" style={{ color: scoreColor }}>{score}<span className="text-3xl font-bold" style={{ color: 'var(--text-muted)' }}>/{total}</span></div>
            <div className="text-lg font-semibold mb-4" style={{ color: 'var(--text-secondary)' }}>
              {accuracy}% Accuracy · Attempt #{attempt_number}
            </div>
            <div className="w-full h-3 rounded-full overflow-hidden mx-auto max-w-xs" style={{ background: 'var(--bg-tertiary)' }}>
              <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${accuracy}%`, background: scoreColor }} />
            </div>
          </div>

          {/* Strengths & Weak Areas */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Strengths */}
            <div className="p-6 rounded-2xl border" style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)' }}>
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-5 h-5" style={{ color: '#10b981' }} />
                <h3 className="text-lg font-bold" style={{ color: '#10b981' }}>Strengths</h3>
              </div>
              {strengths.length > 0 ? (
                <div className="space-y-2">
                  {strengths.map(t => (
                    <div key={t} className="flex items-center gap-2 px-3 py-2 rounded-xl" style={{ background: 'rgba(16,185,129,0.08)' }}>
                      <CheckCircle2 className="w-4 h-4" style={{ color: '#10b981' }} />
                      <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{t}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Keep practicing to build strengths!</p>
              )}
            </div>

            {/* Weak Areas */}
            <div className="p-6 rounded-2xl border" style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)' }}>
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="w-5 h-5" style={{ color: '#f59e0b' }} />
                <h3 className="text-lg font-bold" style={{ color: '#f59e0b' }}>Weak Areas</h3>
              </div>
              {Object.keys(weak_topics).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(weak_topics).sort((a, b) => b[1] - a[1]).map(([t, count]) => (
                    <div key={t} className="flex items-center justify-between px-3 py-2 rounded-xl" style={{ background: 'rgba(245,158,11,0.08)' }}>
                      <div className="flex items-center gap-2">
                        <XCircle className="w-4 h-4" style={{ color: '#f59e0b' }} />
                        <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{t}</span>
                      </div>
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>{count} mistake{count > 1 ? 's' : ''}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No weak areas — great job!</p>
              )}
            </div>
          </div>

          {/* Insights */}
          <div className="p-6 rounded-2xl border" style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)' }}>
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />
              <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Actionable Insights</h3>
            </div>
            <div className="space-y-2">
              {insights.map((insight, i) => (
                <div key={i} className="flex items-start gap-3 px-3 py-2 rounded-xl" style={{ background: 'var(--bg-tertiary)' }}>
                  <span className="text-base mt-0.5">💡</span>
                  <span className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{insight}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3">
            <button onClick={() => { setReviewIdx(0); setPhase('review'); }}
              className="flex-1 h-14 rounded-2xl text-[16px] font-bold flex items-center justify-center gap-2 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] border"
              style={{ borderColor: 'var(--accent-primary)', color: 'var(--accent-primary)', background: 'var(--bg-secondary)' }}>
              <BarChart3 className="w-5 h-5" /> Review Answers
            </button>
            <button onClick={handleGenerateAdaptive} disabled={isGenerating}
              className="flex-1 h-14 rounded-2xl text-[16px] font-bold flex items-center justify-center gap-2 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
              style={{ background: 'var(--gradient-primary)', color: '#FFFFFF', boxShadow: 'var(--shadow-glow)' }}>
              {isGenerating ? <><Loader2 className="w-5 h-5 animate-spin" /> Generating...</> : <><RefreshCw className="w-5 h-5" /> Focus on Weak Areas</>}
            </button>
            <button onClick={handleQuit} disabled={isGenerating}
              className="h-14 px-6 rounded-2xl text-[16px] font-bold flex items-center justify-center gap-2 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] border"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)', background: 'var(--bg-secondary)' }}>
              <LogOut className="w-5 h-5" /> Quit
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── REVIEW SCREEN ──
  if (phase === 'review' && analytics) {
    const pq = analytics.per_question[reviewIdx];
    if (!pq) { setPhase('analysis'); return null; }
    return (
      <div className="h-full overflow-auto flex items-center justify-center p-6" style={{ background: 'var(--bg-primary)' }}>
        <div className="w-full max-w-3xl animate-fade-up">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <button onClick={() => setPhase('analysis')}
              className="flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-xl border transition-all hover:scale-105"
              style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)', background: 'var(--bg-secondary)' }}>
              <ArrowLeft className="w-4 h-4" /> Back to Analysis
            </button>
            <span className="text-sm font-semibold px-3 py-1 rounded-lg" style={{ background: pq.is_correct ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)', color: pq.is_correct ? '#10b981' : '#ef4444' }}>
              {pq.is_correct ? '✓ Correct' : '✗ Incorrect'} · {pq.topic}
            </span>
          </div>

          <div className="text-sm font-medium mb-2" style={{ color: 'var(--text-muted)' }}>
            Question {reviewIdx + 1} of {analytics.per_question.length}
          </div>

          {/* Question */}
          <div className="p-8 rounded-3xl border mb-6" style={{ background: 'var(--gradient-card)', borderColor: 'var(--border)' }}>
            <h2 className="text-2xl font-bold mb-8 leading-relaxed" style={{ color: 'var(--text-primary)' }}>{pq.question}</h2>
            <div className="space-y-3">
              {pq.options.map((opt, i) => {
                const isCorrectOpt = i === pq.correct;
                const isUserPick = i === pq.selected;
                const isWrong = isUserPick && !isCorrectOpt;
                let bg = 'var(--gradient-card)', border = 'var(--border)';
                if (isCorrectOpt) { bg = 'rgba(16,185,129,0.08)'; border = '#10b981'; }
                if (isWrong) { bg = 'rgba(239,68,68,0.08)'; border = '#ef4444'; }
                return (
                  <div key={i} className="w-full text-left p-5 rounded-2xl border" style={{ background: bg, borderColor: border }}>
                    <div className="flex items-center gap-4">
                      <div className="w-8 h-8 rounded-full border-2 flex items-center justify-center flex-shrink-0" style={{ borderColor: border }}>
                        {isCorrectOpt && <CheckCircle2 className="w-5 h-5" style={{ color: '#10b981' }} />}
                        {isWrong && <XCircle className="w-5 h-5" style={{ color: '#ef4444' }} />}
                      </div>
                      <span className="flex-1 text-[17px]" style={{ color: 'var(--text-primary)' }}>{opt}</span>
                      {isUserPick && <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ background: isWrong ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)', color: isWrong ? '#ef4444' : '#10b981' }}>Your answer</span>}
                    </div>
                  </div>
                );
              })}
            </div>
            {/* Explanation */}
            <div className="mt-6 p-5 rounded-2xl" style={{ background: 'var(--bg-tertiary)' }}>
              <div className="flex items-start gap-3">
                <span className="text-xl">💡</span>
                <div>
                  <div className="font-semibold text-base mb-1" style={{ color: 'var(--text-primary)' }}>Explanation</div>
                  <p className="text-base leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{pq.explanation}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Nav */}
          <div className="flex gap-3">
            <button onClick={() => setReviewIdx(Math.max(0, reviewIdx - 1))} disabled={reviewIdx === 0}
              className="h-14 px-6 rounded-2xl text-base font-semibold flex items-center gap-2 border transition-all disabled:opacity-30"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)', background: 'var(--bg-secondary)' }}>
              <ChevronLeft className="w-5 h-5" /> Prev
            </button>
            <button onClick={() => setReviewIdx(Math.min(analytics.per_question.length - 1, reviewIdx + 1))} disabled={reviewIdx === analytics.per_question.length - 1}
              className="flex-1 h-14 rounded-2xl text-lg font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-30"
              style={{ background: 'var(--gradient-primary)', color: '#FFFFFF' }}>
              Next <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
