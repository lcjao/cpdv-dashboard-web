"""CPDV 信号懒加载 API"""
from fastapi import APIRouter, HTTPException
from data_loader import load_bridge_signals, load_registry, load_dashboard_merged, load_records

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/{bridge_id}")
async def get_bridge_signals(bridge_id: str):
    """获取桥梁的 CPDV 信号数据（懒加载）"""
    signals = load_bridge_signals(bridge_id)
    
    if signals is None:
        raise HTTPException(status_code=404, detail=f"桥梁 {bridge_id} 无信号数据")
    
    return {
        "bridge_id": bridge_id,
        **signals
    }


@router.post("/refresh")
async def refresh_all_data():
    """完整刷新：看板数据 + 信号数据 + 实验记录"""
    from datetime import datetime, timezone
    
    # 1. 加载合并的看板数据
    merged = load_dashboard_merged()
    
    # 2. 批量加载所有桥梁的信号数据
    all_signals = {}
    reg = load_registry()
    bridges = reg.get("bridges", [])
    for b in bridges:
        bid = b.get("id")
        signals = load_bridge_signals(bid)
        if signals:
            all_signals[bid] = signals
    
    # 3. 加载实验记录
    all_records = load_records()
    
    # 4. 组装响应
    result = {
        "dashboard": merged,
        "signals": all_signals,
        "records": all_records[-50:] if all_records else [],
        "bridge_count": len(bridges),
        "record_count": len(all_records),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    
    return result
