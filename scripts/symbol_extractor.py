"""symbol_extractor.py - 符号提取与索引构建

从 AST 解析结果构建：
1. 符号表：qualified_name -> Symbol
2. 反向索引：短名称 -> List[qualified_name]
3. 调用图：提取函数调用关系
4. 继承图：类继承/实现关系
5. 模块依赖图：import 关系
"""
import json
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import asdict

from ast_parser import (
    parse_directory, FileInfo, Symbol, SymbolType, Edge, EdgeType,
    Position
)


class SymbolIndex:
    """符号索引构建器"""

    def __init__(self):
        self.symbols: Dict[str, Symbol] = {}           # qualified_name -> Symbol
        self.by_short_name: Dict[str, List[str]] = defaultdict(list)  # 短名 -> 限定名列表
        self.by_type: Dict[SymbolType, List[str]] = defaultdict(list)  # 类型 -> 限定名列表
        self.by_module: Dict[str, List[str]] = defaultdict(list)       # 模块 -> 限定名列表
        self.edges: List[Edge] = []                    # 依赖边
        self.call_graph: Dict[str, Set[str]] = defaultdict(set)  # 调用关系
        self.inheritance_graph: Dict[str, Set[str]] = defaultdict(set)  # 继承关系
        self.module_deps: Dict[str, Set[str]] = defaultdict(set)   # 模块依赖

    def add_file(self, file_info: FileInfo):
        """添加文件解析结果到索引"""
        module_name = file_info.module_name

        for symbol in file_info.symbols:
            self._add_symbol(symbol, module_name)

        for imp in file_info.imports:
            self._add_import(module_name, imp)

        # 提取调用关系（需要二次遍历 AST，这里简化处理）
        self._extract_calls_from_symbols(file_info)

    def _add_symbol(self, symbol: Symbol, module_name: str):
        """添加符号到索引"""
        qn = symbol.qualified_name
        self.symbols[qn] = symbol
        self.by_short_name[symbol.name].append(qn)
        self.by_type[symbol.symbol_type].append(qn)
        self.by_module[module_name].append(qn)

        # 继承边
        for base in symbol.bases:
            self.edges.append(Edge(
                source=qn,
                target=base,
                edge_type=EdgeType.INHERITS,
            ))
            self.inheritance_graph[qn].add(base)

        # 实现 Protocol 边
        for impl in symbol.implements:
            self.edges.append(Edge(
                source=qn,
                target=impl,
                edge_type=EdgeType.IMPLEMENTS,
            ))

        # 装饰器边
        for deco in symbol.decorators:
            # 尝试解析装饰器指向的符号
            self.edges.append(Edge(
                source=qn,
                target=deco,
                edge_type=EdgeType.DECORATES,
            ))

    def _add_import(self, module_name: str, imp: Dict[str, Any]):
        """添加导入依赖"""
        if imp["type"] == "import":
            self.module_deps[module_name].add(imp["module"])
        elif imp["type"] == "from_import":
            target = f"{imp['module']}.{imp['name']}" if imp["module"] else imp["name"]
            self.module_deps[module_name].add(target)

    def _extract_calls_from_symbols(self, file_info: FileInfo):
        """从符号中提取调用关系（简化版：基于类型注解和返回类型推断）"""
        # 这里只做基础推断，完整调用图需要二次遍历 AST
        for symbol in file_info.symbols:
            # 返回类型引用
            if symbol.return_type:
                self.edges.append(Edge(
                    source=symbol.qualified_name,
                    target=symbol.return_type,
                    edge_type=EdgeType.RETURNS,
                ))
            # 参数类型引用
            for param in symbol.parameters:
                if param.get("type"):
                    self.edges.append(Edge(
                        source=symbol.qualified_name,
                        target=param["type"],
                        edge_type=EdgeType.USES_TYPE,
                    ))

    def build_call_graph(self, file_infos: Dict[str, FileInfo]):
        """构建完整调用图（需要完整 AST 遍历，这里占位）"""
        # TODO: 实现完整的函数调用提取
        # 需要遍历每个函数体内的 Call 节点
        pass

    def to_json(self) -> Dict[str, Any]:
        """导出为 JSON 可序列化字典"""
        return {
            "symbols": {qn: s.to_dict() for qn, s in self.symbols.items()},
            "by_short_name": dict(self.by_short_name),
            "by_type": {k.value: v for k, v in self.by_type.items()},
            "by_module": dict(self.by_module),
            "edges": [e.to_dict() for e in self.edges],
            "call_graph": {k: list(v) for k, v in self.call_graph.items()},
            "inheritance_graph": {k: list(v) for k, v in self.inheritance_graph.items()},
            "module_deps": {k: list(v) for k, v in self.module_deps.items()},
        }

    def save(self, output_path: Path):
        """保存到文件"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_json(), f, ensure_ascii=False, indent=2)


def build_symbol_index(root_dirs: List[Path],
                       exclude_dirs: Set[str] = None) -> SymbolIndex:
    """构建多目录符号索引"""
    index = SymbolIndex()

    for root in root_dirs:
        print(f"解析目录: {root}")
        files = parse_directory(root, exclude_dirs=exclude_dirs)
        print(f"  发现 {len(files)} 个 Python 文件")

        for path, file_info in files.items():
            if file_info.parse_errors:
                print(f"  ⚠️ {path}: {file_info.parse_errors}")
            index.add_file(file_info)

    print(f"索引构建完成: {len(index.symbols)} 符号, {len(index.edges)} 边")
    return index


if __name__ == "__main__":
    import sys
    roots = [Path(p) for p in sys.argv[1:]] if len(sys.argv) > 1 else [Path(".")]
    index = build_symbol_index(roots)
    index.save(Path("symbols_index.json"))
    print(f"已保存到 symbols_index.json")