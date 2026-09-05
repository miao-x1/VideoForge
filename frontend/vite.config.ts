import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 后端默认运行在 8000,dev 阶段把 /api 和 /storage 代理过去,避免跨域
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      // 必须用 127.0.0.1：Windows 上 localhost 常解析到 ::1，
      // 后端只绑 IPv4 时，验证码等 /api 请求会打到错误进程并 404。
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/storage': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
});
