"""implementation_mapper.py - 实现映射器

扫描 backends/ 目录，将每个后端的组件映射到对应的 Protocol：
1. 导入后端模块触发注册
2. 查询注册表获取已注册组件
3. 关联 Protocol -> 实现类
4. 生成 implementations.json 供前端对比视图使用
4. 支持版本化：每个后端可有多个版本
"""
import ast
import json
import re
import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict

# 添加脚本目录到路径
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))


@dataclass
class BackendComponent:
    """后端组件信息"""
    backend_name: str           # 如 "legacy", "custom_v1"
    component_type: str         # "data_loader", "model", "loss", "optimizer", "trainer", "evaluator"
    registered_name: str        # @register 装饰器中的 name
    class_name: str             # 类名
    qualified_name: str         # 完整限定名
    file_path: str
    protocol: Optional[str] = None  # 对应的 Protocol qualified_name
    config_schema: Dict[str, Any] = field(default_factory=dict)  # 参数 schema
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BackendInfo:
    """后端完整信息"""
    name: str
    display_name: str
    description: str
    version: str
    path: str
    components: List[BackendComponent] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他后端
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ImplementationMapper:
    """实现映射器主类"""

    # 组件类型 -> 对应的 Protocol 模块名
    PROTOCOL_MAP = {
        "data_loader": "backend_framework.protocols.DataLoaderProtocol",
        "model": "backend_framework.protocols.ModelProtocol",
        "loss": "backend_framework.protocols.LossProtocol",
        "optimizer": "backend_framework.protocols.OptimizerProtocol",
        "trainer": "backend_framework.protocols.TrainerProtocol",
        "evaluator": "backend_framework.protocols.EvaluatorProtocol",
    }

    def __init__(self):
        self.backends: Dict[str, BackendInfo] = {}
        self.component_index: Dict[str, Dict[str, BackendComponent]] = defaultdict(dict)  # type -> name -> component
        self.protocol_implementations: Dict[str, List[BackendComponent]] = defaultdict(list)  # protocol -> components

    def scan_backends(self, backends_root: Path) -> Dict[str, BackendInfo]:
        """扫描 backends/ 目录下所有后端 - 通过导入模块并查询注册表"""
        import sys
        sys.path.insert(0, str(backends_root.parent))

        for backend_dir in backends_root.iterdir():
            if not backend_dir.is_dir() or backend_dir.name.startswith("_"):
                continue
            if backend_dir.name == "__pycache__":
                continue

            backend = self._scan_single_backend(backend_dir)
            if backend:
                self.backends[backend.name] = backend
                self._index_components(backend)

        return self.backends

    def _scan_single_backend(self, backend_dir: Path) -> Optional[BackendInfo]:
        """扫描单个后端目录 - 导入模块并查询注册表"""
        backend_name = backend_dir.name
        module_name = f"backends.{backend_name}"

        # 解析 __init__.py 获取后端元信息
        init_file = backend_dir / "__init__.py"
        metadata = {}
        if init_file.exists():
            content = init_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
                if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
                    metadata["description"] = tree.body[0].value.value
            except Exception:
                pass

            version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if version_match:
                metadata["version"] = version_match.group(1)
            display_match = re.search(r'__display_name__\s*=\s*["\']([^"\']+)["\']', content)
            if display_match:
                metadata["display_name"] = display_match.group(1)

        # 导入后端模块以触发注册
        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)
        except Exception as e:
            print(f"  ⚠️ 导入后端 {backend_name} 失败: {e}")

        # 从注册表查询已注册的组件
        from backend_framework.registry import list_all

        backend = BackendInfo(
            name=backend_name,
            display_name=metadata.get("display_name", backend_name.replace("_", " ").title()),
            description=metadata.get("description", ""),
            version=metadata.get("version", "0.1.0"),
            path=str(backend_dir),
        )

        # 查询每种组件类型的注册表
        for comp_type in ["data_loader", "model", "loss", "optimizer", "trainer", "evaluator"]:
            try:
                all_comps = list_all(comp_type)
                for comp_name, comp_cls in all_comps.items():
                    # 只收集属于当前后端的组件（通过模块名判断）
                    if self._is_component_from_backend(comp_cls, backend_name):
                        comp = BackendComponent(
                            backend_name=backend_name,
                            component_type=comp_type,
                            registered_name=comp_name,
                            class_name=comp_cls.__name__,
                            qualified_name=f"{comp_cls.__module__}.{comp_cls.__name__}",
                            file_path=getattr(comp_cls, "__file__", str(backend_dir)),
                            protocol=self.PROTOCOL_MAP.get(comp_type),
                            config_schema=self._extract_config_schema_from_class(comp_cls),
                            metadata={"module": comp_cls.__module__},
                        )
                        backend.components.append(comp)
            except Exception as e:
                print(f"  ⚠️ 查询 {comp_type} 注册表失败: {e}")

        return backend if backend.components else None

    def _is_component_from_backend(self, comp_cls: type, backend_name: str) -> bool:
        """判断组件类是否属于指定后端"""
        module = comp_cls.__module__
        return module == f"backends.{backend_name}" or module.startswith(f"backends.{backend_name}.") or \
               module == "backend_framework.adapters" or module.startswith("backend_framework.adapters.")  # adapters 也算 legacy 的一部分

    def _extract_config_schema_from_class(self, comp_cls: type) -> Dict[str, Any]:
        """从类的 __init__ 签名提取配置 schema"""
        try:
            sig = inspect.signature(comp_cls.__init__)
            schema = {"type": "object", "properties": {}, "required": []}
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                param_info = {"type": "any"}
                if param.annotation != inspect.Parameter.empty:
                    ann = str(param.annotation)
                    param_info["type"] = self._annotation_to_json_schema(ann)
                schema["properties"][param_name] = param_info
                if param.default == inspect.Parameter.empty:
                    schema["required"].append(param_name)
                else:
                    try:
                        schema["properties"][param_name]["default"] = param.default
                    except Exception:
                        pass
            return schema
        except Exception:
            return {"type": "object", "properties": {}, "required": []}

    def _annotation_to_json_schema(self, annotation: str) -> Dict[str, Any]:
        """类型注解转 JSON Schema 类型"""
        ann = annotation.lower()
        if "int" in ann:
            return {"type": "integer"}
        elif "float" in ann:
            return {"type": "number"}
        elif "bool" in ann:
            return {"type": "boolean"}
        elif "str" in ann:
            return {"type": "string"}
        elif "list" in ann or "sequence" in ann:
            return {"type": "array"}
        elif "dict" in ann or "mapping" in ann:
            return {"type": "object"}
        elif "optional" in ann or "union" in ann:
            return {"type": ["null", "any"]}
        return {"type": "any"}

    def _index_components(self, backend: BackendInfo):
        """建立组件索引"""
        for comp in backend.components:
            self.component_index[comp.component_type][comp.registered_name] = comp
            if comp.protocol:
                self.protocol_implementations[comp.protocol].append(comp)

    def get_component(self, component_type: str, name: str) -> Optional[BackendComponent]:
        """获取指定类型和名称的组件"""
        return self.component_index.get(component_type, {}).get(name)

    def get_implementations_for_protocol(self, protocol: str) -> List[BackendComponent]:
        """获取实现某 Protocol 的所有组件"""
        return self.protocol_implementations.get(protocol, [])

    def export_all(self, output_dir: Path):
        """导出所有映射数据"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # backends.json
        with open(output_dir / "backends.json", "w", encoding="utf-8") as f:
            json.dump({
                name: b.to_dict() for name, b in self.backends.items()
            }, f, ensure_ascii=False, indent=2)

        # component_index.json - 便于前端快速查找
        with open(output_dir / "component_index.json", "w", encoding="utf-8") as f:
            json.dump({
                comp_type: {name: c.to_dict() for name, c in comps.items()}
                for comp_type, comps in self.component_index.items()
            }, f, ensure_ascii=False, indent=2)

        # protocol_implementations.json - 协议实现对比
        with open(output_dir / "protocol_implementations.json", "w", encoding="utf-8") as f:
            json.dump({
                proto: [c.to_dict() for c in comps]
                for proto, comps in self.protocol_implementations.items()
            }, f, ensure_ascii=False, indent=2)

        # backends_summary.json
        with open(output_dir / "backends_summary.json", "w", encoding="utf-8") as f:
            json.dump({
                "total_backends": len(self.backends),
                "total_components": sum(len(b.components) for b in self.backends.values()),
                "by_type": {
                    comp_type: len(comps)
                    for comp_type, comps in self.component_index.items()
                },
                "by_backend": {
                    name: {
                        "components": len(b.components),
                        "types": list(set(c.component_type for c in b.components)),
                    }
                    for name, b in self.backends.items()
                },
            }, f, ensure_ascii=False, indent=2)


def scan_all_implementations(backends_root: Path, output_dir: Path) -> ImplementationMapper:
    """扫描所有后端实现并导出"""
    mapper = ImplementationMapper()
    mapper.scan_backends(backends_root)
    mapper.export_all(output_dir)

    print(f"扫描完成: {len(mapper.backends)} 个后端, {sum(len(b.components) for b in mapper.backends.values())} 个组件")
    for name, backend in mapper.backends.items():
        print(f"  {name}: {len(backend.components)} 组件 - {[c.component_type for c in backend.components]}")

    return mapper


if __name__ == "__main__":
    import sys
    backends_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("backends")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("frontend/public/algorithm-map")

    scan_all_implementations(backends_root, output_dir)