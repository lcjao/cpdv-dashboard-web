from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from data_loader import load_registry, save_registry
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
    bridge = {
        "id": f"bridge_{len(reg['bridges'])+1:02d}",
        "name": req.name,
        "params": merged,
        "status": "registered",
        "last_updated": None,
    }
    reg["bridges"].append(bridge)
    save_registry(reg)
    return bridge
