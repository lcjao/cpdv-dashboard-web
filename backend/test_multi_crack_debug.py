# -*- coding: utf-8 -*-
"""调试多裂缝预测：检查为什么模型没有检测到裂缝"""
import json
import numpy as np
import torch
import sys
sys.path.insert(0, ".")

# 1) 加载模型
MODEL_PATH = "data/models/multi_crack_dual_retrained.pth"
print(f"加载模型: {MODEL_PATH}")

try:
    ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    print(f"模型 checkpoint keys: {list(ckpt.keys())}")
except Exception as e:
    print(f"加载模型失败: {e}")
    sys.exit(1)

# 2) 加载注册桥
from data_loader import load_registry
reg = load_registry()
bridge = next(b for b in reg["bridges"] if b["id"] == "bridge_01")
print(f"\n桥梁: {bridge['name']}")
print(f"cpdv_signals 数量: {len(bridge.get('cpdv_signals', []))}")

# 3) 读取 crack list
signals = bridge.get("cpdv_signals", [])
params = bridge.get("params", {})
fallback = params.get("depth", 0.2)
cracks = []
for s in signals:
    pos = float(s["pos"])
    dep = float(s.get("depth", fallback))
    cracks.append([pos, dep])

print(f"crack_list: {cracks}")
print(f"训练深度范围: [0.05, 0.3]")
print(f"实际深度: {[c[1] for c in cracks]}")

# 4) 检查深度是否在训练范围内
for i, (pos, dep) in enumerate(cracks):
    in_range = 0.05 <= dep <= 0.3
    print(f"  裂缝 {i}: pos={pos:.2f}, depth={dep:.3f}, 在训练范围内: {in_range}")

# 5) 加载模型参数
input_dim = ckpt["input_dim"]
hidden_dim = ckpt.get("hidden_dim", 256)
num_layers = ckpt.get("num_layers", 3)
max_cracks = ckpt.get("max_cracks", 5)
print(f"\n模型参数: input_dim={input_dim}, hidden_dim={hidden_dim}, num_layers={num_layers}, max_cracks={max_cracks}")

# 6) 检查标准化统计量
X_mean = ckpt["X_mean"].flatten()
X_std = ckpt["X_std"].flatten()
y_mean = ckpt["y_mean"].flatten()
y_std = ckpt["y_std"].flatten()
print(f"X_mean shape: {X_mean.shape}, X_std shape: {X_std.shape}")
print(f"y_mean shape: {y_mean.shape}, y_std shape: {y_std.shape}")
print(f"X_mean range: [{X_mean.min():.4f}, {X_mean.max():.4f}]")
print(f"X_std range: [{X_std.min():.4f}, {X_std.max():.4f}]")

# 7) 检查模型输出维度
from model.multi_crack import MultiCrackDualHead
model = MultiCrackDualHead(
    input_dim=input_dim, hidden_dim=hidden_dim,
    num_layers=num_layers, max_cracks=max_cracks,
)
model.load_state_dict(ckpt["model_state_dict"])
model.eval()

# 测试输入
test_input = torch.randn(1, input_dim)
with torch.no_grad():
    cls_logits, reg_pred = model(test_input)
print(f"\n模型输出维度: cls_logits={cls_logits.shape}, reg_pred={reg_pred.shape}")
print(f"cls_logits 示例: {cls_logits[0].numpy()}")
print(f"reg_pred 示例 shape: {reg_pred.shape}")

# 8) 检查 CLS_THRESHOLD
CLS_THRESHOLD = 0.3
print(f"\n分类阈值 CLS_THRESHOLD: {CLS_THRESHOLD}")
print(f"如果所有 cls_logits <= {CLS_THRESHOLD}，则不会检测到任何裂缝")
