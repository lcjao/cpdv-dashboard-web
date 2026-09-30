"""contract_parser.py - Protocol 契约解析器

从 backend_framework/protocols/ 目录解析 Protocol 定义，生成：
1. 契约规范：必需属性、必需方法、参数/返回类型
2. 实现对比表：每个 Protocol 的所有实现类、符合度检查
3. 契约元数据：版本、作者、描述
"""
import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict

# 添加脚本目录到路径
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from ast_parser import Symbol, SymbolType


@dataclass
class ContractMethod:
    """契约方法规范"""
    name: str
    parameters: List[Dict[str, Any]]  # [{name, type, default, required}]
    return_type: Optional[str]
    is_async: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_property: bool = False
    docstring: Optional[str] = None
    raises: List[str] = field(default_factory=list)  # 抛出的异常
    preconditions: List[str] = field(default_factory=list)  # 前置条件
    postconditions: List[str] = field(default_factory=list)  # 后置条件


@dataclass
class ContractAttribute:
    """契约属性规范"""
    name: str
    type: str
    required: bool = True
    docstring: Optional[str] = None


@dataclass
class ProtocolContract:
    """Protocol 契约完整定义"""
    name: str
    qualified_name: str
    file_path: str
    docstring: Optional[str] = None
    required_attributes: List[ContractAttribute] = field(default_factory=list)
    required_methods: List[ContractMethod] = field(default_factory=list)
    optional_methods: List[ContractMethod] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)  # version, author 等

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file_path": self.file_path,
            "docstring": self.docstring,
            "required_attributes": [asdict(a) for a in self.required_attributes],
            "required_methods": [asdict(m) for m in self.required_methods],
            "optional_methods": [asdict(m) for m in self.optional_methods],
            "metadata": self.metadata,
        }


@dataclass
class ImplementationCheck:
    """实现符合度检查结果"""
    protocol: str
    implementation: str
    qualified_name: str
    file_path: str
    implements_all_required: bool
    missing_attributes: List[str] = field(default_factory=list)
    missing_methods: List[str] = field(default_factory=list)
    signature_mismatches: List[Dict[str, Any]] = field(default_factory=list)
    extra_methods: List[str] = field(default_factory=list)
    score: float = 0.0  # 0-1 符合度评分

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ContractParser:
    """Protocol 契约解析器"""

    def __init__(self):
        self.contracts: Dict[str, ProtocolContract] = {}
        self.implementations: Dict[str, List[ImplementationCheck]] = defaultdict(list)

    def parse_protocol_file(self, file_path: Path) -> List[ProtocolContract]:
        """解析单个 Protocol 文件"""
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        contracts = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef) and self._is_protocol(node):
                contract = self._parse_protocol_class(node, file_path)
                contracts.append(contract)
                self.contracts[contract.qualified_name] = contract

        return contracts

    def _is_protocol(self, node: ast.ClassDef) -> bool:
        """判断是否为 Protocol 类"""
        # 检查基类是否包含 Protocol
        for base in node.bases:
            if isinstance(base, ast.Name) and "Protocol" in base.id:
                return True
            if isinstance(base, ast.Attribute):
                if "Protocol" in ast.unparse(base) if hasattr(ast, "unparse") else False:
                    return True
        # 检查装饰器
        for deco in node.decorator_list:
            if isinstance(deco, ast.Name) and "protocol" in deco.id.lower():
                return True
        return False

    def _parse_protocol_class(self, node: ast.ClassDef, file_path: Path) -> ProtocolContract:
        """解析 Protocol 类定义"""
        qualified_name = self._get_qualified_name(node, file_path)

        required_attrs = []
        required_methods = []
        optional_methods = []

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # 类型注解属性
                attr = ContractAttribute(
                    name=item.target.id,
                    type=ast.unparse(item.annotation) if hasattr(ast, "unparse") else ast.dump(item.annotation),
                    required=not (item.value is not None and isinstance(item.value, ast.Constant) and item.value.value is ...),
                    docstring=None,
                )
                required_attrs.append(attr)

            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._parse_method(item)
                # 判断是否可选（有默认实现或抛出 NotImplementedError）
                is_optional = self._is_optional_method(item)
                if is_optional:
                    optional_methods.append(method)
                else:
                    required_methods.append(method)

        return ProtocolContract(
            name=node.name,
            qualified_name=qualified_name,
            file_path=str(file_path),
            docstring=ast.get_docstring(node, clean=True),
            required_attributes=required_attrs,
            required_methods=required_methods,
            optional_methods=optional_methods,
            metadata={"source": "backend_framework/protocols"},
        )

    def _parse_method(self, node: ast.FunctionDef) -> ContractMethod:
        """解析方法签名"""
        params = []
        for arg in node.args.args:
            param_info = {
                "name": arg.arg,
                "type": ast.unparse(arg.annotation) if arg.annotation and hasattr(ast, "unparse") else "Any",
                "default": None,
                "required": True,
            }
            # 检查默认值
            defaults_offset = len(node.args.args) - len(node.args.defaults)
            idx = node.args.args.index(arg)
            if idx >= defaults_offset:
                default_idx = idx - defaults_offset
                param_info["default"] = ast.unparse(node.args.defaults[default_idx]) if hasattr(ast, "unparse") else "<default>"
                param_info["required"] = False

        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns) if hasattr(ast, "unparse") else ast.dump(node.returns)

        return ContractMethod(
            name=node.name,
            parameters=params,
            return_type=return_type,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_classmethod=any(isinstance(d, ast.Name) and d.id == "classmethod" for d in node.decorator_list),
            is_staticmethod=any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in node.decorator_list),
            is_property=any(isinstance(d, ast.Name) and d.id == "property" for d in node.decorator_list),
            docstring=ast.get_docstring(node, clean=True),
        )

    def _is_optional_method(self, node: ast.FunctionDef) -> bool:
        """判断方法是否可选（有默认实现）"""
        # 如果方法体不只有 pass/.../raise NotImplementedError，视为有默认实现
        if not node.body:
            return False
        if len(node.body) == 1:
            stmt = node.body[0]
            if isinstance(stmt, (ast.Pass, ast.Expr)) and isinstance(getattr(stmt, "value", None), ast.Constant):
                if stmt.value.value in (..., "NotImplementedError"):
                    return False
            if isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Call):
                if isinstance(stmt.exc.func, ast.Name) and stmt.exc.func.id == "NotImplementedError":
                    return False
        return True

    def _get_qualified_name(self, node: ast.ClassDef, file_path: Path) -> str:
        """获取限定名"""
        module_parts = file_path.with_suffix("").parts
        for i, part in enumerate(module_parts):
            if part in ("backend_framework", "protocols"):
                return ".".join(module_parts[i:] + (node.name,))
        return ".".join(module_parts[-2:] + (node.name,))

    def parse_implementations(self, root_dirs: List[Path]) -> Dict[str, List[ImplementationCheck]]:
        """扫描实现类并检查符合度"""
        from ast_parser import parse_directory, Symbol, SymbolType

        all_implementations = defaultdict(list)

        for root in root_dirs:
            files = parse_directory(root)
            for path, file_info in files.items():
                for symbol in file_info.symbols:
                    if symbol.symbol_type in (SymbolType.CLASS, SymbolType.METHOD):
                        self._check_implementation(symbol, file_info, all_implementations)

        self.implementations = all_implementations
        return all_implementations

    def _check_implementation(self, symbol: Symbol, file_info, all_impls: Dict):
        """检查单个符号是否实现了某个 Protocol"""
        # 通过基类、装饰器、类名模式推断实现的 Protocol
        implemented_protocols = self._infer_implemented_protocols(symbol)

        for proto_qn in implemented_protocols:
            if proto_qn not in self.contracts:
                continue
            contract = self.contracts[proto_qn]

            check = ImplementationCheck(
                protocol=proto_qn,
                implementation=symbol.name,
                qualified_name=symbol.qualified_name,
                file_path=symbol.position.file,
                implements_all_required=True,
            )

            # 检查必需属性
            for attr in contract.required_attributes:
                if not self._has_attribute(symbol, attr.name):
                    check.missing_attributes.append(attr.name)
                    check.implements_all_required = False

            # 检查必需方法
            for method in contract.required_methods:
                if not self._has_method(symbol, method):
                    check.missing_methods.append(method.name)
                    check.implements_all_required = False
                else:
                    # 签名匹配检查
                    mismatch = self._check_method_signature(symbol, method)
                    if mismatch:
                        check.signature_mismatches.append(mismatch)

            # 计算评分
            total_required = len(contract.required_attributes) + len(contract.required_methods)
            missing_total = len(check.missing_attributes) + len(check.missing_methods)
            check.score = 1.0 - (missing_total / max(total_required, 1))

            all_impls[proto_qn].append(check)

    def _infer_implemented_protocols(self, symbol: Symbol) -> List[str]:
        """推断符号实现的 Protocol"""
        protocols = []

        # 1. 基类中包含 Protocol
        for base in symbol.bases:
            if "Protocol" in base:
                # 尝试匹配已知契约
                for proto_qn in self.contracts:
                    if proto_qn.endswith(f".{base}") or base in proto_qn:
                        protocols.append(proto_qn)

        # 2. 装饰器 @register("type", "name") 推断
        for deco in symbol.decorators:
            if "register" in deco and "Protocol" in deco:
                pass  # TODO: 解析 register 装饰器参数

        # 3. 类名模式匹配
        for proto_qn in self.contracts:
            proto_name = proto_qn.split(".")[-1].replace("Protocol", "")
            if proto_name.lower() in symbol.name.lower():
                protocols.append(proto_qn)

        return list(set(protocols))

    def _has_attribute(self, symbol: Symbol, attr_name: str) -> bool:
        """检查是否有属性（简化版）"""
        return attr_name in symbol.metadata.get("attributes", [])

    def _has_method(self, symbol: Symbol, method: ContractMethod) -> bool:
        """检查是否有方法"""
        return method.name in symbol.metadata.get("methods", [])

    def _check_method_signature(self, symbol: Symbol, method: ContractMethod) -> Optional[Dict]:
        """检查方法签名匹配（简化版）"""
        # 实际需要获取实现类的方法详情
        return None

    def export_all(self, output_dir: Path):
        """导出所有契约和实现检查结果"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # contracts.json
        with open(output_dir / "contracts.json", "w", encoding="utf-8") as f:
            json.dump({
                qn: c.to_dict() for qn, c in self.contracts.items()
            }, f, ensure_ascii=False, indent=2)

        # implementations.json
        with open(output_dir / "implementations.json", "w", encoding="utf-8") as f:
            json.dump({
                proto: [c.to_dict() for c in checks]
                for proto, checks in self.implementations.items()
            }, f, ensure_ascii=False, indent=2)

        # summary.json - 统计概览
        with open(output_dir / "contracts_summary.json", "w", encoding="utf-8") as f:
            json.dump({
                "total_protocols": len(self.contracts),
                "total_implementations": sum(len(v) for v in self.implementations.values()),
                "by_protocol": {
                    proto: {
                        "implementations": len(checks),
                        "fully_compliant": sum(1 for c in checks if c.implements_all_required),
                        "avg_score": sum(c.score for c in checks) / len(checks) if checks else 0,
                    }
                    for proto, checks in self.implementations.items()
                },
            }, f, ensure_ascii=False, indent=2)


def parse_all_contracts(protocol_dir: Path, impl_root_dirs: List[Path]) -> ContractParser:
    """解析所有契约和实现"""
    parser = ContractParser()

    # 1. 解析 Protocol 定义
    for proto_file in protocol_dir.glob("*.py"):
        if proto_file.name.startswith("_"):
            continue
        contracts = parser.parse_protocol_file(proto_file)
        print(f"解析 {proto_file.name}: {len(contracts)} 个 Protocol")

    # 2. 扫描实现
    parser.parse_implementations(impl_root_dirs)

    return parser


if __name__ == "__main__":
    import sys
    protocol_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("backend_framework/protocols")
    impl_dirs = [Path(p) for p in sys.argv[2:]] if len(sys.argv) > 2 else [Path("backends"), Path("backend_framework/adapters")]

    parser = parse_all_contracts(protocol_dir, impl_dirs)
    parser.export_all(Path("frontend/public/algorithm-map"))
    print("契约解析完成")