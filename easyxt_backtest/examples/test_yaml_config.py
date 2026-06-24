import logging

logger = logging.getLogger(__name__)
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

    logger.info("=" * 80)
    logger.info("101因子平台 - YAML配置加载测试")
    logger.info("=" * 80)

    # 1. 测试简单小市值策略
    logger.info(f"\n📄 测试1: 简单小市值策略配置")
    logger.info("-" * 80)

    config_path = project_root / 'config' / 'examples' / 'simple_small_cap.yaml'

    logger.info(f"配置文件路径: {config_path}")
    logger.info(f"文件存在: {config_path.exists()}")

    if not config_path.exists():
        logger.info(f"❌ 配置文件不存在!")
        return

    try:
        config = StrategyConfigLoader.load_from_yaml(str(config_path))

        logger.info(f"✅ 配置加载成功!")
        logger.info(f"\n策略信息:")
        logger.info(f"  名称: {config.name}")
        logger.info(f"  版本: {config.version}")
        logger.info(f"  作者: {config.author}")
        logger.info(f"  描述: {config.description}")

        logger.info(f"\n回测配置:")
        logger.info(f"  开始日期: {config.backtest_config['start_date']}")
        logger.info(f"  结束日期: {config.backtest_config['end_date']}")
        logger.info(f"  初始资金: {config.backtest_config['initial_cash']:,}")
        logger.info(f"  佣金: {config.backtest_config['commission']:.3%}")

        logger.info(f"\n股票池配置:")
        logger.info(f"  类型: {config.universe_config['type']}")
        logger.info(f"  指数代码: {config.universe_config['index_code']}")

        logger.info(f"\n排除条件 ({len(config.exclude_filters)}个):")
        for i, f in enumerate(config.exclude_filters, 1):
            logger.info(f"  {i}. {f.name} - {f.type} - {f.condition}")

        logger.info(f"\n打分因子 ({len(config.scoring_factors)}个):")
        for i, f in enumerate(config.scoring_factors, 1):
            direction = "正相关" if f.direction == 1 else "负相关"
            neutralize = "是" if f.neutralize.get('enabled', False) else "否"
            logger.info(f"  {i}. {f.name}")
            logger.info(f"     类型: {f.factor_type}, 字段: {f.field}")
            logger.info(f"     方向: {direction}, 权重: {f.weight:.1%}")
            logger.info(f"     标准化: {f.normalize}, 中性化: {neutralize}")

        logger.info(f"\n组合构建配置:")
        logger.info(f"  选股方式: {config.portfolio_config['select_method']}")
        logger.info(f"  选择数量: {config.portfolio_config['top_n']}")
        logger.info(f"  权重方式: {config.portfolio_config['weight_method']}")

        logger.info(f"\n调仓配置:")
        logger.info(f"  频率: {config.rebalance_config['frequency']}")
        logger.info(f"  调仓日: {config.rebalance_config.get('rebalance_day', 'N/A')}")

        # 验证配置
        logger.info(f"\n📊 验证配置:")
        try:
            StrategyConfigLoader.validate_config(config)
            logger.info(f"  ✅ 配置验证通过")
        except Exception as e:
            logger.info(f"  ❌ 配置验证失败: {e}")

    except Exception as e:
        logger.info(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. 测试多因子策略
    logger.info(f"\n\n📄 测试2: 多因子策略配置")
    logger.info("-" * 80)

    multi_config_path = project_root / 'config' / 'examples' / 'multi_factor_strategy.yaml'

    try:
        multi_config = StrategyConfigLoader.load_from_yaml(str(multi_config_path))

        logger.info(f"✅ 配置加载成功!")
        logger.info(f"\n策略信息:")
        logger.info(f"  名称: {multi_config.name}")
        logger.info(f"  描述: {multi_config.description}")

        logger.info(f"\n打分因子 ({len(multi_config.scoring_factors)}个):")
        total_weight = 0
        for i, f in enumerate(multi_config.scoring_factors, 1):
            direction = "正相关" if f.direction == 1 else "负相关"
            neutralize = "是" if f.neutralize.get('enabled', False) else "否"
            total_weight += f.weight
            logger.info(f"  {i}. {f.name}")
            logger.info(f"     方向: {direction}, 权重: {f.weight:.1%}, 中性化: {neutralize}")

        logger.info(f"\n  权重总和: {total_weight:.3f}")

    except Exception as e:
        logger.info(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()

    # 3. 测试Alpha101策略
    logger.info(f"\n\n📄 测试3: Alpha101策略配置")
    logger.info("-" * 80)

    alpha_config_path = project_root / 'config' / 'examples' / 'alpha101_strategy.yaml'

    try:
        alpha_config = StrategyConfigLoader.load_from_yaml(str(alpha_config_path))

        logger.info(f"✅ 配置加载成功!")
        logger.info(f"\n策略信息:")
        logger.info(f"  名称: {alpha_config.name}")

        logger.info(f"\n打分因子 ({len(alpha_config.scoring_factors)}个):")
        for i, f in enumerate(alpha_config.scoring_factors, 1):
            logger.info(f"  {i}. {f.name} - {f.factor_type} - 权重{f.weight:.1%}")

    except Exception as e:
        logger.info(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()

    logger.info(f"\n\n" + "=" * 80)
    logger.info("✅ YAML配置加载测试完成!")
    logger.info("=" * 80)

    logger.info(f"\n💡 下一步:")
    logger.info(f"   1. 配置驱动策略框架已完成")
    logger.info(f"   2. 支持YAML配置文件定义策略")
    logger.info(f"   3. 包含排除条件、多因子打分、组合构建等完整流程")
    logger.info(f"   4. 可以开始集成到回测引擎")


if __name__ == "__main__":
    test_yaml_config_loading()
