"""WebSocket 通道 + 进度广播。

G7 实现：
- /ws/progress?tags=train,cpdv — 订阅一个或多个 tag 的进度事件
- emit(tag, stage, message, percent) — 从任何线程触发进度事件
- 自动重放最近 200 条事件，新连接可一次性收到完整状态
- 所有 WS 在主 asyncio 循环上推送，避免跨线程 send_json
"""
import asyncio
import collections
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState

router = APIRouter()


class ProgressBroadcaster:
    """维护一组 (WebSocket, subscribed_tags) 订阅者，支持同步 emit。"""

    def __init__(self):
        self.active: list[tuple] = []  # [(ws, set[str])]
        self.history: collections.deque = collections.deque(maxlen=200)
        self._pending: collections.deque = collections.deque()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, tags: set):
        await ws.accept()
        self.active.append((ws, tags))
        # 重放历史，让新连接立即看到最近 20 条事件
        for evt in list(self.history)[-20:]:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(evt)
            except Exception:
                break

    def disconnect(self, ws: WebSocket):
        self.active = [(w, t) for (w, t) in self.active if w is not ws]

    async def broadcast_one(self, msg: dict):
        """Broadcast single event to subscribers matching tag filters."""
        async with self._lock:
            tag = msg.get("tag", "*")
            self.history.append(msg)
            dead = []
            for ws, ws_tags in self.active:
                if ws.client_state != WebSocketState.CONNECTED:
                    dead.append(ws)
                    continue
                # 订阅匹配：事件 tag '*' 全部接受；订阅 '*' 也全部接受；否则集合包含
                if tag == "*" or "*" in ws_tags or tag in ws_tags:
                    try:
                        await ws.send_json(msg)
                    except Exception:
                        dead.append(ws)
            for ws in dead:
                self.disconnect(ws)

    async def flush(self):
        """把 pending 队列的事件 flush 出去。"""
        n = 0
        while self._pending:
            msg = self._pending.popleft()
            await self.broadcast_one(msg)
            n += 1
        return n


progress = ProgressBroadcaster()


# ────────────────────────────────────────────────────────────────────
# 同步 emit 入口（线程安全，可从 sync 路由 / 子进程调用）
# ────────────────────────────────────────────────────────────────────
def emit(tag: str, stage: str, message: str = "",
         percent: float = None, **extra):
    """Emit a progress event. tag like 'cpdv'/'train'/'random'/'*'.

    这个同步函数把事件 push 到 pending 队列，main asyncio 循环
    的 watchdog 会周期 flush 到所有匹配的 ws 订阅者。
    """
    msg = {"tag": tag, "stage": stage, "message": message}
    if percent is not None:
        msg["percent"] = float(percent)
    msg.update(extra)
    progress._pending.append(msg)


def emit_json(msg: dict):
    """原生 emit：传入已经构造好的 event dict。"""
    progress._pending.append(msg)


# ────────────────────────────────────────────────────────────────────
# 主 asyncio watchdog：周期性 flush pending 队列
# ────────────────────────────────────────────────────────────────────
async def _progress_watchdog(interval: float = 0.5):
    while True:
        try:
            await asyncio.sleep(interval)
            if progress._pending:
                await progress.flush()
        except asyncio.CancelledError:
            return
        except Exception:
            # watchdog 自己的异常不能影响主循环
            await asyncio.sleep(interval)


@router.on_event("startup")
async def startup_watchdog():
    """App 启动时启动 watchdog。"""
    asyncio.create_task(_progress_watchdog())


# ────────────────────────────────────────────────────────────────────
# WebSocket 端点
# ────────────────────────────────────────────────────────────────────
@router.websocket("/ws/status")
async def ws_status(ws: WebSocket):
    """原状态端点，向所有连接 broadcast。"""
    await ws.accept()
    await ws.send_json({"type": "hello", "msg": "cpdv-dashboard status"})
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/progress")
async def ws_progress(ws: WebSocket, tags: str = Query(default="*")):
    """进度订阅端点。?tags=train,cpdv 仅订阅这两类。"""
    if tags == "*" or not tags.strip():
        tag_set = {"*"}
    else:
        tag_set = {t.strip() for t in tags.split(",") if t.strip()}
    await progress.connect(ws, tag_set)
    try:
        # 客户端 → 服务端的入栈消息暂不处理，只保持连接
        while True:
            data = await ws.receive_text()
            # 允许客户端 ping/pong/filter update
            try:
                d = json.loads(data)
                if d.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
                elif d.get("type") == "filter" and isinstance(d.get("tags"), list):
                    new_tags = set(d["tags"]) | {"*"}
                    # 更新订阅 tags
                    progress.active = [(w, new_tags) if w is ws else (w, t) for (w, t) in progress.active]
                    await ws.send_json({"type": "filter_ack", "tags": list(new_tags)})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        progress.disconnect(ws)
