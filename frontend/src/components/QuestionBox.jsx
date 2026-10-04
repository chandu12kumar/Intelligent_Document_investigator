import { useState, useRef, useEffect } from 'react';
import { Search, Zap, ArrowRight } from 'lucide-react';

const EXAMPLE_QUESTIONS = [
  'What is this document about?',
  'Can you summarize the key points?',
  'What are the most important things I should know?',
  'What skills or qualifications are mentioned?',
  'What projects or work experience are described?',
  'Are there any conflicting statements?',
];

export default function QuestionBox({ onSubmit, loading, disabled }) {
  const [question, setQuestion] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (q = question) => {
    const trimmed = (q || question).trim();
    if (!trimmed || loading || disabled) return;
    onSubmit(trimmed);
    setQuestion('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  }, [question]);

  return (
    <div className="question-area">
      {/* Input */}
      <div className="question-input-wrapper">
        <div style={{ position: 'relative', flex: 1 }}>
          <Search
            size={16}
            style={{
              position: 'absolute',
              left: 16,
              top: 18,
              color: 'var(--text-muted)',
              pointerEvents: 'none',
            }}
          />
          <textarea
            ref={textareaRef}
            className="question-input"
            placeholder="Ask a question about your documents... (Shift+Enter for new line)"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading || disabled}
            style={{ paddingLeft: 44, width: '100%' }}
            rows={1}
          />
        </div>
        <button
          className="btn btn-primary"
          onClick={() => handleSubmit()}
          disabled={!question.trim() || loading || disabled}
          style={{ height: 52, flexShrink: 0, minWidth: 130 }}
        >
          {loading ? (
            <>
              <div className="loading-spinner" />
              Investigating...
            </>
          ) : (
            <>
              <Zap size={15} strokeWidth={2.5} />
              Investigate
            </>
          )}
        </button>
      </div>

      {disabled && (
        <div className="text-xs mt-2" style={{ color: 'var(--accent-yellow)', display: 'flex', alignItems: 'center', gap: 4 }}>
          <span>⚠</span>
          Upload documents first to begin investigation
        </div>
      )}

      {/* Example chips */}
      <div className="suggestion-chips">
        <span className="text-xs text-muted" style={{ paddingTop: 6, flexShrink: 0 }}>
          Try:
        </span>
        {EXAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            className="chip"
            onClick={() => handleSubmit(q)}
            disabled={loading || disabled}
          >
            {q.length > 45 ? q.slice(0, 45) + '...' : q}
          </button>
        ))}
      </div>
    </div>
  );
}
