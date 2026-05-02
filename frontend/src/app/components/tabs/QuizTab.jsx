import { useState } from "react";
import { CheckCircle2, XCircle, ArrowRight, Sparkles, Loader2 } from "lucide-react";

import { api } from "@/lib/api";

export function QuizTab({ title = 'this chapter', chapterId }) {
  const [isGenerated, setIsGenerated] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);

  const [quizData, setQuizData] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [showResult, setShowResult] = useState(false);
  const [score, setScore] = useState(0);

  const question = quizData[currentQuestion];

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const data = await api.quiz.generate(chapterId);
      if (data && data.length > 0) {
        setQuizData(data);
        setIsGenerated(true);
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

  if (!isGenerated) {
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
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-sm font-medium">
              {error}
            </div>
          )}

          <button  
            onClick={handleGenerate} disabled={isGenerating}
            className="w-full h-14 rounded-2xl text-[17px] font-bold flex items-center justify-center gap-2 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100"
            style={{ background: 'var(--gradient-primary)', color: '#FFFFFF', boxShadow: 'var(--shadow-glow)' }}>
            {isGenerating ? <><Loader2 className="w-5 h-5 animate-spin" /> Generating Quiz...</> : <><Sparkles className="w-5 h-5" /> Generate Quiz</>}
          </button>
        </div>
      </div>
    );
  }

  const handleAnswer = (index) => { if (!showResult) setSelectedAnswer(index); };
  const handleSubmit = () => {
    if (selectedAnswer === null) return;
    setShowResult(true);
    if (selectedAnswer === question.correct) setScore(score + 1);
  };
  const handleNext = () => {
    if (currentQuestion < quizData.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
      setSelectedAnswer(null);
      setShowResult(false);
    }
  };

  const getOptionStyle = (index) => {
    if (!showResult) {
      return {
        background: selectedAnswer === index ? 'var(--gradient-primary)' : 'var(--gradient-card)',
        borderColor: selectedAnswer === index ? 'transparent' : 'var(--border)',
        color: selectedAnswer === index ? '#FFFFFF' : 'var(--text-primary)',
        boxShadow: selectedAnswer === index ? '0 4px 16px rgba(37, 99, 235, 0.3)' : 'var(--shadow-sm)',
      };
    }
    if (index === question.correct) {
      return { background: 'rgba(16, 185, 129, 0.08)', borderColor: 'var(--accent-success)', color: 'var(--text-primary)', boxShadow: 'none' };
    }
    if (index === selectedAnswer && selectedAnswer !== question.correct) {
      return { background: 'rgba(239, 68, 68, 0.08)', borderColor: 'var(--accent-danger)', color: 'var(--text-primary)', boxShadow: 'none' };
    }
    return { background: 'var(--gradient-card)', borderColor: 'var(--border)', color: 'var(--text-primary)', boxShadow: 'none' };
  };

  return (
    <div className="h-full overflow-auto flex items-center justify-center p-6" style={{ background: 'var(--bg-primary)' }}>
      <div className="w-full max-w-3xl animate-fade-up">
        {/* Progress */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <span className="text-base font-medium" style={{ color: 'var(--text-secondary)' }}>
              Question {currentQuestion + 1} of {quizData.length}
            </span>
            <span className="text-base font-semibold px-3 py-1 rounded-lg" style={{
              background: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent-success)'
            }}>
              Score: {score}/{currentQuestion + (showResult ? 1 : 0)}
            </span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-tertiary)' }}>
            <div className="h-full rounded-full transition-all duration-500" style={{ 
              background: 'var(--gradient-primary)',
              width: `${((currentQuestion + 1) / quizData.length) * 100}%`
            }} />
          </div>
        </div>

        {/* Question */}
        <div className="p-8 rounded-3xl border mb-6" style={{
          background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-sm)',
        }}>
          <h2 className="text-3xl font-bold mb-8 leading-relaxed" style={{ color: 'var(--text-primary)' }}>
            {question.question}
          </h2>

          <div className="space-y-3">
            {question.options.map((option, index) => (
              <button
                key={index}
                onClick={() => handleAnswer(index)}
                disabled={showResult}
                className="w-full text-left p-5 rounded-2xl border transition-all duration-200 hover:scale-[1.005]"
                style={getOptionStyle(index)}
              >
                <div className="flex items-center gap-4">
                  <div className="w-8 h-8 rounded-full border-2 flex items-center justify-center flex-shrink-0" style={{ 
                    borderColor: showResult 
                      ? (index === question.correct ? 'var(--accent-success)' : index === selectedAnswer ? 'var(--accent-danger)' : 'var(--border)')
                      : selectedAnswer === index ? 'rgba(255,255,255,0.5)' : 'var(--border)'
                  }}>
                    {showResult && index === question.correct && <CheckCircle2 className="w-5 h-5" style={{ color: 'var(--accent-success)' }} />}
                    {showResult && index === selectedAnswer && selectedAnswer !== question.correct && <XCircle className="w-5 h-5" style={{ color: 'var(--accent-danger)' }} />}
                  </div>
                  <span className="flex-1 text-[17px]">{option}</span>
                </div>
              </button>
            ))}
          </div>

          {showResult && (
            <div className="mt-6 p-5 rounded-2xl" style={{ background: 'var(--bg-tertiary)' }}>
              <div className="flex items-start gap-3">
                <span className="text-xl">💡</span>
                <div>
                  <div className="font-semibold text-base mb-1" style={{ color: 'var(--text-primary)' }}>Explanation</div>
                  <p className="text-base leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{question.explanation}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Action */}
        {!showResult ? (
          <button
            onClick={handleSubmit}
            disabled={selectedAnswer === null}
            className="w-full h-14 rounded-2xl text-lg font-semibold transition-all duration-200 active:scale-[0.99] disabled:opacity-30"
            style={{ background: 'var(--gradient-primary)', color: '#FFFFFF', boxShadow: '0 4px 16px rgba(37, 99, 235, 0.3)' }}
          >
            Submit Answer
          </button>
        ) : currentQuestion < quizData.length - 1 ? (
          <button
            onClick={handleNext}
            className="w-full h-14 rounded-2xl text-lg font-semibold flex items-center justify-center gap-2 transition-all duration-200 active:scale-[0.99]"
            style={{ background: 'var(--gradient-primary)', color: '#FFFFFF', boxShadow: '0 4px 16px rgba(37, 99, 235, 0.3)' }}
          >
            Next Question <ArrowRight className="w-5 h-5" />
          </button>
        ) : (
          <div className="p-10 rounded-3xl border text-center" style={{
            background: 'var(--gradient-card)', borderColor: 'var(--border)', boxShadow: 'var(--shadow-md)',
          }}>
            <div className="text-5xl mb-4">🎉</div>
            <h3 className="text-2xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>Quiz Complete!</h3>
            <p className="text-lg" style={{ color: 'var(--text-secondary)' }}>
              You scored <span className="font-bold" style={{ color: 'var(--accent-success)' }}>
                {score + (selectedAnswer === question.correct ? 1 : 0)}
              </span> out of {quizData.length}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
