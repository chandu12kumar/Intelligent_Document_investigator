import { Search, Cpu } from 'lucide-react';

export default function Navbar({ healthStatus }) {
  const isOnline = healthStatus?.status === 'healthy' || healthStatus?.status === 'degraded';
  const label = healthStatus?.status === 'healthy'
    ? 'AI Investigation Engine ● Online'
    : healthStatus?.status === 'degraded'
    ? 'AI Engine ● Degraded (Check API Key)'
    : 'Connecting...';

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <div className="navbar-logo">
          <Search size={18} color="white" strokeWidth={2.5} />
        </div>
        <div>
          <div className="navbar-title">Intelligent Document Investigator</div>
          <div className="navbar-subtitle">AI-powered evidence-based document investigation</div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className={`status-badge ${!isOnline ? 'offline' : ''}`}>
          <div className="status-dot" />
          <span>{label}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted">
          <Cpu size={13} />
          <span>{healthStatus?.embedding_model || 'all-MiniLM-L6-v2'}</span>
        </div>
      </div>
    </nav>
  );
}
