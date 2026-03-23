"""
YAML配置加载测试

只测试配置加载功能，不涉及策略导入。
"""

import sys
from pathlib import Path

# 设置UTF-8编码（Windows兼容性）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 直接导入配置模块
from config.strategy_loader import StrategyConfigLoader, load_strategy_config


def test_yaml_config_loading():
    """测试YAML配置加载"""

    print("=" * 80)
    print("101因子平台 - YAML配置加载测试")
    print("=" * 80)

    # 1. 测试简单小市值策略
    print(f"\n📄 测试1: 简单小市值策略配置")
    print("-" * 80)

    config_path = project_root / 'config' / 'examples' / 'simple_small_cap.yaml'

    print(f"配置文件路径: {config_path}")
    print(f"文件存在: {config_path.exists()}")

    if not config_path.exists():
        print(f"❌ 配置文件不存在!")
        return

    try:
        config = StrategyConfigLoader.load_from_yaml(str(config_path))

        print(f"✅ 配置加载成功!")
        print(f"\n策略信息:")
        print(f"  名称: {config.name}")
        print(f"  版本: {config.version}")
        print(f"  作者: {config.author}")
        print(f"  描述: {config.description}")

        print(f"\n回测配置:")
        print(f"  开始日期: {config.backtest_config['start_date']}")
        print(f"  结束日期: {config.backtest_config['end_date']}")
        print(f"  初始资金: {config.backtest_config['initial_cash']:,}")
        print(f"  佣金: {config.backtest_config['commission']:.3%}")

        print(f"\n股票池配置:")
        print(f"  类型: {config.universe_config['type']}")
        print(f"  指数代码: {config.universe_config['index_code']}")

        print(f"\n排除条件 ({len(config.exclude_filters)}个):")
        for i, f in enumerate(config.exclude_filters, 1):
            print(f"  {i}. {f.name} - {f.type} - {f.condition}")

        print(f"\n打分因子 ({len(config.scoring_factors)}个):")
        for i, f in enumerate(config.scoring_factors, 1):
            direction = "正相关" if f.direction == 1 else "负相关"
            neutralize = "是" if f.neutralize.get('enabled', False) else "否"
            print(f"  {i}. {f.name}")
            print(f"     类型: {f.factor_type}, 字段: {f.field}")
            print(f"     方向: {direction}, 权重: {f.weight:.1%}")
            print(f"     标准化: {f.normalize}, 中性化: {neutralize}")

        print(f"\n组合构建配置:")
        print(f"  选股方式: {config.portfolio_config['select_method']}")
        print(f"  选择数量: {config.portfolio_config['top_n']}")
        print(f"  权重方式: {config.portfolio_config['weight_method']}")

        print(f"\n调仓配置:")
        print(f"  频率: {config.rebalance_config['frequency']}")
        print(f"  调仓日: {config.rebalance_config.get('rebalance_day', 'N/A')}")

        # 验证配置
        print(f"\n📊 验证配置:")
        try:
            StrategyConfigLoader.validate_config(config)
            print(f"  ✅ 配置验证通过")
        except Exception as e:
            print(f"  ❌ 配置验证失败: {e}")

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. 测试多因子策略
    print(f"\n\n📄 测试2: 多因子策略配置")
    print("-" * 80)

    multi_config_path = project_root / 'config' / 'examples' / 'multi_factor_strategy.yaml'

    try:
        multi_config = StrategyConfigLoader.load_from_yaml(str(multi_config_path))

        print(f"✅ 配置加载成功!")
        print(f"\n策略信息:")
        print(f"  名称: {multi_config.name}")
        print(f"  描述: {multi_config.description}")

        print(f"\n打分因子 ({len(multi_config.scoring_factors)}个):")
        total_weight = 0
        for i, f in enumerate(multi_config.scoring_factors, 1):
            direction = "正相关" if f.direction == 1 else "负相关"
            neutralize = "是" if f.neutralize.get('enabled', False) else "否"
            total_weight += f.weight
            print(f"  {i}. {f.name}")
            print(f"     方向: {direction}, 权重: {f.weight:.1%}, 中性化: {neutralize}")

        print(f"\n  权重总和: {total_weight:.3f}")

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()

    # 3. 测试Alpha101策略
    print(f"\n\n📄 测试3: Alpha101策略配置")
    print("-" * 80)

    alpha_config_path = project_root / 'config' / 'examples' / 'alpha101_strategy.yaml'

    try:
        alpha_config = StrategyConfigLoader.load_from_yaml(str(alpha_config_path))

        print(f"✅ 配置加载成功!")
        print(f"\n策略信息:")
        print(f"  名称: {alpha_config.name}")

        print(f"\n打分因子 ({len(alpha_config.scoring_factors)}个):")
        for i, f in enumerate(alpha_config.scoring_factors, 1):
            print(f"  {i}. {f.name} - {f.factor_type} - 权重{f.weight:.1%}")

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n\n" + "=" * 80)
    print("✅ YAML配置加载测试完成!")
    print("=" * 80)

    print(f"\n💡 下一步:")
    print(f"   1. 配置驱动策略框架已完成")
    print(f"   2. 支持YAML配置文件定义策略")
    print(f"   3. 包含排除条件、多因子打分、组合构建等完整流程")
    print(f"   4. 可以开始集成到回测引擎")


if __name__ == "__main__":
    test_yaml_config_loading()
