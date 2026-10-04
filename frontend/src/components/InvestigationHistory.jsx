import { BookOpen, Clock, CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';

const STATUS_ICONS = {
  SUPPORTED: { Icon: CheckCircle2, color: 'var(--accent-green)' },
  PARTIALLY_SUPPORTED: { Icon: Info, color: 'var(--accent-yellow)' },
  CONFLICTING: { Icon: AlertTriangle, color: 'var(--accent-orange)' },
  INSUFFICIENT_EVIDENCE: { Icon: XCircle, color: 'var(--accent-red)' },
};

function HistoryItem({ item, isActive, onClick }) {
  const cfg = STATUS_ICONS[item.status] || STATUS_ICONS.INSUFFICIENT_EVIDENCE;
  const { Icon } = cfg;

  const ts = item.timestamp
    ? new Date(item.timestamp).toLocaleString(undefined, {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    : '';

  return (
    <div
      className={`history-item ${isActive ? 'active' : ''}`}
      onClick={() => onClick(item)}
    >
      <div className="flex items-center gap-2">
        <Icon size={12} style={{ color: cfg.color, flexShrink: 0 }} />
        <div className="history-question">{item.question}</div>
      </div>
      <div className="history-meta flex items-center gap-2" style={{ paddingLeft: 20 }}>
        <Clock size={9} />
        {ts}
        <span className="text-xs" style={{ color: cfg.color, fontWeight: 600 }}>
          {Math.round((item.confidence || 0) * 100)}%
        </span>
      </div>
    </div>
  );
}

export default function InvestigationHistory({ history, activeId, onSelect }) {
  if (!history || history.length === 0) {
    return (
      <div className="empty-state" style={{ padding: '20px 16px' }}>
        <BookOpen size={24} style={{ opacity: 0.3 }} />
        <span className="text-xs text-muted">No investigations yet</span>
      </div>
    );
  }

  return (
    <div style={{ padding: '4px 16px 12px' }}>
      {history.map((item) => (
        <HistoryItem
          key={item.investigation_id}
          item={item}
          isActive={item.investigation_id === activeId}
          onClick={onSelect}
        />
      ))}
    </div>
  );
}
