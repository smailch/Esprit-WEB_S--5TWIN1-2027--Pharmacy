import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// Le .env est lu dans Ahmed/ (partagé avec le backend). Le proxy évite tout souci de CORS.
export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, '..', 'VITE_'), ...process.env };
  return {
    plugins: [react()],
    envDir: '..',
    server: {
      port: 5174,
      proxy: { '/api': { target: env.VITE_API_TARGET || 'http://localhost:8000', changeOrigin: true } },
    },
  };
});
