from typing import Optional
from fastapi import APIRouter, HTTPException
from services import cpdv_service, predict_service, multi_crack_service, random_service
import config
import executor

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/cpdv")
def cpdv(bridge: str = "bridge_01", depth: float = 0.2, distances: str = "5,10,15,20,25"):
    try:
        dists = [float(x) for x in distances.split(",")]
        return cpdv_service.compute_cpdv(bridge, depth, dists, {}, config.DATA_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict")
def predict(model: str = "outputs/models/cracknet.json",
            input_data: str = "outputs/data/verify_data.npz"):
    try:
        return predict_service.predict_single(model, input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/multi-crack")
def multi_crack(model: str = "outputs/models/multi_crack_dual_retrained.pth",
                input_data: str = "outputs/data/multi_condition.npz"):
    try:
        return multi_crack_service.predict_multi_crack(model, input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/random")
def random_cond(mode: str = "single", n_samples: int = 50, positions: str = "5,10,15,20"):
    try:
        poss = [float(x) for x in positions.split(",")] if positions else []
        return random_service.random_condition(mode, n_samples, poss)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify")
def verify():
    try:
        return {"ok": True, "msg": executor.verify_import()}
    except Exception as e:
        return {"ok": False, "msg": str(e)}
