import { Search, Loader2 } from 'lucide-react';

const STEPS = [
  'Generating query embedding...',
  'Searching vector database...',
  'Detecting conflicts...',
  'Analyzing evidence...',
  'Generating investigation report...',
];

export default function LoadingState({ message }) {
  return (
    <div className="loading-overlay fade-in">
      <div className="loading-pulse">
        <Search size={28} color="white" strokeWidth={2} />
      </div>

      <div>
        <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>
          Investigating Documents
        </div>
        <div className="text-sm text-secondary" style={{ textAlign: 'center' }}>
          {message || 'Analyzing evidence and retrieving relevant information...'}
        </div>
      </div>

      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '16px 20px',
        width: '100%',
        maxWidth: 400,
      }}>
        {STEPS.map((step, i) => (
          <div key={step} className="upload-status-item" style={{ animationDelay: `${i * 400}ms` }}>
            <Loader2 size={11} style={{ animation: 'spin 0.8s linear infinite', color: 'var(--accent-blue)', flexShrink: 0 }} />
            {step}
          </div>
        ))}
      </div>
    </div>
  );
}
