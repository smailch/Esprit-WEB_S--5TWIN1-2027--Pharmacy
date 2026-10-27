import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// En développement, /api est redirigé vers le back-end FastAPI (port 8000) : pas de souci de CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
});
