import { useState } from 'react';
import { FileText, FileImage, File, Trash2, RefreshCw, Layers } from 'lucide-react';
import { deleteDocument } from '../services/api';

const FILE_ICONS = {
  pdf: { icon: FileText, color: '#ef4444' },
  docx: { icon: FileText, color: '#3b82f6' },
  txt: { icon: FileText, color: '#94a3b8' },
  png: { icon: FileImage, color: '#8b5cf6' },
  jpg: { icon: FileImage, color: '#8b5cf6' },
  jpeg: { icon: FileImage, color: '#8b5cf6' },
};

function DocumentItem({ doc, onDelete }) {
  const [deleting, setDeleting] = useState(false);
  const fileInfo = FILE_ICONS[doc.file_type] || { icon: File, color: 'var(--accent-blue)' };
  const Icon = fileInfo.icon;

  const handleDelete = async (e) => {
    e.stopPropagation();
    if (!confirm(`Delete "${doc.filename}"?`)) return;
    setDeleting(true);
    try {
      await deleteDocument(doc.document_id);
      onDelete?.(doc.document_id);
    } catch (err) {
      alert(err.message || 'Delete failed');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="document-item">
      <div className="document-icon" style={{ color: fileInfo.color, background: `${fileInfo.color}18` }}>
        <Icon size={14} />
      </div>
      <div className="flex-1" style={{ overflow: 'hidden' }}>
        <div className="document-name">{doc.filename}</div>
        <div className="document-meta">
          {doc.pages > 0 ? `${doc.pages}p` : 'DOCX'} · {doc.chunks} chunks
          {doc.ocr_used && <span style={{ color: 'var(--accent-yellow)', marginLeft: 4 }}>OCR</span>}
        </div>
      </div>
      <button
        className="btn btn-icon btn-danger btn-sm"
        onClick={handleDelete}
        disabled={deleting}
        title="Delete document"
        style={{ opacity: deleting ? 0.5 : 1 }}
      >
        {deleting ? <RefreshCw size={12} style={{ animation: 'spin 0.8s linear infinite' }} /> : <Trash2 size={12} />}
      </button>
    </div>
  );
}

export default function DocumentList({ documents, onDocumentDeleted, onRefresh, loading }) {
  if (loading) {
    return (
      <div style={{ padding: '12px 16px' }}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="document-item">
            <div className="skeleton" style={{ width: 32, height: 32, borderRadius: 8, flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div className="skeleton" style={{ height: 12, width: '70%', marginBottom: 6 }} />
              <div className="skeleton" style={{ height: 10, width: '40%' }} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!documents || documents.length === 0) {
    return (
      <div className="empty-state" style={{ padding: '24px 16px' }}>
        <div className="card-icon blue" style={{ width: 40, height: 40, margin: '0 auto' }}>
          <Layers size={18} />
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          No documents indexed yet
        </div>
        <div className="text-xs text-muted">Upload your first document above</div>
      </div>
    );
  }

  return (
    <div style={{ padding: '4px 16px 12px' }}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-muted">{documents.length} document{documents.length !== 1 ? 's' : ''}</span>
        <button className="btn btn-sm btn-secondary" onClick={onRefresh} style={{ padding: '4px 8px' }}>
          <RefreshCw size={11} />
          Refresh
        </button>
      </div>
      {documents.map((doc) => (
        <DocumentItem key={doc.document_id} doc={doc} onDelete={onDocumentDeleted} />
      ))}
    </div>
  );
}
