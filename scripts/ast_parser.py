"""ast_parser.py - 通用 Python AST 解析器

支持标准库 ast + astroid 混合模式：
- ast: 标准库，零依赖，基础节点遍历
- astroid: 更强大，支持推断、装饰器解析、类层级
"""
import ast
import astroid
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import json


class SymbolType(Enum):
    """符号类型枚举"""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    IMPORT = "import"
    DECORATOR = "decorator"
    TYPE_ALIAS = "type_alias"
    PROTOCOL = "protocol"
    VARIABLE = "variable"


class EdgeType(Enum):
    """依赖边类型"""
    CALLS = "calls"           # 函数调用
    INHERITS = "inherits"     # 类继承
    IMPLEMENTS = "implements" # 实现 Protocol
    IMPORTS = "imports"       # 导入关系
    DECORATES = "decorates"   # 装饰器
    RETURNS = "returns"       # 返回类型
    USES_TYPE = "uses_type"   # 使用类型注解


@dataclass
class Position:
    """源码位置"""
    file: str
    line: int
    col: int
    end_line: Optional[int] = None
    end_col: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Symbol:
    """统一符号表示"""
    name: str
    qualified_name: str      # 模块.类.方法 完整限定名
    symbol_type: SymbolType
    position: Position
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    type_annotation: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)  # [{name, type, default}]
    return_type: Optional[str] = None
    bases: List[str] = field(default_factory=list)      # 继承的基类
    implements: List[str] = field(default_factory=list) # 实现的 Protocol
    is_async: bool = False
    is_property: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展字段

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["symbol_type"] = self.symbol_type.value
        d["position"] = self.position.to_dict()
        return d

    @property
    def short_name(self) -> str:
        """短名称（不含模块前缀）"""
        return self.qualified_name.split(".")[-1]


@dataclass
class Edge:
    """依赖关系边"""
    source: str      # 源符号 qualified_name
    target: str      # 目标符号 qualified_name
    edge_type: EdgeType
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["edge_type"] = self.edge_type.value
        return d


@dataclass
class FileInfo:
    """文件级信息"""
    path: str
    module_name: str
    hash: str
    mtime: float
    symbols: List[Symbol] = field(default_factory=list)
    imports: List[Dict[str, Any]] = field(default_factory=list)
    parse_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "module_name": self.module_name,
            "hash": self.hash,
            "mtime": self.mtime,
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": self.imports,
            "parse_errors": self.parse_errors,
        }


class ASTParser:
    """AST 解析器主类"""

    def __init__(self, use_astroid: bool = True):
        self.use_astroid = use_astroid
        self._astroid_cache: Dict[str, astroid.Module] = {}

    def parse_file(self, file_path: Path) -> FileInfo:
        """解析单个 Python 文件"""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return FileInfo(
                path=str(file_path),
                module_name=self._path_to_module(file_path),
                hash="",
                mtime=file_path.stat().st_mtime,
                parse_errors=[f"读取失败: {e}"],
            )

        file_hash = hashlib.md5(content.encode()).hexdigest()
        module_name = self._path_to_module(file_path)

        # 优先用 astroid 解析（更强大）
        if self.use_astroid:
            try:
                return self._parse_with_astroid(file_path, module_name, file_hash, content)
            except Exception as e:
                # 回退到标准库 ast
                pass

        # 标准库 ast 回退
        return self._parse_with_ast(file_path, module_name, file_hash, content)

    def _parse_with_astroid(self, file_path: Path, module_name: str, file_hash: str, content: str) -> FileInfo:
        """使用 astroid 解析"""
        # 构建 astroid 模块
        mod = astroid.parse(content, modname=module_name, path=str(file_path))

        symbols = []
        imports = []

        for node in mod.body:
            self._extract_symbols_astroid(node, module_name, symbols, imports, file_path)

        return FileInfo(
            path=str(file_path),
            module_name=module_name,
            hash=file_hash,
            mtime=file_path.stat().st_mtime,
            symbols=symbols,
            imports=imports,
        )

    def _parse_with_ast(self, file_path: Path, module_name: str, file_hash: str, content: str) -> FileInfo:
        """使用标准库 ast 解析（回退）"""
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return FileInfo(
                path=str(file_path),
                module_name=module_name,
                hash=file_hash,
                mtime=file_path.stat().st_mtime,
                parse_errors=[f"语法错误: {e}"],
            )

        symbols = []
        imports = []

        for node in tree.body:
            self._extract_symbols_ast(node, module_name, symbols, imports, file_path)

        return FileInfo(
            path=str(file_path),
            module_name=module_name,
            hash=file_hash,
            mtime=file_path.stat().st_mtime,
            symbols=symbols,
            imports=imports,
        )

    def _extract_symbols_astroid(self, node: astroid.NodeNG, module_name: str,
                                  symbols: List[Symbol], imports: List[Dict],
                                  file_path: Path, parent_class: Optional[str] = None):
        """astroid 节点提取符号"""
        pos = Position(
            file=str(file_path),
            line=node.lineno,
            col=node.col_offset,
            end_line=getattr(node, "end_lineno", None),
            end_col=getattr(node, "end_col_offset", None),
        )

        if isinstance(node, astroid.ClassDef):
            # 类定义
            decorators = [self._decorator_to_str(d) for d in node.decorators.nodes] if node.decorators else []
            bases = [b.as_string() for b in node.bases]

            # 检测是否为 Protocol
            is_protocol = any("Protocol" in b for b in bases) or any("protocol" in d.lower() for d in decorators)

            symbol = Symbol(
                name=node.name,
                qualified_name=f"{module_name}.{node.name}" if not parent_class else f"{parent_class}.{node.name}",
                symbol_type=SymbolType.PROTOCOL if is_protocol else SymbolType.CLASS,
                position=pos,
                docstring=astroid.util.get_docstring(node, clean=True),
                decorators=decorators,
                bases=bases,
                metadata={"methods": [], "attributes": []},
            )
            symbols.append(symbol)

            # 递归提取类内部方法/属性
            for item in node.body:
                self._extract_symbols_astroid(item, module_name, symbols, imports, file_path, parent_class=symbol.qualified_name)

        elif isinstance(node, astroid.FunctionDef):
            # 函数/方法定义
            decorators = [self._decorator_to_str(d) for d in node.decorators.nodes] if node.decorators else []

            # 参数解析
            params = []
            for arg in node.args.args:
                param_info = {"name": arg.name}
                if arg.annotation:
                    param_info["type"] = arg.annotation.as_string()
                params.append(param_info)

            # 返回类型
            return_type = node.returns.as_string() if node.returns else None

            # 判断方法类型
            is_method = parent_class is not None
            is_property = any("property" in d for d in decorators)
            is_classmethod = any("classmethod" in d for d in decorators)
            is_staticmethod = any("staticmethod" in d for d in decorators)

            symbol = Symbol(
                name=node.name,
                qualified_name=f"{module_name}.{node.name}" if not parent_class else f"{parent_class}.{node.name}",
                symbol_type=SymbolType.METHOD if is_method else SymbolType.FUNCTION,
                position=pos,
                docstring=astroid.util.get_docstring(node, clean=True),
                decorators=decorators,
                parameters=params,
                return_type=return_type,
                is_async=node.is_async(),
                is_property=is_property,
                is_classmethod=is_classmethod,
                is_staticmethod=is_staticmethod,
                metadata={"parent_class": parent_class},
            )
            symbols.append(symbol)

            # 如果是类方法，添加到父类元数据
            if parent_class:
                for s in symbols:
                    if s.qualified_name == parent_class:
                        s.metadata.setdefault("methods", []).append(symbol.qualified_name)

        elif isinstance(node, (astroid.Import, astroid.ImportFrom)):
            # 导入语句
            if isinstance(node, astroid.Import):
                for name, alias in node.names:
                    imports.append({
                        "type": "import",
                        "module": name,
                        "alias": alias,
                        "line": node.lineno,
                    })
            else:  # ImportFrom
                module = node.modname or ""
                for name, alias in node.names:
                    imports.append({
                        "type": "from_import",
                        "module": module,
                        "name": name,
                        "alias": alias,
                        "level": node.level,
                        "line": node.lineno,
                    })

        elif isinstance(node, astroid.Assign):
            # 类型别名、模块级变量
            for target in node.targets:
                if isinstance(target, astroid.Name):
                    symbol = Symbol(
                        name=target.name,
                        qualified_name=f"{module_name}.{target.name}",
                        symbol_type=SymbolType.VARIABLE,
                        position=pos,
                        type_annotation=getattr(target, "annotation", None).as_string() if getattr(target, "annotation", None) else None,
                    )
                    symbols.append(symbol)

    def _extract_symbols_ast(self, node: ast.AST, module_name: str,
                              symbols: List[Symbol], imports: List[Dict],
                              file_path: Path, parent_class: Optional[str] = None):
        """标准库 ast 提取符号（简化版，回退用）"""
        pos = Position(
            file=str(file_path),
            line=getattr(node, "lineno", 1),
            col=getattr(node, "col_offset", 0),
            end_line=getattr(node, "end_lineno", None),
            end_col=getattr(node, "end_col_offset", None),
        )

        if isinstance(node, ast.ClassDef):
            decorators = [self._ast_decorator_to_str(d) for d in node.decorator_list]
            bases = [self._ast_node_to_str(b) for b in node.bases]
            is_protocol = any("Protocol" in b for b in bases)

            symbol = Symbol(
                name=node.name,
                qualified_name=f"{module_name}.{node.name}" if not parent_class else f"{parent_class}.{node.name}",
                symbol_type=SymbolType.PROTOCOL if is_protocol else SymbolType.CLASS,
                position=pos,
                docstring=ast.get_docstring(node, clean=True),
                decorators=decorators,
                bases=bases,
                metadata={"methods": []},
            )
            symbols.append(symbol)

            for item in node.body:
                self._extract_symbols_ast(item, module_name, symbols, imports, file_path, parent_class=symbol.qualified_name)

        elif isinstance(node, ast.FunctionDef):
            decorators = [self._ast_decorator_to_str(d) for d in node.decorator_list]
            params = []
            for arg in node.args.args:
                param_info = {"name": arg.arg}
                if arg.annotation:
                    param_info["type"] = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else "<unknown>"
                params.append(param_info)

            return_type = ast.unparse(node.returns) if node.returns and hasattr(ast, "unparse") else None

            is_method = parent_class is not None
            is_property = any("property" in d for d in decorators)

            symbol = Symbol(
                name=node.name,
                qualified_name=f"{module_name}.{node.name}" if not parent_class else f"{parent_class}.{node.name}",
                symbol_type=SymbolType.METHOD if is_method else SymbolType.FUNCTION,
                position=pos,
                docstring=ast.get_docstring(node, clean=True),
                decorators=decorators,
                parameters=params,
                return_type=return_type,
                is_async=isinstance(node, ast.AsyncFunctionDef),
                is_property=is_property,
                metadata={"parent_class": parent_class},
            )
            symbols.append(symbol)

            if parent_class:
                for s in symbols:
                    if s.qualified_name == parent_class:
                        s.metadata.setdefault("methods", []).append(symbol.qualified_name)

        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    })
            else:
                for alias in node.names:
                    imports.append({
                        "type": "from_import",
                        "module": node.module or "",
                        "name": alias.name,
                        "alias": alias.asname,
                        "level": node.level,
                        "line": node.lineno,
                    })

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbol = Symbol(
                        name=target.id,
                        qualified_name=f"{module_name}.{target.id}",
                        symbol_type=SymbolType.VARIABLE,
                        position=pos,
                    )
                    symbols.append(symbol)

        # 递归处理子节点
        for child in ast.iter_child_nodes(node):
            if not isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Import, ast.ImportFrom, ast.Assign)):
                self._extract_symbols_ast(child, module_name, symbols, imports, file_path, parent_class)

    def _decorator_to_str(self, node: astroid.NodeNG) -> str:
        """astroid 装饰器转字符串"""
        try:
            return node.as_string()
        except Exception:
            return str(node)

    def _ast_decorator_to_str(self, node: ast.AST) -> str:
        """ast 装饰器转字符串"""
        try:
            return ast.unparse(node) if hasattr(ast, "unparse") else ast.dump(node)
        except Exception:
            return str(node)

    def _ast_node_to_str(self, node: ast.AST) -> str:
        """ast 节点转字符串"""
        try:
            return ast.unparse(node) if hasattr(ast, "unparse") else ast.dump(node)
        except Exception:
            return str(node)

    def _path_to_module(self, file_path: Path) -> str:
        """文件路径转模块名"""
        # 移除 .py 后缀，路径分隔符转点
        parts = file_path.with_suffix("").parts
        # 尝试找到包含 scripts/model/simulation 等的部分
        for i, part in enumerate(parts):
            if part in ("scripts", "model", "simulation", "backend_framework", "backends"):
                return ".".join(parts[i:])
        return ".".join(parts[-3:])  # 后3级作为模块名


def parse_directory(root: Path, pattern: str = "*.py",
                    exclude_dirs: Set[str] = None,
                    use_astroid: bool = True) -> Dict[str, FileInfo]:
    """批量解析目录下所有 Python 文件"""
    if exclude_dirs is None:
        exclude_dirs = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules", "dist", "build"}

    parser = ASTParser(use_astroid=use_astroid)
    results = {}

    for file_path in root.rglob(pattern):
        if any(ex in file_path.parts for ex in exclude_dirs):
            continue
        if file_path.name.startswith("."):
            continue

        file_info = parser.parse_file(file_path)
        results[str(file_path)] = file_info

    return results


if __name__ == "__main__":
    # 测试用
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    files = parse_directory(root)
    for path, info in files.items():
        print(f"{path}: {len(info.symbols)} symbols, {len(info.imports)} imports")
        if info.parse_errors:
            print(f"  Errors: {info.parse_errors}")