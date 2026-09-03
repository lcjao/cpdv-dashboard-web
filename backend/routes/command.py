from fastapi import APIRouter
from pydantic import BaseModel
from scheduler import parse_command

router = APIRouter(prefix="/api/command", tags=["command"])


class CmdReq(BaseModel):
    text: str


@router.post("")
def execute_command(req: CmdReq):
    parsed = parse_command(req.text)
    if not parsed:
        return {"action": "unknown", "text": req.text}
    action, full = parsed
    # 各 action 分发到对应 service；此处为骨架，关键 pipeline 调用走分析路由
    if action == "cpdv":
        return {"action": action, "hint": "CPDV 已触发，走 /api/analysis/cpdv"}
    if action == "predict":
        return {"action": action, "hint": "预测已触发，走 /api/analysis/predict"}
    if action == "multi_crack":
        return {"action": action, "hint": "多裂缝已触发，走 /api/analysis/multi-crack"}
    if action == "random_condition":
        return {"action": action, "hint": "随机工况已触发，走 /api/analysis/random"}
    if action in ("overview", "list", "register"):
        return {"action": action, "hint": f"{action} 操作完成"}
    return {"action": action, "hint": f"{action} 已识别"}
