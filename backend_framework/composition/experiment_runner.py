"""ExperimentRunner - 实验运行器与 A/B 测试框架

提供单实验运行、多版本 A/B 测试、统计显著性检验、报告生成。
"""
from typing import Dict, Any, List, Optional, Tuple
import yaml
import json
import csv
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import defaultdict
import numpy as np
from scipy import stats

from backend_framework.protocols import (
    DataLoaderProtocol, ModelProtocol, LossProtocol,
    OptimizerProtocol, TrainerProtocol, EvaluatorProtocol,
    TrainResult, EvaluationResult
)
from backend_framework.composition.pipeline_builder import PipelineBuilder, build_pipeline_from_config
from backend_framework.registry import get_instance, register_all


@dataclass
class ExperimentResult:
    """单次实验结果"""
    variant_name: str
    run_idx: int
    train_result: Optional[TrainResult] = None
    eval_result: Optional[EvaluationResult] = None
    duration_s: float = 0.0
    error: Optional[str] = None
    output_dir: str = ""


@dataclass
class ABTestResult:
    """A/B 测试汇总结果"""
    test_name: str
    variants: List[str]
    primary_metric: str
    n_runs: int
    results: List[ExperimentResult]
    statistics: Dict[str, Any]
    ranking: List[Dict[str, Any]]
    report_path: str = ""


class ExperimentRunner:
    """实验运行器
    
    支持：
    - 单实验运行
    - A/B 测试（多版本、多轮重复、统计检验）
    - 结果持久化（metrics.csv, statistical_test.json, report.md）
    """
    
    def __init__(self, base_config: Dict[str, Any]):
        """
        Args:
            base_config: 基础实验配置（包含 experiment, components, output）
        """
        self.base_config = base_config
        self.results: List[ExperimentResult] = []
    
    def run_single(
        self,
        variant_config: Optional[Dict[str, Any]] = None,
        run_idx: int = 0,
        variant_name: str = "default",
    ) -> ExperimentResult:
        """运行单个实验
        
        Args:
            variant_config: 变体配置（覆盖 base_config 的 components）
            run_idx: 运行索引（用于多轮重复）
            variant_name: 变体名称
            
        Returns:
            ExperimentResult
        """
        # 合并配置
        config = self._merge_config(variant_config or {})
        config["experiment"]["name"] = f"{config['experiment'].get('name', 'exp')}_{variant_name}_run{run_idx}"
        
        # 设置随机种子
        seed = config["experiment"].get("seed", 42) + run_idx
        import torch
        import numpy as np
        import random
        torch.manual_seed(seed)
        np.random.seed(seed)
        random.seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        
        # 触发注册
        register_all()
        
        # 构建管线
        builder = PipelineBuilder(config)
        output_dir = builder.get_output_dir()
        builder.save_config(output_dir)
        
        data_loader, model, loss_fn, optimizer, trainer, evaluator = builder.build()
        
        # 运行训练
        started = time.time()
        train_result = None
        eval_result = None
        error = None
        
        try:
            train_result = trainer.train(
                model=model,
                train_loader=data_loader,
                val_loader=data_loader,  # 使用同一数据加载器的验证集
                loss_fn=loss_fn,
                optimizer=optimizer,
                config=config.get("trainer", {}).get("params", {}),
            )
            
            # 运行评估
            eval_result = evaluator.evaluate(
                model=model,
                test_loader=data_loader,
                loss_fn=loss_fn,
                config=config.get("evaluator", {}).get("params", {}),
            )
            
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            import traceback
            traceback.print_exc()
        
        duration_s = time.time() - started
        
        result = ExperimentResult(
            variant_name=variant_name,
            run_idx=run_idx,
            train_result=train_result,
            eval_result=eval_result,
            duration_s=duration_s,
            error=error,
            output_dir=str(output_dir),
        )
        
        self.results.append(result)
        return result
    
    def _merge_config(self, override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并配置"""
        import copy
        config = copy.deepcopy(self.base_config)
        
        def deep_merge(base: dict, update: dict):
            for k, v in update.items():
                if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                    deep_merge(base[k], v)
                else:
                    base[k] = v
        
        deep_merge(config, override)
        return config


def run_single_experiment(config: Dict[str, Any]) -> ExperimentResult:
    """便捷函数：运行单实验"""
    runner = ExperimentRunner(config)
    return runner.run_single()


def run_ab_test(ab_config: Dict[str, Any]) -> ABTestResult:
    """运行 A/B 测试
    
    Args:
        ab_config: A/B 测试配置，格式：
            {
                "ab_test": {
                    "name": "model_comparison",
                    "seed": 42,
                    "n_runs": 5,
                    "statistical_test": "wilcoxon",
                    "alpha": 0.05,
                    "variants": [
                        {"name": "baseline", "config": "baseline.yaml"},
                        {"name": "custom_v1", "config": "exp_v1.yaml"},
                    ],
                    "primary_metric": "val_f1",
                    "secondary_metrics": ["val_mae", "val_recall", "val_precision"]
                }
            }
            
    Returns:
        ABTestResult 包含统计检验结果和排名
    """
    ab = ab_config.get("ab_test", {})
    test_name = ab.get("name", "ab_test")
    seed = ab.get("seed", 42)
    n_runs = ab.get("n_runs", 5)
    statistical_test = ab.get("statistical_test", "wilcoxon")
    alpha = ab.get("alpha", 0.05)
    variants = ab.get("variants", [])
    primary_metric = ab.get("primary_metric", "f1")
    secondary_metrics = ab.get("secondary_metrics", ["pos_mae", "depth_mae", "recall", "precision"])
    
    if not variants:
        raise ValueError("variants 不能为空")
    
    # 加载基础配置（使用第一个变体的配置作为基础）
    first_variant_config = variants[0].get("config")
    if isinstance(first_variant_config, str):
        # 从文件加载
        with open(first_variant_config, "r", encoding="utf-8") as f:
            base_config = yaml.safe_load(f)
    else:
        base_config = first_variant_config or {}
    
    # 确保基础配置有 ab_test 节
    if "ab_test" not in base_config:
        base_config["ab_test"] = ab
    
    runner = ExperimentRunner(base_config)
    all_results = []
    
    # 对每个变体运行 n_runs 次
    for variant in variants:
        variant_name = variant["name"]
        variant_config = variant.get("config", {})
        
        if isinstance(variant_config, str):
            with open(variant_config, "r", encoding="utf-8") as f:
                variant_config = yaml.safe_load(f)
        
        for run_idx in range(n_runs):
            result = runner.run_single(
                variant_config=variant_config,
                run_idx=run_idx,
                variant_name=variant_name,
            )
            all_results.append(result)
    
    # 统计分析
    statistics = _compute_statistics(all_results, variants, primary_metric, secondary_metrics, statistical_test, alpha)
    
    # 排名
    ranking = _compute_ranking(all_results, variants, primary_metric)
    
    # 生成报告
    output_dir = Path("experiments/results") / f"{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存 metrics.csv
    _save_metrics_csv(all_results, output_dir / "metrics.csv")
    
    # 保存 statistical_test.json
    _save_statistics_json(statistics, output_dir / "statistical_test.json")
    
    # 生成 report.md
    report_path = _generate_report(test_name, variants, primary_metric, n_runs, statistics, ranking, all_results, output_dir / "report.md")
    
    return ABTestResult(
        test_name=test_name,
        variants=[v["name"] for v in variants],
        primary_metric=primary_metric,
        n_runs=n_runs,
        results=all_results,
        statistics=statistics,
        ranking=ranking,
        report_path=report_path,
    )


def _compute_statistics(
    results: List[ExperimentResult],
    variants: List[Dict],
    primary_metric: str,
    secondary_metrics: List[str],
    test_method: str,
    alpha: float,
) -> Dict[str, Any]:
    """计算统计显著性"""
    variant_names = [v["name"] for v in variants]
    
    # 收集每个变体每个指标的多轮结果
    metric_data = {vn: defaultdict(list) for vn in variant_names}
    
    for r in results:
        if r.error:
            continue
        metrics = {}
        if r.train_result and r.train_result.metrics:
            metrics.update(r.train_result.metrics)
        if r.eval_result and r.eval_result.metrics:
            metrics.update(r.eval_result.metrics)
        
        for m in [primary_metric] + secondary_metrics:
            if m in metrics:
                metric_data[r.variant_name][m].append(metrics[m])
    
    # 两两比较
    comparisons = {}
    for i, v1 in enumerate(variant_names):
        for v2 in variant_names[i+1:]:
            key = f"{v1}_vs_{v2}"
            comparisons[key] = {}
            
            for metric in [primary_metric] + secondary_metrics:
                data1 = metric_data[v1].get(metric, [])
                data2 = metric_data[v2].get(metric, [])
                
                if len(data1) >= 2 and len(data2) >= 2:
                    if test_method == "wilcoxon":
                        # Wilcoxon 符号秩检验（配对样本）
                        try:
                            stat, p = stats.wilcoxon(data1, data2, alternative="two-sided")
                        except ValueError:
                            stat, p = None, None
                    elif test_method == "mannwhitney":
                        # Mann-Whitney U 检验（独立样本）
                        stat, p = stats.mannwhitneyu(data1, data2, alternative="two-sided")
                    elif test_method == "ttest":
                        # 配对 t 检验
                        stat, p = stats.ttest_rel(data1, data2)
                    else:
                        stat, p = None, None
                    
                    comparisons[key][metric] = {
                        "test": test_method,
                        "statistic": float(stat) if stat is not None else None,
                        "p_value": float(p) if p is not None else None,
                        "significant": p is not None and p < alpha,
                        "v1_mean": float(np.mean(data1)) if data1 else None,
                        "v2_mean": float(np.mean(data2)) if data2 else None,
                        "v1_std": float(np.std(data1, ddof=1)) if len(data1) > 1 else None,
                        "v2_std": float(np.std(data2, ddof=1)) if len(data2) > 1 else None,
                    }
                else:
                    comparisons[key][metric] = {
                        "error": "样本量不足（需要至少 2 个重复）",
                    }
    
    return {
        "test_method": test_method,
        "alpha": alpha,
        "primary_metric": primary_metric,
        "comparisons": comparisons,
        "summary": {
            vn: {m: {"mean": float(np.mean(vals)), "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0, "n": len(vals)}
                 for m, vals in metric_data[vn].items()}
            for vn in variant_names
        },
    }


def _compute_ranking(
    results: List[ExperimentResult],
    variants: List[Dict],
    primary_metric: str,
) -> List[Dict[str, Any]]:
    """按主指标排名"""
    variant_names = [v["name"] for v in variants]
    
    # 计算每个变体主指标的均值
    variant_scores = {}
    for vn in variant_names:
        vals = []
        for r in results:
            if r.variant_name == vn and not r.error:
                metrics = {}
                if r.train_result and r.train_result.metrics:
                    metrics.update(r.train_result.metrics)
                if r.eval_result and r.eval_result.metrics:
                    metrics.update(r.eval_result.metrics)
                if primary_metric in metrics:
                    vals.append(metrics[primary_metric])
        if vals:
            variant_scores[vn] = np.mean(vals)
    
    # 排序（F1 越大越好，MAE 越小越好）
    higher_is_better = "f1" in primary_metric or "recall" in primary_metric or "precision" in primary_metric
    sorted_variants = sorted(variant_scores.items(), key=lambda x: x[1], reverse=higher_is_better)
    
    return [
        {"rank": i+1, "variant": vn, f"mean_{primary_metric}": float(score)}
        for i, (vn, score) in enumerate(sorted_variants)
    ]


def _save_metrics_csv(results: List[ExperimentResult], path: Path):
    """保存指标 CSV"""
    rows = []
    for r in results:
        row = {
            "variant": r.variant_name,
            "run_idx": r.run_idx,
            "duration_s": r.duration_s,
            "error": r.error or "",
            "output_dir": r.output_dir,
        }
        if r.train_result and r.train_result.metrics:
            for k, v in r.train_result.metrics.items():
                row[f"train_{k}"] = v
        if r.eval_result and r.eval_result.metrics:
            for k, v in r.eval_result.metrics.items():
                row[f"eval_{k}"] = v
        rows.append(row)
    
    if rows:
        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def _save_statistics_json(statistics: Dict[str, Any], path: Path):
    """保存统计结果 JSON"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(statistics, f, indent=2, ensure_ascii=False)


def _generate_report(
    test_name: str,
    variants: List[Dict],
    primary_metric: str,
    n_runs: int,
    statistics: Dict[str, Any],
    ranking: List[Dict[str, Any]],
    results: List[ExperimentResult],
    path: Path,
) -> str:
    """生成 Markdown 对比报告"""
    lines = []
    lines.append(f"# A/B 测试报告: {test_name}")
    lines.append("")
    lines.append(f"- **测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **重复次数**: {n_runs}")
    lines.append(f"- **主指标**: {primary_metric}")
    lines.append(f"- **统计检验**: {statistics['test_method']} (α={statistics['alpha']})")
    lines.append(f"- **变体数**: {len(variants)}")
    lines.append("")
    
    # 排名表
    lines.append("## 📊 排名结果")
    lines.append("")
    lines.append("| 排名 | 变体 | 平均 " + primary_metric + " |")
    lines.append("|------|------|" + "|".join(["---"] * 1) + "|")
    for r in ranking:
        lines.append(f"| {r['rank']} | {r['variant']} | {r[f'mean_{primary_metric}']:.4f} |")
    lines.append("")
    
    # 统计显著性
    lines.append("## 📈 统计显著性检验")
    lines.append("")
    for comp_key, comp_data in statistics["comparisons"].items():
        lines.append(f"### {comp_key}")
        lines.append("")
        lines.append("| 指标 | 统计量 | P值 | 显著性 | " + comp_key.split("_vs_")[0] + " 均值±标准差 | " + comp_key.split("_vs_")[1] + " 均值±标准差 |")
        lines.append("|------|--------|-----|--------|" + "|".join(["---"] * 3) + "|")
        
        for metric, data in comp_data.items():
            if "error" in data:
                lines.append(f"| {metric} | - | - | - | {data['error']} | - |")
            else:
                sig = "✅" if data["significant"] else "❌"
                v1_mean = data["v1_mean"] if data["v1_mean"] is not None else "N/A"
                v1_std = data["v1_std"] if data["v1_std"] is not None else "N/A"
                v2_mean = data["v2_mean"] if data["v2_mean"] is not None else "N/A"
                v2_std = data["v2_std"] if data["v2_std"] is not None else "N/A"
                lines.append(f"| {metric} | {data['statistic']:.4f} | {data['p_value']:.4f} | {sig} | {v1_mean:.4f}±{v1_std:.4f} | {v2_mean:.4f}±{v2_std:.4f} |")
        lines.append("")
    
    # 详细数据
    lines.append("## 📋 详细实验数据")
    lines.append("")
    lines.append("| 变体 | 轮次 | 时长(s) | 错误 | 主指标 |")
    lines.append("|------|------|---------|------|--------|")
    for r in results:
        primary_val = "ERROR"
        if not r.error:
            metrics = {}
            if r.train_result and r.train_result.metrics:
                metrics.update(r.train_result.metrics)
            if r.eval_result and r.eval_result.metrics:
                metrics.update(r.eval_result.metrics)
            if primary_metric in metrics:
                primary_val = f"{metrics[primary_metric]:.4f}"
        lines.append(f"| {r.variant_name} | {r.run_idx} | {r.duration_s:.1f} | {r.error or '-'} | {primary_val} |")
    
    content = "\n".join(lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return str(path)