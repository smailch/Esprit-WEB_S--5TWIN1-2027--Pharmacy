import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Modules Pathologie + Personne (Ahmed) : back-end FastAPI sur le port 8001, page /ahmed.html
      '/api-ahmed': {
        target: process.env.VITE_AHMED_BACKEND_URL || 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api-ahmed/, '/api'),
      },
    },
  },
  build: {
    rollupOptions: {
      input: { main: resolve(__dirname, 'index.html'), ahmed: resolve(__dirname, 'ahmed.html') },
    },
  },
});
