import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// En développement, /api est redirigé vers le back-end FastAPI (port 8000) : pas de souci de CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Modules Pathologie + Personne (Ahmed) : à garder AVANT '/api' (sinon '/api' capte aussi '/api-ahmed/…').
      '/api-ahmed': {
        target: process.env.VITE_AHMED_BACKEND_URL || 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api-ahmed/, '/api'),
      },
      '/api': { target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    rollupOptions: {
      input: { main: resolve(__dirname, 'index.html'), ahmed: resolve(__dirname, 'ahmed.html') },
    },
  },
});
