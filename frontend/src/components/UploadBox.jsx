import { useState, useRef, useCallback } from 'react';
import { Upload, FileText, Image, CheckCircle2, Loader2, AlertCircle, X } from 'lucide-react';
import { uploadDocument } from '../services/api';

const SUPPORTED_TYPES = ['.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg'];
const MAX_FILE_SIZE_MB = 50;

const UPLOAD_STEPS = [
  { key: 'upload', label: 'Uploading file...' },
  { key: 'extract', label: 'Extracting text...' },
  { key: 'embed', label: 'Generating embeddings...' },
  { key: 'index', label: 'Indexing in vector database...' },
];

function UploadStatusItem({ label, state }) {
  return (
    <li className={`upload-status-item ${state}`}>
      {state === 'done' && <CheckCircle2 size={12} />}
      {state === 'active' && <Loader2 size={12} className="spin" style={{ animation: 'spin 0.8s linear infinite' }} />}
      {state === 'pending' && <div style={{ width: 12, height: 12, borderRadius: '50%', border: '1px solid var(--border)', flexShrink: 0 }} />}
      <span>{label}</span>
    </li>
  );
}

function FileQueueItem({ file, status, error, progress, onRemove }) {
  const ext = file.name.split('.').pop().toLowerCase();

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: `1px solid ${error ? 'rgba(239,68,68,0.3)' : status === 'done' ? 'rgba(16,185,129,0.3)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-md)',
      padding: '10px 12px',
      marginBottom: 8,
    }}>
      <div className="flex items-center gap-2">
        <div className="document-icon" style={{ width: 28, height: 28 }}>
          {['png','jpg','jpeg'].includes(ext)
            ? <Image size={14} />
            : <FileText size={14} />
          }
        </div>
        <div className="flex-1 truncate">
          <div className="document-name" style={{ fontSize: 12 }}>{file.name}</div>
          <div className="text-xs text-muted">
            {(file.size / 1024 / 1024).toFixed(2)} MB
          </div>
        </div>
        {status === 'idle' && (
          <button className="btn btn-icon btn-danger btn-sm" onClick={() => onRemove(file)}>
            <X size={12} />
          </button>
        )}
        {status === 'uploading' && <Loader2 size={16} className="spin" style={{ animation: 'spin 0.8s linear infinite', color: 'var(--accent-blue)', flexShrink: 0 }} />}
        {status === 'done' && <CheckCircle2 size={16} style={{ color: 'var(--accent-green)', flexShrink: 0 }} />}
        {status === 'error' && <AlertCircle size={16} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />}
      </div>

      {status === 'uploading' && (
        <div className="progress-bar-wrapper">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="text-xs text-muted mt-1">{progress}%</div>
        </div>
      )}

      {error && (
        <div className="text-xs mt-1" style={{ color: 'var(--accent-red)' }}>{error}</div>
      )}
    </div>
  );
}

export default function UploadBox({ onDocumentUploaded }) {
  const [dragOver, setDragOver] = useState(false);
  const [fileQueue, setFileQueue] = useState([]);
  const [fileStatuses, setFileStatuses] = useState({});
  const fileInputRef = useRef(null);

  const validateFile = (file) => {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!SUPPORTED_TYPES.includes(ext)) {
      return `Unsupported type: ${ext}`;
    }
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      return `File too large (max ${MAX_FILE_SIZE_MB}MB)`;
    }
    return null;
  };

  const addFiles = useCallback((files) => {
    const newFiles = Array.from(files);
    const validFiles = [];
    const newStatuses = {};

    for (const file of newFiles) {
      const error = validateFile(file);
      if (error) {
        newStatuses[file.name] = { status: 'error', error, progress: 0 };
      } else {
        validFiles.push(file);
        newStatuses[file.name] = { status: 'idle', progress: 0 };
      }
    }

    setFileQueue((prev) => [...prev, ...Array.from(files)]);
    setFileStatuses((prev) => ({ ...prev, ...newStatuses }));

    // Auto-upload valid files
    for (const file of validFiles) {
      uploadFile(file, newStatuses);
    }
  }, [onDocumentUploaded]);

  const uploadFile = async (file, initialStatuses) => {
    setFileStatuses((prev) => ({
      ...prev,
      [file.name]: { ...prev[file.name], status: 'uploading', progress: 0 },
    }));

    try {
      const result = await uploadDocument(file, (pct) => {
        setFileStatuses((prev) => ({
          ...prev,
          [file.name]: { ...prev[file.name], progress: pct },
        }));
      });

      setFileStatuses((prev) => ({
        ...prev,
        [file.name]: { status: 'done', progress: 100 },
      }));

      onDocumentUploaded?.(result);
    } catch (err) {
      setFileStatuses((prev) => ({
        ...prev,
        [file.name]: {
          status: 'error',
          error: err.message || 'Upload failed',
          progress: 0,
        },
      }));
    }
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const handleRemove = (file) => {
    setFileQueue((prev) => prev.filter((f) => f.name !== file.name));
    setFileStatuses((prev) => {
      const s = { ...prev };
      delete s[file.name];
      return s;
    });
  };

  return (
    <div style={{ padding: '12px 16px' }}>
      <div
        className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={SUPPORTED_TYPES.join(',')}
          onChange={(e) => addFiles(e.target.files)}
          onClick={(e) => e.stopPropagation()}
        />
        <div className="upload-icon">
          <Upload size={20} />
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
          Drop documents here
        </div>
        <div className="text-xs text-muted">
          PDF, DOCX, TXT, PNG, JPG • Max {MAX_FILE_SIZE_MB}MB
        </div>
      </div>

      {fileQueue.length > 0 && (
        <div style={{ marginTop: 12 }}>
          {fileQueue.map((file) => (
            <FileQueueItem
              key={file.name}
              file={file}
              status={fileStatuses[file.name]?.status || 'idle'}
              error={fileStatuses[file.name]?.error}
              progress={fileStatuses[file.name]?.progress || 0}
              onRemove={handleRemove}
            />
          ))}
        </div>
      )}
    </div>
  );
}
