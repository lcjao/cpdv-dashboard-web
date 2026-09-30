/**
 * 进度订阅客户端（评审 G7）。
 * 通过 WS /ws/progress?tags=train,cpdv 接收实时进度事件，
 * 并通过 onProgress / onError callback 给上层。
 */

export type ProgressEvent = {
  tag: string;
  stage: string;
  message: string;
  percent?: number;
  [k: string]: unknown;
};

export type ProgressHandler = (evt: ProgressEvent) => void;
export type WSErrorHandler = (e: Event) => void;

/** G7 — 订阅一个或多个 tag 的进度事件，自动指数退避重连。 */
export class ProgressSubscriber {
  private ws: WebSocket | null = null;
  private retryAttempt = 0;
  private alive = true;

  constructor(
    private tags: string[] = ['*'],
    private onProgress: ProgressHandler = () => {},
    private onError: WSErrorHandler = () => {},
  ) {}

  connect(baseUrl: string = '') {
    if (!this.alive) return;
    const wsBase = baseUrl || (typeof window !== 'undefined' ? window.location.origin : '');
    const url = wsBase.replace(/^http/, 'ws') + `/ws/progress?tags=${this.tags.join(',')}`;
    this.ws = new WebSocket(url);
    this.ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data?.type === 'pong' || data?.type === 'hello') return;
        this.onProgress(data as ProgressEvent);
      } catch {
        /* ignore non-JSON */
      }
    };
    this.ws.onerror = (e) => this.onError(e);
    this.ws.onclose = () => {
      if (!this.alive) return;
      this.retryAttempt++;
      const delay = Math.min(30000, 1000 * Math.pow(1.5, this.retryAttempt));
      setTimeout(() => this.connect(baseUrl), delay);
    };
  }

  disconnect() {
    this.alive = false;
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
    }
  }
}

/** 旧 ws/status 连接（heartbeat）。保留向后兼容。 */
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
