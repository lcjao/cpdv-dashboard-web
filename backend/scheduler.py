import re
import config


def parse_command(text: str):
    """将自然语言命令解析为 (action, args)。返回 None 若无匹配意图。"""
    t = text.strip()
    for kw, action in config.COMMANDS.items():
        if kw in t:
            return action, t
    return None


def parse_params(text: str):
    """从命令文本中提取 key=value 参数，支持值带单位后缀（如 V=50kmh）。

    单位换算：km/h→m/s, kN→N, GPa→Pa, t→kg, mm→m
    也支持参数名带单位（如 V_kmh=50 → V(m/s)）。
    复合值（如 distances=5,10,15）保留为字符串，由上层 split。

    数值段支持（G18）：
      - 整数 / 浮点：5, 0.05, -3, +1.5, .5
      - 科学计数：1e3, 1.5E-2, -2.5e+3
      - 列表：5,10,15（保留为字符串，调用方 split）

    regex 关键点：unit 部分必须严格白名单匹配 multipliers，
    否则会贪婪吞掉下一个 key（曾导致 depth=0.05 distances 整段被
    吃成 depth 的 unit）。
    """
    # key + 值（数字/列表 OR 无空格字符串）+ 可选标准单位。
    # ⚠️ 警告：千万不要在 adjacent raw string 拼接处加空白（曾坑过——
    # `(?P<v>" + "  \d+...")` 实际匹配 "两个空格+数字"，所有 case 全部 miss）。
    # 数值段：「整数或 . 浮点」+ 可选科学计数尾（1e3 / 1.5E-2）
    # 支持负号、科学计数法、逗号分隔列表
    re_item = re.compile(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
        r"(?P<v>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?:\s*,\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)*|[^\s,=][^\s,=]*)"
        r"(?:\s*(?P<u>kmh|km/h|kn|kN|gpa|GPa|t|ton|mm))?",
        re.IGNORECASE,
    )
    multipliers = {
        "kmh": 1 / 3.6, "km/h": 1 / 3.6, "kn": 1000, "gpa": 1e9,
        "t": 1000, "ton": 1000, "mm": 1e-3,
    }
    params = {}
    for m in re_item.finditer(text):
        k = m.group(1)
        raw_v = (m.group("v") or "").replace(" ", "")  # 移除逗号间空格
        unit = (m.group("u") or "").lower()
        # 参数名里的单位后缀（如 V_kmh、kv_kN）
        key_lower = k.lower()
        for suf in multipliers:
            if key_lower.endswith(suf):
                base = k[:-len(suf)]
                if base.endswith('_'):
                    base = base[:-1]
                k = base
                break
        try:
            v = float(raw_v)
        except ValueError:
            # 字符串值（如 note=桥梁02首次测试 / action_type=train）保持原样
            params[k] = raw_v
            continue
        # 值后面的单位后缀（如 V=50kmh、kv=100kN）
        if unit in multipliers:
            v *= multipliers[unit]
        params[k] = v
    return params


def validate_params(params: dict):
    """合理性校验；返回 (ok, msg)。越界必须向用户确认。"""
    rules = {
        "E": (1e9, 5e11), "V": (0.5, 40), "L": (5, 200),
        "mv": (500, 80000), "I": (0.01, 1),
    }
    for k, (lo, hi) in rules.items():
        if k in params and not (lo <= params[k] <= hi):
            return False, f"{k}={params[k]} 超出合理范围 [{lo},{hi}]，请确认后再执行"
    return True, ""
