import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 min timeout for LLM calls
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─── Response Interceptor ──────────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const message =
        error.response.data?.detail ||
        error.response.data?.message ||
        `Server error: ${error.response.status}`;
      return Promise.reject(new Error(message));
    } else if (error.request) {
      return Promise.reject(
        new Error('Cannot connect to the server. Is the backend running on port 8000?')
      );
    }
    return Promise.reject(error);
  }
);

// ─── Health ────────────────────────────────────────────────────────────────────
export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

// ─── Documents ────────────────────────────────────────────────────────────────
export const uploadDocument = async (file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });
  return response.data;
};

export const listDocuments = async () => {
  const response = await api.get('/documents');
  return response.data;
};

export const deleteDocument = async (documentId) => {
  const response = await api.delete(`/documents/${documentId}`);
  return response.data;
};

// ─── Questions ────────────────────────────────────────────────────────────────
export const askQuestion = async (question) => {
  const response = await api.post('/questions/ask', { question });
  return response.data;
};

export const getInvestigationHistory = async () => {
  const response = await api.get('/questions/history');
  return response.data;
};

export const getInvestigation = async (investigationId) => {
  const response = await api.get(`/questions/history/${investigationId}`);
  return response.data;
};
