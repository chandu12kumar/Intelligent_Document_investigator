import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ─── Shared error handler ──────────────────────────────────────────────────────
const attachInterceptor = (instance) => {
  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response) {
        const message =
          error.response.data?.detail ||
          error.response.data?.message ||
          `Server error: ${error.response.status}`;
        return Promise.reject(new Error(message));
      } else if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        return Promise.reject(
          new Error('Request timed out. The server is processing your request — please wait and try again.')
        );
      } else if (error.request) {
        return Promise.reject(
          new Error('Cannot connect to the backend server. Please verify the backend is running and CORS/network settings are correct.')
        );
      }
      return Promise.reject(error);
    }
  );
  return instance;
};

// ─── Standard API (30s timeout for normal calls) ──────────────────────────────
const api = attachInterceptor(axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
}));

// ─── Upload API (5 min timeout — model download + embedding on first cold start)
const uploadApi = attachInterceptor(axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes
}));

// ─── LLM API (3 min timeout for RAG + LLM synthesis) ─────────────────────────
const llmApi = attachInterceptor(axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000, // 3 minutes
  headers: { 'Content-Type': 'application/json' },
}));

// ─── Health ────────────────────────────────────────────────────────────────────
export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

// ─── Documents ────────────────────────────────────────────────────────────────
export const uploadDocument = async (file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await uploadApi.post('/documents/upload', formData, {
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
  const response = await llmApi.post('/questions/ask', { question });
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
