# 单实验运行
python -m backend_framework.cli run --config experiments/configs/exp_v1.yaml

# A/B 测试
python -m backend_framework.cli ab-test --config experiments/configs/ab_test.yaml

# 列出组件
python -m backend_framework.cli list-components

# 交互模式
python -m backend_framework.cli interactive