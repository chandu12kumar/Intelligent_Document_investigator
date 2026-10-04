import { FileText, BookOpen, Tag, Hash } from 'lucide-react';

export default function EvidenceCard({ item, index }) {
  const scoreColor =
    item.similarity_score >= 0.8
      ? 'var(--accent-green)'
      : item.similarity_score >= 0.6
      ? 'var(--accent-yellow)'
      : 'var(--accent-red)';

  return (
    <div className="evidence-card fade-in" style={{ animationDelay: `${index * 50}ms` }}>
      {/* Header */}
      <div className="evidence-source">
        <div style={{ width: 24, height: 24, borderRadius: 6, background: 'rgba(6,182,212,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <FileText size={12} style={{ color: 'var(--accent-cyan)' }} />
        </div>
        <span className="evidence-doc-name truncate">{item.document}</span>
        {item.page && item.page !== -1 && (
          <span className="evidence-page">pg. {item.page}</span>
        )}
        {item.section && (
          <span className="evidence-page" style={{ background: 'rgba(139,92,246,0.1)', color: 'var(--accent-purple)' }}>
            <Tag size={9} style={{ display: 'inline', marginRight: 2 }} />
            {item.section}
          </span>
        )}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4 }}>
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: scoreColor,
              flexShrink: 0,
            }}
          />
          <span className="text-xs" style={{ color: scoreColor, fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>
            {(item.similarity_score * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Quote */}
      <div className="evidence-quote">
        {item.quote || 'No text available'}
      </div>

      {/* Footer */}
      <div className="flex gap-2 mt-2">
        <span className="text-xs text-muted">
          <Hash size={10} style={{ display: 'inline', marginRight: 2 }} />
          Chunk {item.chunk_index}
        </span>
        <span className="text-xs text-muted">·</span>
        <span className="text-xs text-muted">{item.source_type?.toUpperCase()}</span>
        {item.source_type === 'ocr_used' && (
          <span className="badge badge-blue" style={{ fontSize: 10 }}>OCR</span>
        )}
      </div>
    </div>
  );
}
