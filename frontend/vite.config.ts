import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 后端默认运行在 8000,dev 阶段把 /api 和 /storage 代理过去,避免跨域
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8010', changeOrigin: true },
      '/storage': { target: 'http://localhost:8010', changeOrigin: true },
    },
  },
});
