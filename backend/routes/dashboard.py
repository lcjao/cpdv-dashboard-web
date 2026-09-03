from fastapi import APIRouter
from data_loader import load_dashboard_data

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard():
    """读取看板数据（兼容 dashboard_data.js 结构）"""
    return load_dashboard_data()
