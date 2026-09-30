"""外部算法代码文件操作 API。
支持两个代码根目录：
- CODE_ROOT: 原始 bridge_crack_id pipeline (D:/研/土木水利/论文/代码/github) - 后端 subprocess 实际执行
- ALGORITHM_CODE_ROOT: 整理后的纯算法模块 (D:/Documents/Obsidian/.../算法代码) - 可 import 复用、前端浏览
"""
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

import config

router = APIRouter(prefix="/api/external-code", tags=["external-code"])

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'.py', '.txt', '.md', '.yaml', '.yml', '.json', '.toml', '.cfg', '.ini'}

# 两个代码根目录
CODE_ROOT = Path(config.CODE_ROOT).resolve()
ALGORITHM_CODE_ROOT = Path(config.ALGORITHM_CODE_ROOT).resolve()

# 根目录类型标签（用于前端显示）
ROOT_LABELS = {
    "pipeline": "🔧 原始 Pipeline (后端执行)",
    "algorithm": "📚 纯算法库 (可 import 复用)",
}

# 当前使用的根目录（默认显示纯算法库）
DEFAULT_ROOT = "algorithm"  # "pipeline" 或 "algorithm"


def _get_root(root_type: str) -> Path:
    """根据类型返回对应的根路径。"""
    if root_type == "pipeline":
        return CODE_ROOT
    elif root_type == "algorithm":
        return ALGORITHM_CODE_ROOT
    else:
        raise HTTPException(status_code=400, detail=f"未知的根目录类型: {root_type}，可选: pipeline, algorithm")


def _resolve_safe_path(rel_path: str, root: Path) -> Path:
    """解析相对路径并确保在指定根目录内（防止路径遍历攻击）。"""
    # 规范化路径
    rel_path = rel_path.lstrip('/')
    target = (root / rel_path).resolve()
    # 安全检查：必须在根目录树内
    try:
        target.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=403, detail=f"路径超出 {root} 范围")
    return target


def _list_files_recursive(dir_path: Path, root: Path) -> list:
    """递归列出目录下所有允许的文件。"""
    result = []
    try:
        for entry in sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if entry.is_dir():
                # 递归子目录
                children = _list_files_recursive(entry, root)
                if children:  # 只显示非空目录
                    result.append({
                        "name": entry.name,
                        "type": "folder",
                        "path": str(entry.relative_to(root)),
                        "children": children,
                    })
            elif entry.is_file() and entry.suffix.lower() in ALLOWED_EXTENSIONS:
                result.append({
                    "name": entry.name,
                    "type": "file",
                    "path": str(entry.relative_to(root)),
                    "size": entry.stat().st_size,
                    "modified": entry.stat().st_mtime,
                })
    except PermissionError:
        pass
    return result


@router.get("/tree")
def get_file_tree(root: str = Query(DEFAULT_ROOT, description="代码根目录类型: pipeline(原始Pipeline) 或 algorithm(纯算法库)")):
    """获取指定根目录下的文件树（仅允许的扩展名）。"""
    root_path = _get_root(root)
    if not root_path.exists():
        raise HTTPException(status_code=404, detail=f"根目录不存在: {root_path}")
    tree = _list_files_recursive(root_path, root_path)
    return {
        "root": str(root_path),
        "root_type": root,
        "root_label": ROOT_LABELS.get(root, root),
        "tree": tree
    }


class ReadFileReq(BaseModel):
    path: str  # 相对于 CODE_ROOT 的路径


@router.get("/read")
def read_file(path: str = Query(..., description="相对于根目录的文件路径"), root: str = Query(DEFAULT_ROOT, description="代码根目录类型: pipeline 或 algorithm")):
    """读取外部代码文件内容。"""
    root_path = _get_root(root)
    target = _resolve_safe_path(path, root_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    if target.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="不支持的文件类型")
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            content = target.read_text(encoding="gbk")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取文件失败: {e}")
    return {
        "path": path,
        "root_type": root,
        "name": target.name,
        "content": content,
        "size": target.stat().st_size,
        "modified": target.stat().st_mtime,
    }


class WriteFileReq(BaseModel):
    path: str
    content: str
    root: str = DEFAULT_ROOT


@router.post("/write")
def write_file(req: WriteFileReq):
    """写入外部代码文件（仅允许覆盖现有文件，不允许创建新文件，防止误操作）。"""
    root_path = _get_root(req.root)
    target = _resolve_safe_path(req.path, root_path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="文件不存在，不允许创建新文件")
    if not target.is_file():
        raise HTTPException(status_code=403, detail="目标不是文件")
    if target.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="不支持的文件类型")
    try:
        # 备份原文件
        backup = target.with_suffix(target.suffix + ".bak")
        if target.exists():
            backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
        target.write_text(req.content, encoding="utf-8")
        return {"ok": True, "path": req.path, "root_type": req.root, "backup": str(backup.relative_to(root_path))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入失败: {e}")


@router.get("/list")
def list_files(dir_path: str = Query("", description="相对于根目录的目录路径"), root: str = Query(DEFAULT_ROOT, description="代码根目录类型: pipeline 或 algorithm")):
    """列出指定目录下的文件（非递归）。"""
    root_path = _get_root(root)
    target = _resolve_safe_path(dir_path, root_path) if dir_path else root_path
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="目录不存在")
    files = []
    for entry in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
        if entry.is_dir():
            files.append({"name": entry.name, "type": "folder", "path": str(entry.relative_to(root_path))})
        elif entry.is_file() and entry.suffix.lower() in ALLOWED_EXTENSIONS:
            files.append({
                "name": entry.name,
                "type": "file",
                "path": str(entry.relative_to(root_path)),
                "size": entry.stat().st_size,
                "modified": entry.stat().st_mtime,
            })
    return {"dir": dir_path or ".", "root_type": root, "files": files}