import { useState, useEffect, useCallback } from 'react';
import { Upload, BookOpen, History, Search, Layers, AlertCircle } from 'lucide-react';

import Navbar from '../components/Navbar';
import UploadBox from '../components/UploadBox';
import DocumentList from '../components/DocumentList';
import QuestionBox from '../components/QuestionBox';
import AnswerCard from '../components/AnswerCard';
import InvestigationHistory from '../components/InvestigationHistory';
import LoadingState from '../components/LoadingState';

import { checkHealth, listDocuments, askQuestion, getInvestigationHistory, getInvestigation } from '../services/api';

const SIDEBAR_TABS = [
  { key: 'documents', label: 'Documents', Icon: Layers },
  { key: 'history', label: 'History', Icon: History },
];

export default function Investigator() {
  const [healthStatus, setHealthStatus] = useState(null);
  const [sidebarTab, setSidebarTab] = useState('documents');
  const [documents, setDocuments] = useState([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [currentResult, setCurrentResult] = useState(null);
  const [investigating, setInvestigating] = useState(false);
  const [error, setError] = useState(null);
  const [activeHistoryId, setActiveHistoryId] = useState(null);

  // ── Health check ────────────────────────────────────────────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const h = await checkHealth();
        setHealthStatus(h);
      } catch {
        setHealthStatus({ status: 'offline' });
      }
    };
    poll();
    const interval = setInterval(poll, 30000);
    return () => clearInterval(interval);
  }, []);

  // ── Load documents ──────────────────────────────────────────────────────────
  const loadDocuments = useCallback(async () => {
    setDocsLoading(true);
    try {
      const data = await listDocuments();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setDocsLoading(false);
    }
  }, []);

  useEffect(() => { loadDocuments(); }, [loadDocuments]);

  // ── Load history ────────────────────────────────────────────────────────────
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const data = await getInvestigationHistory();
      setHistory(data.investigations || []);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (sidebarTab === 'history') loadHistory();
  }, [sidebarTab, loadHistory]);

  // ── Document uploaded ───────────────────────────────────────────────────────
  const handleDocumentUploaded = useCallback((result) => {
    loadDocuments();
  }, [loadDocuments]);

  // ── Document deleted ────────────────────────────────────────────────────────
  const handleDocumentDeleted = useCallback((docId) => {
    setDocuments((prev) => prev.filter((d) => d.document_id !== docId));
  }, []);

  // ── Ask question ────────────────────────────────────────────────────────────
  const handleQuestion = useCallback(async (question) => {
    setInvestigating(true);
    setError(null);
    setCurrentResult(null);
    setActiveHistoryId(null);

    try {
      const result = await askQuestion(question);
      setCurrentResult(result);
      setActiveHistoryId(result.investigation_id);
      // Refresh history
      loadHistory();
    } catch (err) {
      setError(err.message || 'Investigation failed. Please try again.');
    } finally {
      setInvestigating(false);
    }
  }, [loadHistory]);

  // ── Select history item ─────────────────────────────────────────────────────
  const handleHistorySelect = useCallback(async (item) => {
    setActiveHistoryId(item.investigation_id);
    try {
      const full = await getInvestigation(item.investigation_id);
      setCurrentResult(full);
    } catch {
      // Use summary as fallback
      setCurrentResult(item);
    }
  }, []);

  const hasDocuments = documents.length > 0;

  return (
    <div className="app-container">
      <Navbar healthStatus={healthStatus} />

      <div className="main-layout">
        {/* ── Sidebar ───────────────────────────────────────────────────────── */}
        <aside className="sidebar">
          {/* Sidebar Tabs */}
          <div style={{ padding: '12px 16px 0', flexShrink: 0 }}>
            <div className="tab-list">
              {SIDEBAR_TABS.map(({ key, label, Icon }) => (
                <button
                  key={key}
                  className={`tab-btn ${sidebarTab === key ? 'active' : ''}`}
                  onClick={() => setSidebarTab(key)}
                  style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  <Icon size={13} />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {sidebarTab === 'documents' && (
            <>
              <div className="section-header" style={{ marginTop: 12 }}>
                <Upload size={12} />
                Upload Documents
              </div>
              <UploadBox onDocumentUploaded={handleDocumentUploaded} />
              <div className="section-header">
                <Layers size={12} />
                Indexed Documents
              </div>
              <div className="scrollable">
                <DocumentList
                  documents={documents}
                  loading={docsLoading}
                  onDocumentDeleted={handleDocumentDeleted}
                  onRefresh={loadDocuments}
                />
              </div>
            </>
          )}

          {sidebarTab === 'history' && (
            <>
              <div className="section-header" style={{ marginTop: 12 }}>
                <History size={12} />
                Recent Investigations
              </div>
              <div className="scrollable">
                {historyLoading ? (
                  <div style={{ padding: 16 }}>
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="history-item">
                        <div className="skeleton" style={{ height: 12, width: '80%', marginBottom: 6 }} />
                        <div className="skeleton" style={{ height: 10, width: '50%' }} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <InvestigationHistory
                    history={history}
                    activeId={activeHistoryId}
                    onSelect={handleHistorySelect}
                  />
                )}
              </div>
            </>
          )}
        </aside>

        {/* ── Main Content ──────────────────────────────────────────────────── */}
        <main className="main-content">
          {/* Question Box */}
          <div style={{
            background: 'var(--bg-secondary)',
            borderBottom: '1px solid var(--border)',
            flexShrink: 0,
          }}>
            <div style={{ padding: '16px 24px 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <Search size={16} style={{ color: 'var(--accent-cyan)' }} />
                <h1 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
                  Investigation Workspace
                </h1>
              </div>
              <p className="text-xs text-muted" style={{ paddingLeft: 24, marginBottom: 0 }}>
                Ask questions — the AI investigator will find evidence, detect conflicts, and cite sources
              </p>
            </div>
            <QuestionBox
              onSubmit={handleQuestion}
              loading={investigating}
              disabled={!hasDocuments && !investigating}
            />
          </div>

          {/* Results Area */}
          <div style={{ flex: 1, overflowY: 'auto', paddingTop: 24 }}>
            {/* Error state */}
            {error && !investigating && (
              <div style={{
                margin: '0 24px 24px',
                padding: '14px 18px',
                background: 'rgba(239,68,68,0.08)',
                border: '1px solid rgba(239,68,68,0.3)',
                borderRadius: 'var(--radius-lg)',
                display: 'flex',
                gap: 10,
              }}>
                <AlertCircle size={16} style={{ color: 'var(--accent-red)', flexShrink: 0, marginTop: 2 }} />
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--accent-red)', marginBottom: 4 }}>
                    Investigation Error
                  </div>
                  <div className="text-sm text-secondary">{error}</div>
                </div>
              </div>
            )}

            {/* Loading */}
            {investigating && <LoadingState />}

            {/* Result */}
            {!investigating && currentResult && (
              <AnswerCard result={currentResult} />
            )}

            {/* Empty / Welcome state */}
            {!investigating && !currentResult && !error && (
              <div className="loading-overlay" style={{ opacity: 0.6 }}>
                <div style={{
                  width: 80,
                  height: 80,
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(6,182,212,0.15))',
                  border: '1px solid rgba(59,130,246,0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <Search size={32} style={{ color: 'var(--accent-blue)' }} />
                </div>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', textAlign: 'center' }}>
                    Ready to Investigate
                  </div>
                  <div className="text-sm text-secondary" style={{ textAlign: 'center', marginTop: 6 }}>
                    {hasDocuments
                      ? `${documents.length} document${documents.length > 1 ? 's' : ''} indexed · Ask a question above to begin`
                      : 'Upload documents in the sidebar to get started'}
                  </div>
                </div>

                {hasDocuments && (
                  <div style={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '16px 20px',
                    maxWidth: 480,
                    width: '100%',
                  }}>
                    <div className="text-xs text-muted" style={{ marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 700 }}>
                      Demo Questions
                    </div>
                    {[
                      'What is this document about?',
                      'Can you summarize the key points?',
                      'What are the most important things I should know?',
                      'What skills or qualifications are mentioned?',
                      'What projects or work experience are described?',
                      'Are there any conflicting statements?',
                    ].map((q) => (
                      <button
                        key={q}
                        className="chip"
                        style={{ marginBottom: 6, display: 'block', width: '100%', textAlign: 'left' }}
                        onClick={() => handleQuestion(q)}
                      >
                        🔍 {q}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
