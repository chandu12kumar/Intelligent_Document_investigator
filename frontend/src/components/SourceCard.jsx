import { useState } from 'react';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';

export default function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false);

  // Support both new (excerpt/relevance) and old (relevant_text/similarity_score) fields
  const excerpt = source.excerpt || source.relevant_text || '';
  const relevanceRaw = source.relevance || source.similarity_score || 0;
  const relevancePercent = Math.round(Math.min(1, relevanceRaw) * 100);

  const scoreColor =
    relevancePercent >= 70
      ? 'var(--accent-green)'
      : relevancePercent >= 45
      ? 'var(--accent-yellow)'
      : 'var(--accent-red)';

  return (
    <div className="source-card fade-in" style={{ animationDelay: `${index * 50}ms` }}>
      <div className="source-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-2" style={{ flex: 1, overflow: 'hidden' }}>
          <div className="document-icon" style={{ width: 28, height: 28, flexShrink: 0 }}>
            <FileText size={13} />
          </div>
          <div style={{ overflow: 'hidden', flex: 1 }}>
            <div className="document-name" style={{ fontSize: 13 }}>{source.document}</div>
            {source.page && source.page !== -1 && (
              <div className="document-meta">Page {source.page}</div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2" style={{ flexShrink: 0 }}>
          <div
            style={{
              padding: '2px 8px',
              borderRadius: 12,
              background: `${scoreColor}20`,
              border: `1px solid ${scoreColor}40`,
              fontSize: 11,
              fontWeight: 700,
              color: scoreColor,
              fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            {relevancePercent}% relevance
          </div>
          {expanded ? <ChevronUp size={14} style={{ color: 'var(--text-muted)' }} /> : <ChevronDown size={14} style={{ color: 'var(--text-muted)' }} />}
        </div>
      </div>

      {/* Always show excerpt below header */}
      {excerpt && (
        <div style={{
          padding: '8px 12px 4px',
          fontSize: 12,
          color: 'var(--text-muted)',
          fontStyle: 'italic',
          borderLeft: '2px solid var(--border-light)',
          marginLeft: 40,
          marginTop: 6,
        }}>
          "{excerpt}"
        </div>
      )}

      {expanded && (
        <div className="source-card-body fade-in">
          <div className="text-xs text-muted mt-2" style={{ paddingLeft: 4, borderTop: '1px solid var(--border)', paddingTop: 8, marginTop: 8 }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>
              Relevance score: {relevanceRaw.toFixed(4)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
