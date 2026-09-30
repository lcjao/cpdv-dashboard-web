"""LegacyEvaluator - 适配原始 Pipeline 评估器

复用 model/multi_crack.py 的 evaluate_multi_crack 和 match_predictions。
"""
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import time
from dataclasses import dataclass, field
import sys
from pathlib import Path

from backend_framework.protocols import (
    EvaluatorProtocol, EvaluationResult,
    ModelProtocol, DataLoaderProtocol, LossProtocol
)
from backend_framework.registry.evaluators import register_evaluator


CODE_ROOT = Path(r"D:\研\土木水利\论文\代码\github")
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from model.multi_crack import (
    evaluate_multi_crack,
    match_predictions,
    monitor_crack_counts,
)


@register_evaluator("legacy_hungarian")
class LegacyHungarianEvaluator:
    """原始匈牙利匹配评估器适配器"""
    
    name = "legacy_hungarian"
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "cls_threshold": 0.3,
            "pos_threshold": 0.0,
            "match_cost": 5.0,
            "device": "auto",
            "save_details": False,
            "output_dir": None,
        }
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        errors = []
        if config.get("cls_threshold", 0) < 0 or config.get("cls_threshold", 0) > 1:
            errors.append("cls_threshold 必须在 [0, 1] 范围内")
        if config.get("match_cost", 0) < 0:
            errors.append("match_cost 不能 < 0")
        return errors
    
    def evaluate(
        self,
        model: ModelProtocol,
        test_loader: DataLoaderProtocol,
        loss_fn: LossProtocol,
        config: Dict[str, Any],
    ) -> EvaluationResult:
        full_config = self.get_default_config()
        full_config.update(config)
        config = full_config
        
        errors = self.validate_config(config)
        if errors:
            raise ValueError(f"配置错误: {errors}")
        
        # 设备
        device_str = config["device"]
        if device_str == "auto":
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            device = torch.device(device_str)
        
        model.to(device)
        model.eval()
        
        started = time.time()
        
        # 获取测试数据
        test_arrays = test_loader.get_data_arrays()
        X_test = torch.FloatTensor(test_arrays["X_test"].T).to(device)
        y_test = torch.FloatTensor(test_arrays["y_test"].T).to(device)
        
        use_dual_head = getattr(model, "dual_head", False)
        max_cracks = getattr(model, "max_cracks", 5)
        
        with torch.no_grad():
            if use_dual_head:
                cls_pred_ts, reg_pred_ts = model(X_test)
                pred_np = reg_pred_ts.cpu().numpy()
                cls_np = cls_pred_ts.cpu().numpy()
            else:
                pred_np = model(X_test).cpu().numpy()
                cls_np = None
        
        target_np = y_test.cpu().numpy()
        
        # 反归一化
        stats = test_arrays.get("stats", {})
        if "y_mean" in stats and "y_std" in stats:
            y_mean = stats["y_mean"].flatten()
            y_std = stats["y_std"].flatten()
            for i in range(target_np.shape[1]):
                slot_mask = target_np[:, i] >= 0
                if slot_mask.sum() > 0:
                    pred_np[slot_mask, i] = pred_np[slot_mask, i] * y_std[i] + y_mean[i]
                    target_np[slot_mask, i] = target_np[slot_mask, i] * y_std[i] + y_mean[i]
        
        # 计算指标
        metrics = evaluate_multi_crack(
            pred_np, target_np,
            cls_pred_batch=cls_np,
            position_threshold=config["pos_threshold"],
            cls_threshold=config["cls_threshold"],
            max_cost=config["match_cost"],
            use_dual_head=use_dual_head,
        )
        
        duration_s = time.time() - started
        
        # 可选：保存详细结果
        per_sample = []
        matches_detail = []
        
        if config.get("save_details"):
            batch_size = pred_np.shape[0]
            for b in range(batch_size):
                gt_list = []
                for j in range(max_cracks):
                    pos, depth = float(target_np[b, j * 2]), float(target_np[b, j * 2 + 1])
                    if pos >= 0 and depth >= 0:
                        gt_list.append((pos, depth))
                
                if use_dual_head and cls_np is not None:
                    pred_list = [
                        (float(pred_np[b, j * 2]), float(pred_np[b, j * 2 + 1]))
                        for j in range(max_cracks)
                        if cls_np[b, j] > config["cls_threshold"] and float(pred_np[b, j * 2 + 1]) > 0
                    ]
                else:
                    pred_list = [
                        (float(pred_np[b, j * 2]), float(pred_np[b, j * 2 + 1]))
                        for j in range(max_cracks)
                        if float(pred_np[b, j * 2]) > config["pos_threshold"]
                        and float(pred_np[b, j * 2 + 1]) > 0
                    ]
                
                matches, unmatched_gt, unmatched_pred = match_predictions(
                    gt_list, pred_list, config["match_cost"]
                )
                
                per_sample.append({
                    "sample_idx": b,
                    "gt_cracks": gt_list,
                    "pred_cracks": pred_list,
                    "matches": [{"gt": gt_list[i], "pred": pred_list[j]} for i, j in matches],
                    "unmatched_gt": [gt_list[i] for i in unmatched_gt],
                    "unmatched_pred": [pred_list[j] for j in unmatched_pred],
                })
                
                for i, j in matches:
                    matches_detail.append({
                        "sample_idx": b,
                        "gt_position": gt_list[i][0],
                        "gt_depth": gt_list[i][1],
                        "pred_position": pred_list[j][0],
                        "pred_depth": pred_list[j][1],
                        "pos_error": abs(gt_list[i][0] - pred_list[j][0]),
                        "depth_error": abs(gt_list[i][1] - pred_list[j][1]),
                    })
        
        return EvaluationResult(
            metrics=metrics,
            per_sample=per_sample,
            matches=matches_detail,
            confusion={
                "tp": metrics.get("n_matched", 0),
                "fp": metrics.get("n_pred", 0) - metrics.get("n_matched", 0),
                "fn": metrics.get("n_gt", 0) - metrics.get("n_matched", 0),
            },
            model_path="",
            data_path="",
            config=config,
            duration_s=duration_s,
        )
    
    def evaluate_multiple(
        self,
        model_paths: List[str],
        test_loader: DataLoaderProtocol,
        loss_fn: LossProtocol,
        config: Dict[str, Any],
        n_runs: int = 1,
    ) -> List[EvaluationResult]:
        results = []
        for model_path in model_paths:
            for run_idx in range(n_runs):
                # 加载模型
                if hasattr(model, "load"):
                    loaded_model = model.load(model_path)
                else:
                    # 尝试从配置推断模型类型并加载
                    loaded_model = ModelProtocol.load(model_path)  # type: ignore
                
                run_config = config.copy()
                run_config["run_idx"] = run_idx
                result = self.evaluate(loaded_model, test_loader, loss_fn, run_config)
                result.model_path = model_path
                results.append(result)
        return results
    
    def compute_metrics(
        self,
        pred_batch: np.ndarray,
        target_batch: np.ndarray,
        cls_pred_batch: Optional[np.ndarray] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        if config is None:
            config = self.get_default_config()
        
        return evaluate_multi_crack(
            pred_batch, target_batch,
            cls_pred_batch=cls_pred_batch,
            position_threshold=config.get("pos_threshold", 0.0),
            cls_threshold=config.get("cls_threshold", 0.3),
            max_cost=config.get("match_cost", 5.0),
            use_dual_head=cls_pred_batch is not None,
        )