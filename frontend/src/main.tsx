import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './globals.css';

// ====== DEBUG: 全局错误捕获 + 把错误渲染到 root（让页面不再"一片空白"） ======
function renderError(err: unknown, source: string) {
  const root = document.getElementById('root')!;
  const msg = err instanceof Error
    ? `${err.name}: ${err.message}\n${(err.stack || '').split('\n').slice(0, 5).join('\n')}`
    : String(err);
  root.innerHTML = `
    <div style="font-family: Consolas, monospace; padding: 24px; color: #d94141; background: #fff5f5; border: 1px solid #d94141; border-radius: 8px; margin: 24px; white-space: pre-wrap;">
      <h2 style="margin: 0 0 12px; color: #b03030;">React mount failed</h2>
      <p style="color: #555;"><b>Source:</b> ${source}</p>
      <pre style="margin: 0;">${msg.replace(/[<>]/g, c => ({ '<': '&lt;', '>': '&gt;' }[c] || c))}</pre>
    </div>
  `;
  // 同时 console
  // eslint-disable-next-line no-console
  console.error(`[${source}]`, err);
}

window.addEventListener('error', (ev) => {
  renderError(ev.error || ev.message, 'window.onerror');
});
window.addEventListener('unhandledrejection', (ev) => {
  renderError(ev.reason, 'unhandledrejection');
});

try {
  const rootEl = document.getElementById('root');
  if (!rootEl) throw new Error('No #root element in index.html');
  createRoot(rootEl).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
} catch (err) {
  renderError(err, 'createRoot');
}