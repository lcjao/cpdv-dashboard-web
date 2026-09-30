"""backend_framework.cli - 统一命令行入口

提供 run, ab-test, list-components, interactive 子命令。
"""
import argparse
import sys
import yaml
from pathlib import Path
from typing import Optional

from backend_framework.composition.experiment_runner import run_single_experiment, run_ab_test
from backend_framework.registry import list_all_names, register_all


def main():
    parser = argparse.ArgumentParser(
        description="可插拔后端执行框架 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单实验运行
  python -m backend_framework.cli run --config experiments/configs/exp_v1.yaml
  
  # A/B 测试
  python -m backend_framework.cli ab-test --config experiments/configs/ab_test.yaml
  
  # 列出所有可用组件
  python -m backend_framework.cli list-components
  
  # 交互式选择
  python -m backend_framework.cli interactive
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # run 子命令
    run_parser = subparsers.add_parser("run", help="运行单个实验")
    run_parser.add_argument("--config", "-c", required=True, help="实验配置 YAML 文件路径")
    run_parser.add_argument("--variant", "-v", help="变体名称（可选）")
    run_parser.add_argument("--run-idx", type=int, default=0, help="运行索引（用于多轮重复）")
    
    # ab-test 子命令
    ab_parser = subparsers.add_parser("ab-test", help="运行 A/B 测试")
    ab_parser.add_argument("--config", "-c", required=True, help="A/B 测试配置 YAML 文件路径")
    
    # list-components 子命令
    list_parser = subparsers.add_parser("list-components", help="列出所有已注册组件")
    list_parser.add_argument("--type", "-t", choices=[
        "data_loader", "model", "loss", "optimizer", "trainer", "evaluator", "all"
    ], default="all", help="组件类型")
    
    # interactive 子命令
    interactive_parser = subparsers.add_parser("interactive", help="交互式选择并运行")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # 触发所有后端注册
    register_all()
    
    try:
        if args.command == "run":
            return cmd_run(args)
        elif args.command == "ab-test":
            return cmd_ab_test(args)
        elif args.command == "list-components":
            return cmd_list_components(args)
        elif args.command == "interactive":
            return cmd_interactive(args)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


def cmd_run(args) -> int:
    """运行单实验"""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}", file=sys.stderr)
        return 1
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    print(f"🚀 启动单实验: {config_path}")
    print(f"   实验名称: {config.get('experiment', {}).get('name', 'unknown')}")
    
    result = run_single_experiment(config)
    
    if result.error:
        print(f"❌ 实验失败: {result.error}")
        return 1
    
    print(f"✅ 实验完成!")
    print(f"   耗时: {result.duration_s:.1f}s")
    print(f"   输出目录: {result.output_dir}")
    
    if result.train_result and result.train_result.metrics:
        print(f"   训练指标: {result.train_result.metrics}")
    if result.eval_result and result.eval_result.metrics:
        print(f"   评估指标: {result.eval_result.metrics}")
    
    return 0


def cmd_ab_test(args) -> int:
    """运行 A/B 测试"""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}", file=sys.stderr)
        return 1
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    print(f"🔬 启动 A/B 测试: {config_path}")
    ab = config.get("ab_test", {})
    print(f"   测试名称: {ab.get('name', 'unknown')}")
    print(f"   变体: {[v['name'] for v in ab.get('variants', [])]}")
    print(f"   重复次数: {ab.get('n_runs', 5)}")
    print(f"   主指标: {ab.get('primary_metric', 'f1')}")
    
    result = run_ab_test(config)
    
    print(f"✅ A/B 测试完成!")
    print(f"   报告: {result.report_path}")
    print(f"   排名:")
    for r in result.ranking:
        print(f"     {r['rank']}. {r['variant']} ({r[f'mean_{result.primary_metric}']:.4f})")
    
    return 0


def cmd_list_components(args) -> int:
    """列出所有已注册组件"""
    if args.type == "all":
        for comp_type in ["data_loader", "model", "loss", "optimizer", "trainer", "evaluator"]:
            names = list_all_names(comp_type)
            print(f"\n{comp_type}:")
            if names:
                for name in names:
                    print(f"  - {name}")
            else:
                print("  (无)")
    else:
        names = list_all_names(args.type)
        print(f"{args.type}:")
        if names:
            for name in names:
                print(f"  - {name}")
        else:
            print("  (无)")
    return 0


def cmd_interactive(args) -> int:
    """交互式选择并运行"""
    print("=== 可插拔后端执行框架 - 交互模式 ===")
    print()
    
    # 1. 选择组件
    print("可用组件:")
    components = {}
    for comp_type in ["data_loader", "model", "loss", "optimizer", "trainer", "evaluator"]:
        names = list_all_names(comp_type)
        if names:
            print(f"\n{comp_type}:")
            for i, name in enumerate(names):
                print(f"  {i+1}. {name}")
            components[comp_type] = names
    
    print("\n" + "="*50)
    print("请为每个组件选择编号（回车使用默认第一个）:")
    
    selected = {}
    for comp_type, names in components.items():
        while True:
            try:
                choice = input(f"{comp_type} [1-{len(names)}]: ").strip()
                if not choice:
                    idx = 0
                else:
                    idx = int(choice) - 1
                if 0 <= idx < len(names):
                    selected[comp_type] = names[idx]
                    break
                else:
                    print(f"  请输入 1-{len(names)} 之间的数字")
            except ValueError:
                print("  请输入有效数字")
            except KeyboardInterrupt:
                print("\n取消")
                return 1
    
    print(f"\n已选择: {selected}")
    
    # 2. 选择运行模式
    print("\n运行模式:")
    print("  1. 单实验运行")
    print("  2. A/B 测试（需要配置文件）")
    
    mode = input("选择模式 [1/2]: ").strip()
    
    if mode == "1":
        # 单实验 - 构建临时配置
        config = build_config_from_selection(selected)
        result = run_single_experiment(config)
        if result.error:
            print(f"❌ 失败: {result.error}")
            return 1
        print(f"✅ 完成! 输出: {result.output_dir}")
    elif mode == "2":
        config_path = input("A/B 测试配置文件路径: ").strip()
        if Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            result = run_ab_test(config)
            print(f"✅ 完成! 报告: {result.report_path}")
        else:
            print(f"文件不存在: {config_path}")
            return 1
    else:
        print("无效选择")
        return 1
    
    return 0


def build_config_from_selection(selected: Dict[str, str]) -> Dict[str, Any]:
    """从交互选择构建配置"""
    return {
        "experiment": {
            "name": "interactive_experiment",
            "seed": 42,
            "device": "auto",
        },
        "components": {
            "data_loader": {"type": selected.get("data_loader", "legacy"), "params": {}},
            "model": {"type": selected.get("model", "legacy_dual_head"), "params": {}},
            "loss": {"type": selected.get("loss", "legacy_dual_head"), "params": {}},
            "optimizer": {"type": selected.get("optimizer", "legacy_adamw"), "params": {"lr": 1e-3}},
            "trainer": {"type": selected.get("trainer", "legacy_three_phase"), "params": {}},
            "evaluator": {"type": selected.get("evaluator", "legacy_hungarian"), "params": {}},
        },
        "output": {
            "save_dir": "experiments/results/${experiment.name}_${timestamp}",
            "save_checkpoints": True,
        },
    }


if __name__ == "__main__":
    sys.exit(main())