import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// G14/G17 配套：Vite 代理的 backend 端口。
// 之前硬编码 8000 但实际后端跑在 8765，导致 /api 请求被发到无服务的端口，
// 看板 fetch 失败、UI 显示空白/缺数据。改成读 env 默认 8765。
const API_TARGET = process.env.VITE_API_TARGET || 'http://127.0.0.1:8765';
console.log('[Vite Config] API_TARGET:', API_TARGET);

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    fs: {
      // 允许访问 frontend 之外的项目根（sample_data 示例数据位于项目根）
      allow: [resolve(__dirname, '..')],
    },
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
      '/ws': { target: API_TARGET.replace(/^http/, 'ws'), ws: true },
    },
  },
});
