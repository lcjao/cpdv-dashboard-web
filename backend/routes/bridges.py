from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time
from data_loader import load_registry, save_registry, clean_associated_data
from scheduler import validate_params

router = APIRouter(prefix="/api/bridges", tags=["bridges"])

DEFAULT_PARAMS = {
    "mv": 5000, "kv": 100000, "cv": 5000, "V": 2, "L": 30,
    "E": 3.0e10, "I": 0.1, "m": 400, "EL": 30, "depth": 0.8,
    "width": 0.25, "n_modes": 3, "kexi": 0.1, "deltat": 0.005,
    "road_type": "b",
}


class RegisterReq(BaseModel):
    name: str
    params: Optional[dict] = None


def _next_bridge_id(reg: dict) -> str:
    """G16：用持久计数器取下一个 id（避免按 len() 派生导致删除后撞号）。

    registry 顶层保留 `_next_id` 字段，初始为 1。
    每次发号后自增 1 并写回，保证删除中间桥后不会复用旧 id。
    """
    nxt = reg.get("_next_id")
    if not isinstance(nxt, int) or nxt < 1:
        # 兜底：用现有 id 数字部分的最大值 +1（迁移旧数据时）
        nxt = 1
        for b in reg.get("bridges", []):
            bid = b.get("id", "")
            if isinstance(bid, str) and bid.startswith("bridge_"):
                try:
                    n = int(bid.split("_", 1)[1])
                    if n >= nxt:
                        nxt = n + 1
                except ValueError:
                    pass
    bid = f"bridge_{nxt:02d}"
    reg["_next_id"] = nxt + 1
    return bid


@router.get("")
def list_bridges():
    return load_registry().get("bridges", [])


@router.post("/register")
def register_bridge(req: RegisterReq):
    reg = load_registry()
    # 参数校验
    merged = {**DEFAULT_PARAMS, **(req.params or {})}
    ok, msg = validate_params(merged)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    name = (req.name or "").strip()
    # 幂等：同名桥梁已存在 → 更新参数而非追加（避免重复注册产生 bridge_08/bridge_09 这类重名项）
    existing = next((b for b in reg["bridges"]
                     if name and (b.get("name") or "").strip() == name), None)
    if existing is not None:
        existing["params"] = merged
        existing["status"] = "registered"
        existing["last_updated"] = time.time()
        save_registry(reg)
        return {**existing, "duplicated": True, "updated": True}

    bid = _next_bridge_id(reg)
    bridge = {
        "id": bid,
        "name": name,
        "params": merged,
        "status": "registered",
        "last_updated": None,
    }
    reg["bridges"].append(bridge)
    save_registry(reg)
    return {**bridge, "duplicated": False, "updated": False}


@router.delete("/{bridge_id}")
def delete_bridge(bridge_id: str):
    """删除桥梁及其关联数据（CPDV 信号、推理缓存、实验记录等）"""
    reg = load_registry()
    bridges = reg.get("bridges", [])
    idx = next((i for i, b in enumerate(bridges) if b.get("id") == bridge_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"桥梁 {bridge_id} 不存在")

    deleted = bridges.pop(idx)
    save_registry(reg)

    # 清理关联数据（看板 JSON、CPDV 图、推理缓存等）
    clean_associated_data(bridge_id)

    return {"ok": True, "deleted": {"id": bridge_id, "name": deleted.get("name")}}
