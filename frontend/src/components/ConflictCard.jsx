import { AlertTriangle, FileText } from 'lucide-react';

function ConflictSource({ source, label }) {
  return (
    <div className="conflict-source">
      <div className="conflict-source-name">
        <FileText size={10} style={{ display: 'inline', marginRight: 4 }} />
        {source?.document || 'Unknown Document'}
        {source?.page && source.page !== -1 && (
          <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 4 }}>
            · pg.{source.page}
          </span>
        )}
      </div>
      <div className="conflict-source-quote">
        {source?.value
          ? <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: 15 }}>{source.value}</span>
          : null}
        {source?.quote && !source?.value ? (
          <span style={{ fontStyle: 'italic', fontSize: 12, color: 'var(--text-secondary)' }}>
            "{source.quote.slice(0, 200)}"
          </span>
        ) : source?.quote ? (
          <div style={{ marginTop: 6, fontStyle: 'italic', fontSize: 11, color: 'var(--text-muted)' }}>
            "{source.quote.slice(0, 150)}"
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function ConflictCard({ conflict, index }) {
  const typeLabel = {
    numeric_conflict: '🔢 Numeric Conflict',
    semantic_conflict: '🔤 Semantic Conflict',
    direct_contradiction: '❌ Direct Contradiction',
  }[conflict.type] || '⚠ Conflict';

  return (
    <div className="conflict-card fade-in" style={{ animationDelay: `${index * 80}ms` }}>
      <div className="conflict-header">
        <AlertTriangle size={16} style={{ color: 'var(--accent-orange)', flexShrink: 0 }} />
        <span className="conflict-title">{typeLabel}</span>
        {conflict.topic && (
          <span style={{
            fontSize: 11,
            padding: '2px 8px',
            background: 'rgba(249,115,22,0.1)',
            color: 'var(--accent-orange)',
            borderRadius: 20,
            marginLeft: 'auto',
            fontWeight: 500,
          }}>
            {conflict.topic}
          </span>
        )}
      </div>

      <div className="conflict-vs-grid">
        <ConflictSource source={conflict.source_a} label="Source A" />
        <div className="conflict-vs-divider">VS</div>
        <ConflictSource source={conflict.source_b} label="Source B" />
      </div>

      {conflict.description && (
        <div className="conflict-description">
          <span style={{ fontWeight: 600, color: 'var(--accent-orange)' }}>⚠ </span>
          {conflict.description}
        </div>
      )}
    </div>
  );
}
