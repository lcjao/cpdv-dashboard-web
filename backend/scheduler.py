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
    """
    # 捕获 key = 数值 可选单位后缀
    re_item = re.compile(r"([A-Za-z_]+)\s*=\s*([\d.]+)\s*([A-Za-z_]*)")
    # 统一用小写 key
    multipliers = {
        "kmh": 1 / 3.6, "km/h": 1 / 3.6, "kn": 1000, "gpa": 1e9,
        "t": 1000, "ton": 1000, "mm": 1e-3,
    }
    params = {}
    for m in re_item.finditer(text):
        k = m.group(1)
        v = float(m.group(2))
        unit = m.group(3).lower()
        # 参数名里的单位后缀（如 V_kmh、kv_kN）
        for suf, mult in multipliers.items():
            if k.lower().endswith(suf):
                base = k[:-len(suf)]
                if base.endswith('_'):
                    base = base[:-1]
                v *= mult
                k = base
                break
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
