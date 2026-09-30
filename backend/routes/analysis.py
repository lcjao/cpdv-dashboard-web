from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import cpdv_service, predict_service, multi_crack_service, random_service, train_service, evaluate_service
import config
import executor

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/cpdv")
def cpdv(bridge: str = "bridge_01", depth: float = 0.2,
         distances: str = "5,10,15,20,25", depths: str = "",
         # 仿真参数覆盖（可选，来自 tool 调用或自然语言解析）
         mv: float = None, kv: float = None, cv: float = None,
         V: float = None, L: float = None, E: float = None,
         I: float = None, m: float = None, EL: float = None,
         width: float = None, n_modes: int = None,
         kexi: float = None, deltat: float = None,
         road_type: str = None):
    """流程 C1：计算 CPDV。

    G20 多裂缝模式：可选 `depths`（逗号分隔，与 distances 一一对应），
    如 ?bridge=bridge_01&distances=5,10,15&depths=0.2,0.3,0.25
    每个位置用各自深度计算；缺省退化为单深度模式（depth 作用于所有位置）。

    仿真参数可选覆盖：mv, kv, cv, V, L, E, I, m, EL, width, n_modes, kexi, deltat, road_type
    优先级：默认值 < 注册桥参数 < 本次请求参数
    """
    try:
        dists = [float(x) for x in distances.split(",")]
        depths_list = [float(x) for x in depths.split(",")] if depths.strip() else None
        if depths_list is not None and len(depths_list) != len(dists):
            raise ValueError(f"depths({len(depths_list)}) 数量必须与 distances({len(dists)}) 一致")

        # 收集仿真参数覆盖
        sim_overrides = {}
        for k, v in {
            "mv": mv, "kv": kv, "cv": cv, "V": V, "L": L, "E": E,
            "I": I, "m": m, "EL": EL, "width": width,
            "n_modes": n_modes, "kexi": kexi, "deltat": deltat,
            "road_type": road_type,
        }.items():
            if v is not None:
                sim_overrides[k] = v

        return cpdv_service.compute_cpdv(bridge, depth, dists, sim_overrides, config.DATA_DIR, depths=depths_list)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict")
def predict(model: str = "outputs/models/cracknet_aligned.json",
            input_data: str = "outputs/data/training_data.npz"):
    try:
        return predict_service.predict_single(model, input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/multi-crack")
def multi_crack(model: str = multi_crack_service.DEFAULT_MODEL,
                input_data: str = "outputs/data/multi_condition.npz",
                bridge: str = None):
    """多裂缝预测（流程C3）。bridge 指定注册桥 id/名称时：读该桥 cpdv_signals →
    组合信号单样本推理 → 解码真/伪裂缝 → 写回 registry，看板刷新即展示。"""
    try:
        return multi_crack_service.predict_multi_crack(model, input_data, bridge_id=bridge)
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


class TrainReq(BaseModel):
    model_type: str = "multi_crack"
    n_samples: int = 10000
    data: Optional[str] = None
    model: Optional[str] = None
    epochs: int = 100
    regenerate: bool = False
    bridge: Optional[str] = None  # 可选：指定桥梁，默认取第一座已注册桥


@router.post("/train")
def train(req: TrainReq):
    try:
        # 自动解析 bridge_id：优先用请求参数，其次取第一座已注册桥
        bridge_id = req.bridge
        if not bridge_id:
            from data_loader import load_registry
            reg = load_registry()
            bridges = reg.get("bridges", [])
            if bridges:
                bridge_id = bridges[0]["id"]
        return train_service.train_model(
            bridge_id=bridge_id,
            model_type=req.model_type, n_samples=req.n_samples,
            data=req.data, model=req.model, epochs=req.epochs,
            regenerate=req.regenerate,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluate")
def evaluate(
    bridge: str = None,
    model: str = evaluate_service.DEFAULT_MODEL,
    input_data: str = "outputs/data/multi_condition.npz",
    cls_threshold: float = 0.3,
    match_cost: float = 5.0,
    pos_threshold: float = 0.0,
):
    try:
        return evaluate_service.evaluate_model(
            bridge_id=bridge,
            model=model,
            input_data=input_data,
            cls_threshold=cls_threshold,
            match_cost=match_cost,
            pos_threshold=pos_threshold,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
