export function connectStatus(cb: (msg: any) => void): () => void {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws/status`);
  ws.onmessage = e => {
    try {
      cb(JSON.parse(e.data));
    } catch {
      /* ignore */
    }
  };
  return () => ws.close();
}