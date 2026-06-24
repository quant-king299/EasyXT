# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
"""
ATR动态网格策略测试脚本
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# ========================================
# 路径配置：使用统一路径管理器
# ========================================
import os
# 先添加项目根目录到 Python 路径（用于导入 core.path_manager）
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 使用统一路径管理器初始化所有路径
from core.path_manager import init_paths
init_paths()

# 现在可以导入项目中的其他模块了
import easy_xt
from ATR动态网格策略 import ATR动态网格策略


def load_config(config_file='atr_grid_config.json'):
    """加载配置文件"""
    config_path = Path(__file__).parent / config_file

    if not config_path.exists():
        logger.info(f"❌ 配置文件不存在: {config_file}")
        logger.info(f"   请先创建配置文件！")
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"✓ 配置文件加载成功: {config_file}")
        return config
    except Exception as e:
        logger.info(f"❌ 配置文件加载失败: {str(e)}")
        return None


def print_config_summary(config):
    """打印配置摘要"""
    logger.info("\n" + "=" * 60)
    logger.info("策略配置".center(50))
    logger.info("=" * 60)

    logger.info(f"\n📊 基本信息:")
    logger.info(f"   账户ID: {config.get('账户ID')}")
    logger.info(f"   账户类型: {config.get('账户类型')}")
    logger.info(f"   股票池: {config.get('股票池')}")

    logger.info(f"\n📈 ATR参数:")
    logger.info(f"   ATR周期: {config.get('ATR周期', 14)}")
    logger.info(f"   ATR倍数: {config.get('ATR倍数', 0.5)}")
    logger.info(f"   最小网格间距: {config.get('最小网格间距', 0.1)}%")
    logger.info(f"   最大网格间距: {config.get('最大网格间距', 1.0)}%")

    logger.info(f"\n🎯 网格参数:")
    logger.info(f"   网格层数: {config.get('网格层数', 5)}")
    logger.info(f"   单次交易数量: {config.get('单次交易数量', 100)}股")
    logger.info(f"   最大持仓数量: {config.get('最大持仓数量', 1000)}股")

    logger.info(f"\n🔄 基准价调整:")
    logger.info(f"   均线周期: {config.get('均线周期', 20)}")
    logger.info(f"   趋势阈值: {config.get('趋势阈值', 0.5)}%")

    logger.info(f"\n⏰ 交易时间:")
    logger.info(f"   交易时段: {config.get('交易时间段', 8)} (8=工作日)")
    logger.info(f"   开始时间: {config.get('交易开始时间', 9)}:00")
    logger.info(f"   结束时间: {config.get('交易结束时间', 24)}:00")
    logger.info(f"   参加集合竞价: {'是' if config.get('是否参加集合竞价', False) else '否'}")

    logger.info(f"\n🚀 运行模式:")
    mode = "🧪 测试模式" if config.get('是否测试', False) else "🔴 实盘模式"
    logger.info(f"   {mode}")

    logger.info("\n" + "=" * 60)


def check_market_status(api, stock_pool):
    """检查市场状态"""
    logger.info("\n📊 市场状态检查:")
    logger.info("-" * 60)

    try:
        # 检查数据服务连接
        if hasattr(api, 'init_data'):
            if api.init_data():
                logger.info("✓ 数据服务连接正常")
            else:
                logger.info("⚠ 数据服务连接失败")

        # 检查交易服务连接
        if hasattr(api, 'init_trade'):
            try:
                if api.init_trade():
                    logger.info("✓ 交易服务连接正常")
                else:
                    logger.info("⚠ 警告: 交易服务连接失败，请在QMT客户端手动登录交易账户")
            except Exception as e:
                logger.info(f"⚠ 警告: 交易服务初始化异常 - {str(e)}")
                logger.info("   提示: 请在QMT客户端手动登录交易账户")

        # 获取股票行情
        for stock_code in stock_pool:
            try:
                # 获取行情（返回DataFrame）
                price_df = api.data.get_current_price([stock_code])

                if price_df is not None and not price_df.empty:
                    # 从DataFrame中提取数据
                    stock_data = price_df[price_df['code'] == stock_code]
                    if not stock_data.empty:
                        price = stock_data.iloc[0]['price']
                        high = stock_data.iloc[0].get('high', price)
                        low = stock_data.iloc[0].get('low', price)
                        volume = stock_data.iloc[0].get('volume', 0)

                        logger.info(f"\n{stock_code}:")
                        logger.info(f"   当前价: {price:.3f}")
                        logger.info(f"   最高价: {high:.3f}")
                        logger.info(f"   最低价: {low:.3f}")
                        logger.info(f"   成交量: {volume}")
                    else:
                        logger.info(f"\n{stock_code}: ⚠ 未找到该股票数据")
                else:
                    logger.info(f"\n{stock_code}: ⚠ 无法获取行情数据")
            except Exception as e:
                logger.info(f"\n{stock_code}: ✗ 获取行情失败 - {str(e)}")

    except Exception as e:
        logger.info(f"✗ 市场状态检查失败: {str(e)}")

    logger.info("-" * 60)


def check_account_status(api, account_id):
    """检查账户状态"""
    logger.info("\n💰 账户状态:")
    logger.info("-" * 60)

    try:
        asset = api.trade.get_account_asset(account_id)

        if asset:
            total_asset = asset.get('总资产', 0)
            cash = asset.get('可用资金', 0)
            market_value = asset.get('证券市值', 0)
            position_pnl = asset.get('持仓盈亏', 0)

            logger.info(f"总资产: {total_asset:,.2f} 元")
            logger.info(f"可用资金: {cash:,.2f} 元")
            logger.info(f"证券市值: {market_value:,.2f} 元")
            logger.info(f"持仓盈亏: {position_pnl:,.2f} 元")
        else:
            logger.info("⚠ 无法获取账户信息")

    except Exception as e:
        logger.info(f"✗ 获取账户状态失败: {str(e)}")

    logger.info("-" * 60)


def run_strategy_test(config):
    """运行策略测试"""
    logger.info("\n" + "=" * 60)
    logger.info("启动ATR动态网格策略".center(50))
    logger.info("=" * 60)

    # 初始化API
    try:
        api = easy_xt.get_api()
        logger.info("✓ API连接成功")
    except Exception as e:
        logger.info(f"✗ API连接失败: {str(e)}")
        return

    # 检查市场状态
    check_market_status(api, config.get('股票池', []))

    # 检查账户状态
    check_account_status(api, config.get('账户ID'))

    # 创建策略实例
    try:
        strategy = ATR动态网格策略(config)
        logger.info("\n✓ 策略实例创建成功")
    except Exception as e:
        logger.info(f"\n✗ 策略实例创建失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # 确认启动
    if config.get('是否测试', False):
        logger.info("\n🧪 测试模式启动...")
    else:
        logger.info("\n🔴 实盘模式启动...")
        response = input("\n确认启动实盘交易？(输入 'yes' 确认): ")
        if response.lower() != 'yes':
            logger.info("已取消启动")
            return

    # 启动策略
    try:
        strategy.start()
    except KeyboardInterrupt:
        logger.info("\n\n策略已手动停止")
    except Exception as e:
        logger.info(f"\n\n策略运行异常: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    logger.info("\n" + "=" * 60)
    logger.info("ATR动态网格策略测试程序".center(50))
    logger.info("=" * 60)

    # 加载配置
    config = load_config()
    if not config:
        return

    # 打印配置摘要
    print_config_summary(config)

    # 运行策略
    run_strategy_test(config)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n程序已退出")
    except Exception as e:
        logger.info(f"\n\n程序异常: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("\n" + "=" * 60)
        logger.info("程序结束".center(50))
        logger.info("=" * 60)
        input("\n按任意键退出...")
