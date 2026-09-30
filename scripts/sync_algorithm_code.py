#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sync_algorithm_code.py - 算法代码库同步主脚本

功能：
1. 解析两套代码库（原始 Pipeline + 整理版算法库）的 AST
2. 提取符号、构建索引、生成拓扑图
3. 解析 Protocol 契约、检查实现符合度
4. 扫描后端实现、建立组件映射
5. 输出静态 JSON 到 frontend/public/algorithm-map/ 供前端加载

用法：
    python scripts/sync_algorithm_code.py --full          # 全量同步
    python scripts/sync_algorithm_code.py --incremental   # 增量同步（默认）
    python scripts/sync_algorithm_code.py --watch         # 监听模式（开发用）
"""
import argparse
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
import sys

# 添加脚本目录到路径
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from ast_parser import parse_directory, FileInfo
from symbol_extractor import SymbolIndex, build_symbol_index
from contract_parser import ContractParser, parse_all_contracts
from implementation_mapper import ImplementationMapper, scan_all_implementations


# 代码库路径配置
CODE_ROOTS = {
    "github": Path(r"D:\研\土木水利\论文\代码\github"),
    "algorithm": Path(r"D:\Documents\Obsidian\O1\桥梁健康系统\Project\p11_多桥梁CPDV看板\算法代码"),
    "backend_framework": Path(r"D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend_framework"),
    "backends": Path(r"D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backends"),
    # 统一算法代码库 (项目内，按 Pipeline 组织，动态可修改)
    "unified": Path(r"D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\algorithm-code"),
}

OUTPUT_DIR = Path(r"D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend\public\algorithm-map")
CACHE_DIR = OUTPUT_DIR / ".cache"

EXCLUDE_DIRS = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules", "dist", "build", ".pytest_cache", ".mypy_cache"}


@dataclass
class SyncStats:
    """同步统计信息"""
    start_time: float
    end_time: float = 0
    files_parsed: int = 0
    symbols_extracted: int = 0
    contracts_parsed: int = 0
    implementations_found: int = 0
    backends_scanned: int = 0
    components_registered: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> Dict:
        return asdict(self)


def compute_file_hash(file_path: Path) -> str:
    """计算文件 MD5 哈希"""
    try:
        return hashlib.md5(file_path.read_bytes()).hexdigest()
    except Exception:
        return ""


def load_cache() -> Dict[str, str]:
    """加载增量缓存：文件路径 -> 哈希"""
    cache_file = CACHE_DIR / "file_hashes.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache: Dict[str, str]):
    """保存增量缓存"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "file_hashes.json"
    cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def get_changed_files(root: Path, cache: Dict[str, str], full: bool = False) -> Tuple[List[Path], Dict[str, str]]:
    """获取变更文件列表，返回 (changed_files, new_cache)"""
    new_cache = {}
    changed = []

    for file_path in root.rglob("*.py"):
        if any(ex in file_path.parts for ex in EXCLUDE_DIRS):
            continue
        if file_path.name.startswith("."):
            continue

        rel_path = str(file_path.relative_to(root))
        file_hash = compute_file_hash(file_path)
        new_cache[rel_path] = file_hash

        if full or rel_path not in cache or cache[rel_path] != file_hash:
            changed.append(file_path)

    return changed, new_cache


def sync_library(name: str, root: Path, cache: Dict[str, str], full: bool,
                 symbol_index: SymbolIndex, stats: SyncStats) -> Dict[str, FileInfo]:
    """同步单个代码库"""
    print(f"\n=== 同步代码库: {name} ({root}) ===")

    if not root.exists():
        msg = f"代码库不存在: {root}"
        print(f"[WARN] {msg}")
        stats.warnings.append(msg)
        return {}

    if full:
        print("  全量模式: 解析所有文件")
        files = parse_directory(root, exclude_dirs=EXCLUDE_DIRS)
    else:
        changed, new_cache = get_changed_files(root, cache, full)
        cache.update(new_cache)
        print(f"  增量模式: {len(changed)} 个变更文件 / 总计 {len(new_cache)} 文件")
        if changed:
            files = {}
            for f in changed:
                # 单文件解析
                from ast_parser import ASTParser
                parser = ASTParser()
                files[str(f)] = parser.parse_file(f)
        else:
            print("  无变更，跳过")
            return {}

    stats.files_parsed += len(files)
    print(f"  解析完成: {len(files)} 文件")

    # 添加到符号索引
    for path, file_info in files.items():
        if file_info.parse_errors:
            stats.warnings.append(f"{name}:{path}: {file_info.parse_errors}")
        symbol_index.add_file(file_info)

    stats.symbols_extracted = len(symbol_index.symbols)
    return files


def main():
    parser = argparse.ArgumentParser(description="算法代码库同步工具")
    parser.add_argument("--full", action="store_true", help="全量同步（忽略缓存）")
    parser.add_argument("--incremental", action="store_true", help="增量同步（默认）")
    parser.add_argument("--watch", action="store_true", help="监听模式（持续监听文件变化）")
    parser.add_argument("--only", nargs="+", choices=list(CODE_ROOTS.keys()), help="只同步指定代码库")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help="输出目录")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    full_sync = args.full or not args.incremental
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = SyncStats(start_time=time.time())
    cache = {} if full_sync else load_cache()
    symbol_index = SymbolIndex()

    print(f"[START] 算法代码库同步启动 ({'全量' if full_sync else '增量'}模式)")
    print(f"输出目录: {output_dir}")

    # 目标代码库
    target_libs = args.only if args.only else list(CODE_ROOTS.keys())

    # 1. 同步各代码库，构建符号索引
    all_files = {}
    for lib_name in target_libs:
        root = CODE_ROOTS[lib_name]
        files = sync_library(lib_name, root, cache, full_sync, symbol_index, stats)
        all_files[lib_name] = files

    # 保存符号索引
    print(f"\n[SAVE] 保存符号索引 ({len(symbol_index.symbols)} 符号)...")
    symbol_index.save(output_dir / "symbols_index.json")

    # 保存拓扑图数据（用于前端 cytoscape）
    topology_data = {
        "nodes": [],
        "edges": [],
    }
    for qn, symbol in symbol_index.symbols.items():
        topology_data["nodes"].append({
            "id": qn,
            "label": symbol.name,
            "type": symbol.symbol_type.value,
            "module": symbol.qualified_name.split(".")[0] if "." in symbol.qualified_name else "unknown",
            "file": symbol.position.file,
            "line": symbol.position.line,
        })
    for edge in symbol_index.edges:
        topology_data["edges"].append({
            "source": edge.source,
            "target": edge.target,
            "type": edge.edge_type.value,
        })

    with open(output_dir / "topology.json", "w", encoding="utf-8") as f:
        json.dump(topology_data, f, ensure_ascii=False, indent=2)
    print(f"  拓扑图: {len(topology_data['nodes'])} 节点, {len(topology_data['edges'])} 边")

    # 2. 解析 Protocol 契约
    print(f"\n[LIST] 解析 Protocol 契约...")
    protocol_dir = CODE_ROOTS["backend_framework"] / "protocols"
    impl_dirs = [
        CODE_ROOTS["backends"],
        CODE_ROOTS["backend_framework"] / "adapters",
    ]
    contract_parser = parse_all_contracts(protocol_dir, impl_dirs)
    contract_parser.export_all(output_dir)
    stats.contracts_parsed = len(contract_parser.contracts)
    stats.implementations_found = sum(len(v) for v in contract_parser.implementations.values())
    print(f"  契约: {stats.contracts_parsed} 个, 实现: {stats.implementations_found} 个")

    # 3. 扫描后端实现
    print(f"\n[PLUG] 扫描后端实现...")
    impl_mapper = scan_all_implementations(CODE_ROOTS["backends"], output_dir)
    stats.backends_scanned = len(impl_mapper.backends)
    stats.components_registered = sum(len(b.components) for b in impl_mapper.backends.values())

    # 4. 生成搜索索引（用于前端 SymbolSearch）
    print(f"\n[SEARCH] 生成搜索索引...")
    search_index = {
        "symbols": [],
        "by_type": {},
        "by_module": {},
    }
    for qn, symbol in symbol_index.symbols.items():
        search_index["symbols"].append({
            "q": qn,
            "n": symbol.name,
            "t": symbol.symbol_type.value,
            "m": symbol.qualified_name.split(".")[0] if "." in symbol.qualified_name else "",
            "f": symbol.position.file,
            "l": symbol.position.line,
        })

    # 按类型分组
    for stype, qnames in symbol_index.by_type.items():
        search_index["by_type"][stype.value] = qnames

    # 按模块分组
    for mod, qnames in symbol_index.by_module.items():
        search_index["by_module"][mod] = qnames

    with open(output_dir / "search_index.json", "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)
    print(f"  搜索索引: {len(search_index['symbols'])} 符号")

    # 5. 生成库元数据
    print(f"\n[DOCS] 生成库元数据...")
    libraries_meta = []
    for lib_name in target_libs:
        root = CODE_ROOTS[lib_name]
        if root.exists():
            file_count = len(list(root.rglob("*.py")))
            libraries_meta.append({
                "id": lib_name,
                "name": lib_name.replace("_", " ").title(),
                "path": str(root),
                "file_count": file_count,
                "last_sync": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

    with open(output_dir / "libraries.json", "w", encoding="utf-8") as f:
        json.dump(libraries_meta, f, ensure_ascii=False, indent=2)

    # 6. 保存缓存
    if not full_sync:
        save_cache(cache)

    # 7. 完成统计
    stats.end_time = time.time()
    print(f"\n[OK] 同步完成! 耗时 {stats.duration:.1f}s")
    print(f"  文件解析: {stats.files_parsed}")
    print(f"  符号提取: {stats.symbols_extracted}")
    print(f"  契约解析: {stats.contracts_parsed}")
    print(f"  实现发现: {stats.implementations_found}")
    print(f"  后端扫描: {stats.backends_scanned}")
    print(f"  组件注册: {stats.components_registered}")
    if stats.errors:
        print(f"  [ERROR] 错误: {len(stats.errors)}")
    if stats.warnings:
        print(f"  [WARN] 警告: {len(stats.warnings)}")

    # 保存统计
    with open(output_dir / "sync_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats.to_dict(), f, ensure_ascii=False, indent=2)

    if args.watch:
        print("\n[WATCH] 进入监听模式... (Ctrl+C 退出)")
        try:
            while True:
                time.sleep(5)
                # TODO: 实现文件监听（watchdog）
                print("  检查变更...")
        except KeyboardInterrupt:
            print("\n[BYE] 监听结束")

    return 0


if __name__ == "__main__":
    from dataclasses import field
    sys.exit(main())