// Central backend URL config. Override with VITE_API_URL in frontend/.env.local
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_BASE = API_BASE.replace(/^http/, 'ws');
