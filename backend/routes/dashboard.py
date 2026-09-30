from fastapi import APIRouter
from data_loader import load_dashboard_merged, load_dashboard_data, merge_legacy_bridges

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard():
    """读取看板数据（G8：registry + records 合并，再并入 legacy 信号数据）。

    返回结构与前端 types.ts 中的 DashboardData 保持一致。
    合并策略：registry 注册桥在前；未注册的 legacy dashboard_data.js 桥
    追加在后（带完整 CPDV 信号，保证看板 CPDV 图始终有真实数据可展示）。
    """
    merged = load_dashboard_merged()
    legacy = load_dashboard_data()
    merged = merge_legacy_bridges(merged, legacy)
    merged["meta"] = {
        **merged.get("meta", {}),
        "source": "registry+records+legacy(merged)",
    }
    return merged
