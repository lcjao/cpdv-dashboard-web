"""LegacyTrainer - 适配原始 Pipeline 三阶段训练器

复用 scripts/04_train_multi_crack.py 的 train_three_phase 函数。
"""
from typing import Dict, Any, List, Optional, Callable
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import sys
from pathlib import Path

from backend_framework.protocols import (
    TrainerProtocol, TrainResult,
    ModelProtocol, DataLoaderProtocol, LossProtocol, OptimizerProtocol
)
from backend_framework.registry.trainers import register_trainer


CODE_ROOT = Path(r"D:\研\土木水利\论文\代码\github")
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from scripts.data_loader import load_data as load_npz_data
from model.multi_crack import (
    MultiCrackPredictor,
    MultiCrackDualHead,
    weighted_multi_crack_loss,
    MultiCrackDualHeadLoss,
    evaluate_multi_crack,
    monitor_crack_counts,
)


ProgressCallback = Callable[[str, str, float, Dict[str, Any]], None]


@register_trainer("legacy_three_phase")
class LegacyThreePhaseTrainer:
    """原始三阶段训练器适配器
    
    完整复现 scripts/04_train_multi_crack.py 的训练流程：
    - 阶段1: 分类头预热 (仅双头)
    - 阶段2: 回归头训练 (仅双头)
    - 阶段3: 端到端联合微调
    """
    
    name = "legacy_three_phase"
    
    def __init__(self):
        self._history = {"train_loss": [], "val_loss": [], "phase": []}
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "max_epochs": 100,
            "phase1_epochs": 20,
            "phase2_epochs": 30,
            "phase3_epochs": 100,
            "early_stopping_patience": 30,
            "gradient_accumulation_steps": 1,
            "clip_grad": 1.0,
            "lr": 1e-3,
            "lr_finetune": 1e-4,
            "weight_decay": 1e-5,
            "miss_weight": 5.0,
            "reg_weight": 1.0,
            "pos_threshold": 0.0,
            "cls_threshold": 0.3,
            "match_cost": 5.0,
            "device": "auto",
            "seed": 42,
            "save_dir": "outputs/models",
            "save_history": "outputs/reports/training/multi_crack_history.json",
        }
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        errors = []
        if config.get("max_epochs", 0) <= 0:
            errors.append("max_epochs 必须 > 0")
        if config.get("phase1_epochs", 0) < 0:
            errors.append("phase1_epochs 不能 < 0")
        if config.get("phase2_epochs", 0) < 0:
            errors.append("phase2_epochs 不能 < 0")
        if config.get("phase3_epochs", 0) < 0:
            errors.append("phase3_epochs 不能 < 0")
        return errors
    
    def train(
        self,
        model: ModelProtocol,
        train_loader: DataLoaderProtocol,
        val_loader: DataLoaderProtocol,
        loss_fn: LossProtocol,
        optimizer: OptimizerProtocol,
        config: Dict[str, Any],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> TrainResult:
        
        # 合并默认配置
        full_config = self.get_default_config()
        full_config.update(config)
        config = full_config
        
        # 验证配置
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
        
        # 获取数据数组用于验证
        train_arrays = train_loader.get_data_arrays()
        val_arrays = val_loader.get_data_arrays()
        
        X_val = torch.FloatTensor(val_arrays["X_val"].T).to(device)
        y_val = torch.FloatTensor(val_arrays["y_val"].T).to(device)
        
        # 确定是否双头
        use_dual_head = getattr(model, "dual_head", False)
        
        # 准备损失函数参数
        loss_kwargs = {
            "miss_weight": config["miss_weight"],
            "reg_weight": config.get("reg_weight", 1.0),
        }
        
        # 训练历史
        history = {"train_loss": [], "val_loss": [], "phase": []}
        best_val_loss = float("inf")
        best_state = None
        patience_counter = 0
        started = time.time()
        epochs_completed = 0
        best_epoch = 0
        early_stopped = False
        
        def emit(stage: str, msg: str, percent: float, extra: Dict = None):
            if progress_callback:
                progress_callback(stage, msg, percent, extra or {})
        
        def run_epoch(
            phase_name: str,
            freeze_cls: bool = False,
            freeze_reg: bool = False,
            lr: Optional[float] = None,
            epochs: int = 1,
        ):
            nonlocal best_val_loss, patience_counter, best_state, best_epoch, epochs_completed, early_stopped
            
            if use_dual_head and hasattr(model.model, "backbone"):
                # 设置冻结
                for p in model.model.backbone.parameters():
                    p.requires_grad = True
                for p in model.model.classification_head.parameters():
                    p.requires_grad = not freeze_cls
                for p in model.model.regression_head.parameters():
                    p.requires_grad = not freeze_reg
            
            # 优化器
            if lr is None:
                lr = config["lr"]
            # 重新创建优化器以应用新的 lr 和冻结
            optim = torch.optim.AdamW(
                filter(lambda p: p.requires_grad, model.parameters()),
                lr=lr,
                weight_decay=config["weight_decay"],
            )
            
            for epoch in range(epochs):
                model.train()
                train_loss = 0.0
                for batch_x, batch_y in train_loader:
                    batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                    
                    if use_dual_head:
                        cls_pred, reg_pred = model(batch_x)
                        loss, _ = loss_fn((cls_pred, reg_pred), batch_y, **loss_kwargs)
                    else:
                        pred = model(batch_x)
                        loss = loss_fn(pred, batch_y, **loss_kwargs)
                    
                    optim.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), config["clip_grad"])
                    optim.step()
                    train_loss += loss.item()
                
                train_loss /= len(train_loader)
                history["train_loss"].append(train_loss)
                history["phase"].append(phase_name)
                
                # 验证
                model.eval()
                with torch.no_grad():
                    if use_dual_head:
                        cls_pred_v, reg_pred_v = model(X_val)
                        val_loss, _ = loss_fn((cls_pred_v, reg_pred_v), y_val, **loss_kwargs)
                    else:
                        pred_v = model(X_val)
                        val_loss = loss_fn(pred_v, y_val, **loss_kwargs)
                    val_loss = val_loss.item()
                
                history["val_loss"].append(val_loss)
                epochs_completed += 1
                
                # 早停检查
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    best_epoch = epochs_completed
                    best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                else:
                    patience_counter += 1
                
                # 进度回调
                if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
                    emit(phase_name, f"Epoch {epoch+1}/{epochs} | Train: {train_loss:.6f} | Val: {val_loss:.6f}", 
                         20 + 60 * epochs_completed / (config["phase1_epochs"] + config["phase2_epochs"] + config["phase3_epochs"]))
                
                if patience_counter >= config["early_stopping_patience"]:
                    early_stopped = True
                    emit(phase_name, f"早停于 Epoch {epoch + 1}", 85)
                    break
            
            patience_counter = 0  # 重置耐心计数器供下一阶段
        
        emit("preparing", "准备三阶段训练...", 10)
        
        # 阶段1: 分类预热 (仅双头)
        if use_dual_head and config["phase1_epochs"] > 0:
            emit("phase1", "阶段1: 分类头预热 (冻结回归头)", 20)
            run_epoch("phase1", freeze_cls=False, freeze_reg=True, lr=config["lr"], epochs=config["phase1_epochs"])
        
        # 阶段2: 回归训练 (仅双头)
        if use_dual_head and config["phase2_epochs"] > 0:
            emit("phase2", "阶段2: 回归头训练 (冻结分类头)", 40)
            run_epoch("phase2", freeze_cls=True, freeze_reg=False, lr=config["lr"], epochs=config["phase2_epochs"])
        
        # 阶段3: 端到端联合微调
        emit("phase3", "阶段3: 端到端联合微调", 60)
        run_epoch("phase3", lr=config["lr_finetune"], epochs=config["phase3_epochs"])
        
        # 恢复最佳模型
        if best_state is not None:
            model.load_state_dict(best_state)
            emit("best_model_restored", f"已恢复最佳模型 (val_loss={best_val_loss:.6f})", 80)
        
        # 最终评估
        emit("evaluating", "最终评估...", 90)
        
        model.eval()
        test_arrays = train_loader.get_data_arrays()  # 使用训练数据的测试集
        X_test = torch.FloatTensor(test_arrays["X_test"].T).to(device)
        y_test = torch.FloatTensor(test_arrays["y_test"].T).to(device)
        
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
        
        # 保存模型
        save_dir = Path(config["save_dir"])
        save_dir.mkdir(parents=True, exist_ok=True)
        model_name = f"multi_crack_{'dual' if use_dual_head else 'base'}.pth"
        model_path = str(save_dir / model_name)
        
        save_dict = {
            "model_state_dict": model.state_dict(),
            "input_dim": model.model_info().get("input_dim") if hasattr(model, "model_info") else train_arrays["X_train"].shape[0],
            "hidden_dim": config.get("hidden_dim", 256),
            "num_layers": config.get("num_layers", 3),
            "max_cracks": getattr(model, "max_cracks", 5),
            "dual_head": use_dual_head,
            "metrics": metrics,
        }
        if "X_mean" in stats:
            save_dict["X_mean"] = stats["X_mean"]
            save_dict["X_std"] = stats["X_std"]
        if "y_mean" in stats:
            save_dict["y_mean"] = stats["y_mean"]
            save_dict["y_std"] = stats["y_std"]
        
        torch.save(save_dict, model_path)
        
        # 保存历史
        hist_path = config.get("save_history")
        if hist_path:
            import json
            Path(hist_path).parent.mkdir(parents=True, exist_ok=True)
            with open(hist_path, "w") as f:
                json.dump(history, f, indent=2)
        
        emit("done", f"训练完成 ({duration_s:.1f}s)", 100, {
            "model": model_path,
            "duration_s": round(duration_s, 1),
            "f1": metrics.get("f1"),
            "pos_mae": metrics.get("pos_mae"),
            "depth_mae": metrics.get("depth_mae"),
        })
        
        return TrainResult(
            model_state=model.state_dict(),
            metrics=metrics,
            history=history,
            artifacts={
                "model_path": model_path,
                "history_path": hist_path or "",
            },
            duration_s=duration_s,
            epochs_completed=epochs_completed,
            best_epoch=best_epoch,
            best_val_loss=best_val_loss,
            early_stopped=early_stopped,
            config=config,
        )
    
    def evaluate(
        self,
        model: ModelProtocol,
        test_loader: DataLoaderProtocol,
        loss_fn: LossProtocol,
        config: Dict[str, Any],
    ) -> Dict[str, float]:
        """评估模式复用训练末尾的评估逻辑"""
        device_str = config.get("device", "auto")
        if device_str == "auto":
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            device = torch.device(device_str)
        
        model.to(device)
        model.eval()
        
        test_arrays = test_loader.get_data_arrays()
        X_test = torch.FloatTensor(test_arrays["X_test"].T).to(device)
        y_test = torch.FloatTensor(test_arrays["y_test"].T).to(device)
        
        use_dual_head = getattr(model, "dual_head", False)
        
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
        
        metrics = evaluate_multi_crack(
            pred_np, target_np,
            cls_pred_batch=cls_np,
            position_threshold=config.get("pos_threshold", 0.0),
            cls_threshold=config.get("cls_threshold", 0.3),
            max_cost=config.get("match_cost", 5.0),
            use_dual_head=use_dual_head,
        )
        
        return metrics