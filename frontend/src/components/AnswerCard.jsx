import { useState } from 'react';
import {
  FileQuestion, Clock, BookOpen, AlertTriangle, ChevronDown,
  ChevronUp, Info, CheckCircle2, XCircle, Sparkles
} from 'lucide-react';
import ConfidenceBadge from '../components/ConfidenceBadge';
import ConflictCard from '../components/ConflictCard';
import SourceCard from '../components/SourceCard';

const TABS = [
  { key: 'answer', label: 'Answer' },
  { key: 'sources', label: 'Sources' },
  { key: 'conflicts', label: 'Conflicts' },
];

export default function AnswerCard({ result }) {
  const [activeTab, setActiveTab] = useState('answer');
  const [evidenceExpanded, setEvidenceExpanded] = useState(false);

  if (!result) return null;

  const conflictCount = result.conflicts?.length || 0;
  const sourceCount = result.sources?.length || 0;
  const evidencePoints = result.evidence_points || [];
  const isInsufficient = result.status === 'INSUFFICIENT_EVIDENCE';
  const isConflicting = result.status === 'CONFLICTING';

  const tabLabel = (key) => {
    if (key === 'conflicts') return `Conflicts${conflictCount > 0 ? ` (${conflictCount})` : ''}`;
    if (key === 'sources') return `Sources (${sourceCount})`;
    return 'Answer';
  };

  const ts = result.timestamp
    ? new Date(result.timestamp).toLocaleString()
    : '';

  return (
    <div className="card fade-in" style={{ margin: '0 24px 24px' }}>
      {/* Header */}
      <div className="card-header" style={{ marginBottom: 16, justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <div className="flex items-center gap-2">
          <div className="card-icon blue"><BookOpen size={15} /></div>
          <div>
            <div className="card-title">Investigation Result</div>
            {ts && (
              <div className="text-xs text-muted flex items-center gap-1" style={{ marginTop: 2 }}>
                <Clock size={9} /> {ts}
                {result.processing_time_ms > 0 && (
                  <span>· {result.processing_time_ms}ms</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Question echo */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: '10px 14px',
        marginBottom: 16,
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
      }}>
        <FileQuestion size={14} style={{ color: 'var(--text-muted)', marginTop: 2, flexShrink: 0 }} />
        <span className="text-sm" style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>
          "{result.question}"
        </span>
      </div>

      {/* Confidence + Status */}
      <div style={{ marginBottom: 16 }}>
        <ConfidenceBadge
          status={result.status}
          confidence={result.confidence}
          confidenceLevel={result.confidence_level}
          confidenceExplanation={result.confidence_explanation}
        />
      </div>

      {/* Conflict warning banner */}
      {conflictCount > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '10px 14px',
          background: 'rgba(249,115,22,0.08)',
          border: '1px solid rgba(249,115,22,0.25)',
          borderRadius: 'var(--radius-md)',
          marginBottom: 16,
          cursor: 'pointer',
        }}
        onClick={() => setActiveTab('conflicts')}
        >
          <AlertTriangle size={15} style={{ color: 'var(--accent-orange)', flexShrink: 0 }} />
          <span style={{ fontSize: 13, color: 'var(--accent-orange)', fontWeight: 600 }}>
            ⚠ {conflictCount} conflicting claim{conflictCount > 1 ? 's' : ''} detected across documents
          </span>
          <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>Click to view →</span>
        </div>
      )}

      {/* Tabs */}
      <div className="tab-list" style={{ marginBottom: 16 }}>
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={`tab-btn ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tabLabel(tab.key)}
            {tab.key === 'conflicts' && conflictCount > 0 && (
              <span style={{ marginLeft: 4, width: 16, height: 16, background: 'var(--accent-orange)', color: 'white', borderRadius: '50%', fontSize: 10, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}>
                {conflictCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── ANSWER TAB ─────────────────────────────────────────────────────── */}
      {activeTab === 'answer' && (
        <div className="fade-in">

          {/* Main Answer Block */}
          <div style={{
            background: isInsufficient
              ? 'rgba(239,68,68,0.05)'
              : isConflicting
              ? 'rgba(249,115,22,0.05)'
              : 'rgba(59,130,246,0.04)',
            border: `1px solid ${isInsufficient ? 'rgba(239,68,68,0.2)' : isConflicting ? 'rgba(249,115,22,0.2)' : 'rgba(59,130,246,0.15)'}`,
            borderRadius: 'var(--radius-md)',
            padding: '16px 18px',
            marginBottom: 16,
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              {isInsufficient
                ? <XCircle size={18} style={{ color: 'var(--accent-red)', flexShrink: 0, marginTop: 2 }} />
                : isConflicting
                ? <AlertTriangle size={18} style={{ color: 'var(--accent-orange)', flexShrink: 0, marginTop: 2 }} />
                : <Sparkles size={18} style={{ color: 'var(--accent-blue)', flexShrink: 0, marginTop: 2 }} />
              }
              <p style={{
                fontSize: 15,
                lineHeight: 1.75,
                color: 'var(--text-primary)',
                fontWeight: 400,
                margin: 0,
              }}>
                {result.answer}
              </p>
            </div>
          </div>

          {/* Key Evidence Points */}
          {evidencePoints.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <button
                onClick={() => setEvidenceExpanded(!evidenceExpanded)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  padding: '4px 0',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  marginBottom: 6,
                }}
              >
                <CheckCircle2 size={12} style={{ color: 'var(--accent-green)' }} />
                Key Evidence
                {evidenceExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>

              {evidenceExpanded && (
                <div className="fade-in" style={{
                  borderLeft: '2px solid var(--accent-blue)',
                  paddingLeft: 12,
                }}>
                  {evidencePoints.map((pt, i) => (
                    <div key={i} style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 8,
                      padding: '5px 0',
                      borderBottom: i < evidencePoints.length - 1 ? '1px solid var(--border)' : 'none',
                    }}>
                      <span style={{ color: 'var(--accent-cyan)', fontSize: 12, marginTop: 2, flexShrink: 0 }}>•</span>
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{pt}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Source quick-links at the bottom of the answer tab */}
          {sourceCount > 0 && !isInsufficient && (
            <div style={{ marginBottom: 12 }}>
              <div style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: 'var(--text-muted)',
                marginBottom: 8,
              }}>
                Sources
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {result.sources.map((s, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '8px 12px',
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                    }}
                    onClick={() => setActiveTab('sources')}
                  >
                    <span style={{ fontSize: 14 }}>📄</span>
                    <div style={{ flex: 1, overflow: 'hidden' }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {s.document}
                        {s.page && s.page !== -1 ? ` — Page ${s.page}` : ''}
                      </div>
                      {s.excerpt && (
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          "{s.excerpt}"
                        </div>
                      )}
                    </div>
                    <div style={{
                      flexShrink: 0,
                      padding: '2px 7px',
                      borderRadius: 10,
                      fontSize: 10,
                      fontWeight: 700,
                      background: 'rgba(59,130,246,0.12)',
                      border: '1px solid rgba(59,130,246,0.3)',
                      color: 'var(--accent-blue)',
                    }}>
                      {Math.round(Math.min(1, s.relevance || s.similarity_score || 0) * 100)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Uncertainty note — only show when meaningful */}
          {result.uncertainty && (
            <div style={{
              marginTop: 12,
              padding: '10px 14px',
              background: 'rgba(100,116,139,0.08)',
              border: '1px solid rgba(100,116,139,0.2)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              gap: 8,
            }}>
              <Info size={14} style={{ color: 'var(--text-muted)', flexShrink: 0, marginTop: 2 }} />
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 3 }}>Uncertainty</div>
                <span className="text-xs text-secondary">{result.uncertainty}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── SOURCES TAB ────────────────────────────────────────────────────── */}
      {activeTab === 'sources' && (
        <div className="fade-in">
          {sourceCount === 0 ? (
            <div className="empty-state">
              <span className="text-sm text-muted">No sources available</span>
            </div>
          ) : (
            result.sources.map((source, i) => (
              <SourceCard key={i} source={source} index={i} />
            ))
          )}
        </div>
      )}

      {/* ── CONFLICTS TAB ──────────────────────────────────────────────────── */}
      {activeTab === 'conflicts' && (
        <div className="fade-in">
          {conflictCount === 0 ? (
            <div className="empty-state">
              <div style={{ fontSize: 28 }}>✓</div>
              <span className="text-sm" style={{ color: 'var(--accent-green)' }}>No conflicts detected</span>
              <span className="text-xs text-muted">All retrieved evidence appears consistent</span>
            </div>
          ) : (
            result.conflicts.map((conflict, i) => (
              <ConflictCard key={i} conflict={conflict} index={i} />
            ))
          )}
        </div>
      )}
    </div>
  );
}
