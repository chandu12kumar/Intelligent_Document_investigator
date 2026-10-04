import { CheckCircle2, AlertTriangle, XCircle, Info, HelpCircle } from 'lucide-react';

const STATUS_CONFIG = {
  SUPPORTED: {
    label: 'Supported',
    className: 'supported',
    Icon: CheckCircle2,
    description: 'Answer is directly supported by document evidence',
  },
  PARTIALLY_SUPPORTED: {
    label: 'Partially Supported',
    className: 'partial',
    Icon: Info,
    description: 'Answer is partially supported; some aspects lack evidence',
  },
  CONFLICTING: {
    label: 'Conflicting Evidence',
    className: 'conflicting',
    Icon: AlertTriangle,
    description: 'Documents contain contradictory information on this topic',
  },
  INSUFFICIENT_EVIDENCE: {
    label: 'Insufficient Evidence',
    className: 'insufficient',
    Icon: XCircle,
    description: 'No relevant evidence found in the uploaded documents',
  },
};

export default function ConfidenceBadge({ status, confidence, confidenceLevel, confidenceExplanation }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.INSUFFICIENT_EVIDENCE;
  const { Icon } = config;

  const confidencePercent = Math.round((confidence || 0) * 100);
  const levelClass = (confidenceLevel || 'LOW').toLowerCase();

  return (
    <div>
      {/* Status Pill */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <div className={`status-pill ${config.className}`}>
          <Icon size={12} strokeWidth={2.5} />
          {config.label}
        </div>
        <span className="text-xs text-muted">{config.description}</span>
      </div>

      {/* Confidence Bar */}
      <div className="confidence-bar-wrapper">
        <div className="confidence-label">
          <span className="text-xs text-secondary">
            Evidence Confidence
          </span>
          <span
            className="text-xs"
            style={{
              color:
                levelClass === 'high'
                  ? 'var(--accent-green)'
                  : levelClass === 'medium'
                  ? 'var(--accent-yellow)'
                  : 'var(--accent-red)',
              fontWeight: 600,
            }}
          >
            {confidencePercent}% · {confidenceLevel || 'LOW'}
          </span>
        </div>
        <div className="confidence-bar">
          <div
            className={`confidence-fill ${levelClass}`}
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
        {confidenceExplanation && (
          <div className="text-xs text-muted mt-1">{confidenceExplanation}</div>
        )}
      </div>
    </div>
  );
}
