#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球跟单系统 - 带初始同步的启动脚本
启动时立即根据雪球组合当前持仓进行调仓，然后监控变化
"""

import os
import sys
import json
import time
import asyncio
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """设置日志"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"xueqiu_sync_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def print_banner():
    """显示启动横幅"""
    print("=" * 80)
    print("🚀 雪球跟单系统 - 初始同步版")
    print("🔄 启动时立即根据雪球组合当前持仓进行调仓")
    print("=" * 80)
    
    # 先加载配置获取组合信息
    config = load_config()
    
    # 尝试从配置管理器获取启用的组合
    try:
        from strategies.xueqiu_follow.core.config_manager import ConfigManager
        config_manager = ConfigManager("strategies/xueqiu_follow/config/unified_config.json")
        config_manager.load_all_configs()  # 确保加载所有配置
        
        # 调试信息 - 检查_portfolios内容
        print(f"DEBUG: _portfolios类型: {type(config_manager._portfolios)}")
        print(f"DEBUG: _portfolios内容: {config_manager._portfolios}")
        
        # 正确获取组合列表：从_portfolios字典中获取portfolios键的值
        if isinstance(config_manager._portfolios, dict) and 'portfolios' in config_manager._portfolios:
            all_portfolios = config_manager._portfolios['portfolios']
        else:
            all_portfolios = []
        
        # 过滤启用的组合
        enabled_portfolios = [p for p in all_portfolios if p.get('enabled', False)]
        
        # 调试信息
        print(f"DEBUG: 获取到的启用组合数量: {len(enabled_portfolios)}")
        for i, portfolio in enumerate(enabled_portfolios):
            print(f"DEBUG: 组合 {i}: {portfolio}")
        
        if enabled_portfolios:
            portfolio = enabled_portfolios[0]
            portfolio_code = portfolio.get('code', portfolio.get('symbol', '未知'))
            account_id = config.get('settings', {}).get('account', {}).get('account_id', '未配置') if config else '未配置'
            
            print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 跟单组合: {portfolio_code}")
            print(f"🏦 交易账号: {account_id}")
        else:
            print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 跟单组合: 未配置")
            print(f"🏦 交易账号: 未配置")
    except Exception as e:
        print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 跟单组合: ZH3368671")
        print(f"🏦 交易账号: 39020958")
        print(f"⚠️ 配置加载警告: {e}")
    
    print(f"💰 交易模式: 真实交易模式")
    print(f"🔧 交易接口: EasyXT (高级封装)")
    print("=" * 80)

def safety_confirmation():
    """安全确认流程"""
    print("\n⚠️" + "⚠️" * 19)
    print("重要安全提醒")
    print("⚠️" + "⚠️" * 19)
    print("此版本将执行真实交易操作！")
    print("- 系统启动时会立即根据雪球组合进行调仓")
    print("- 会使用您的真实资金进行买卖")
    print("- 存在盈亏风险")
    print("- 请确保您了解相关风险")
    print("⚠️" + "⚠️" * 19)
    
    # 第一重确认
    confirm1 = input("\n🔐 第一重确认 - 输入 'YES' 确认启动真实交易: ").strip()
    if confirm1 != "YES":
        print("❌ 用户取消启动")
        return False
    
    # 第二重确认
    confirm2 = input("🔐 第二重确认 - 输入 'SYNC' 确认立即同步调仓: ").strip()
    if confirm2 != "SYNC":
        print("❌ 用户取消启动")
        return False
    
    # 第三重确认
    confirm3 = input("🔐 第三重确认 - 输入 'START' 最终确认: ").strip()
    if confirm3 != "START":
        print("❌ 用户取消启动")
        return False
    
    print("✅ 安全确认完成")
    return True

def load_config():
    """加载配置"""
    config_file = Path(__file__).parent / "config" / "real_trading.json"
    
    if not config_file.exists():
        # 如果真实交易配置不存在，使用统一配置
        config_file = Path(__file__).parent / "config" / "unified_config.json"
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 确保是真实交易模式
        if 'settings' not in config:
            config['settings'] = {}
        if 'trading' not in config['settings']:
            config['settings']['trading'] = {}
        
        config['settings']['trading']['trade_mode'] = 'real'
        
        print("✅ 真实交易配置加载成功")
        return config
    except Exception as e:
        print(f"❌ 真实交易配置加载失败: {e}")
        return None

def export_holdings_to_excel(holdings, portfolio_code, export_dir=None):
    """导出持仓数据到Excel文件（固定文件名覆盖写，受配置开关控制）"""
    try:
        # 读取统一配置以确定导出开关与目录
        export_enabled = False
        export_dir_name = "reports"
        try:
            cfg_path = Path(__file__).parent / "config" / "unified_config.json"
            if cfg_path.exists():
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                # 尝试两种键路径
                export_enabled = (
                    (cfg.get('settings', {}).get('export_holdings')) or
                    cfg.get('导出持仓') or
                    False
                )
                export_dir_name = (cfg.get('settings', {}).get('export_dir')) or "reports"
        except Exception:
            pass

        if not export_enabled:
            print("ℹ️ 导出开关关闭（settings.export_holdings/导出持仓），跳过Excel导出")
            return None

        # 导出目录
        if export_dir is None:
            export_dir = Path(__file__).parent.parent.parent / export_dir_name
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)

        # 创建DataFrame（增加类型检查与安全默认）
        df_data = []
        for holding in holdings:
            if not isinstance(holding, dict):
                continue
            weight = holding.get('weight', 0) or 0
            try:
                weight_pct = float(weight) * 100.0
            except Exception:
                weight_pct = 0.0
            df_data.append({
                '股票代码': holding.get('stock_symbol', '') or '',
                '股票名称': holding.get('stock_name', '') or '',
                '持仓比例(%)': weight_pct,
                '持仓市值': holding.get('market_value', 0) or 0,
                '持仓数量': holding.get('quantity', 0) or 0,
                '成本价': holding.get('cost_price', 0) or 0,
                '当前价': holding.get('current_price', 0) or 0
            })
        df = pd.DataFrame(df_data)
        if not df.empty:
            df = df.sort_values('持仓比例(%)', ascending=False)

        # 固定文件名，覆盖写
        filename = f"{portfolio_code}_持仓数据.xlsx"
        filepath = export_path / filename

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='持仓明细', index=False)
            summary_data = {
                '项目': ['组合代码', '持仓数量', '导出时间'],
                '数值': [portfolio_code, len(holdings), datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='汇总信息', index=False)

        print(f"✅ 持仓数据已导出到: {filepath}（覆盖写）")
        return filepath

    except Exception as e:
        print(f"❌ Excel导出失败: {e}")
        return None

def test_easyxt_connection(config):
    """测试 easy_xt 连接"""
    try:
        print("\n🔧 测试 EasyXT 交易API连接...")
        
        # 先尝试导入 xtquant
        try:
            # 添加 xtquant 路径
            xtquant_path = project_root / "xtquant"
            if str(xtquant_path) not in sys.path:
                sys.path.insert(0, str(xtquant_path))
            
            import xtquant.xttrader as xt
            print("xtquant高级交易模块导入成功")
        except ImportError as e:
            print(f"⚠️ xtquant高级交易模块导入失败: {e}")
        
        # 导入 easy_xt
        from easy_xt.advanced_trade_api import AdvancedTradeAPI
        
        # 获取配置
        qmt_path = config['settings']['account'].get('qmt_path')
        account_id = config['settings']['account']['account_id']
        
        # 检查QMT路径是否存在
        if not qmt_path:
            print("❌ EasyXT 连接测试失败: 'qmt_path'")
            return False
            
        if not os.path.exists(qmt_path):
            print(f"❌ QMT路径不存在: {qmt_path}")
            print("💡 请检查配置文件中的QMT路径设置")
            return False
        
        print(f"📁 QMT路径: {qmt_path}")
        print(f"🏦 交易账号: {account_id}")
        
        # 创建高级交易API
        session_id = f"xueqiu_test_{int(time.time())}"
        api = AdvancedTradeAPI()
        
        # 连接交易服务
        print("🚀 连接交易服务...")
        result = api.connect(qmt_path, session_id)
        
        if not result:
            print("❌ EasyXT 连接失败")
            return False
        
        print("✅ EasyXT 连接成功")
        
        # 添加账户
        print("📡 添加交易账户...")
        account_result = api.add_account(account_id)
        
        if not account_result:
            print("❌ 添加账户失败")
            api.disconnect()
            return False
        
        print("✅ 账户添加成功")
        
        # 测试账户查询
        try:
            print("💰 查询账户资产...")
            asset_info = api.get_account_asset_detailed(account_id)
            if asset_info:
                print("✅ 账户查询成功")
                total_asset = getattr(asset_info, 'total_asset', 0)
                cash = getattr(asset_info, 'cash', 0)
                print(f"💰 总资产: {total_asset:.2f}")
                print(f"💵 可用资金: {cash:.2f}")
            else:
                print("⚠️ 账户查询返回空数据")
        except Exception as e:
            print(f"⚠️ 账户查询失败: {e}")
        
        # 断开连接
        api.disconnect()
        return True
        
    except ImportError as e:
        print(f"❌ EasyXT 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ EasyXT 连接测试失败: {e}")
        return False

async def test_portfolio_data():
    """测试模式：直接获取组合持仓数据"""
    print("🔧 测试模式：直接获取组合持仓数据")
    
    # 加载配置
    config = load_config()
    if not config:
        print("❌ 配置加载失败")
        return
    
    # 获取启用组合
    try:
        from strategies.xueqiu_follow.core.config_manager import ConfigManager
        config_manager = ConfigManager("strategies/xueqiu_follow/config/unified_config.json")
        config_manager.load_all_configs()
        enabled_portfolios = config_manager.get_enabled_portfolios()
        
        if not enabled_portfolios:
            print("❌ 没有启用的组合")
            return
        
        portfolio = enabled_portfolios[0]
        portfolio_code = portfolio.get('code', portfolio.get('symbol', '未知'))
        print(f"📊 测试组合: {portfolio['name']} ({portfolio_code})")
        
        # 初始化数据采集器
        print("🚀 初始化数据采集器...")
        from strategies.xueqiu_follow.core.xueqiu_collector_real import XueqiuCollectorReal
        collector = XueqiuCollectorReal()
        
        # 初始化采集器
        print("🔧 初始化HTTP会话...")
        if not await collector.initialize():
            print("❌ 数据采集器初始化失败")
            return
        
        # 测试获取组合持仓
        print("📡 尝试获取组合持仓数据...")
        holdings = await collector.get_portfolio_holdings(portfolio_code)
        
        if holdings:
            print(f"✅ 成功获取到 {len(holdings)} 个持仓")
            for i, holding in enumerate(holdings[:5]):  # 只显示前5个
                stock_name = holding.get('stock_name', 'N/A')
                stock_symbol = holding.get('stock_symbol', 'N/A')
                weight = holding.get('weight', 0)
                print(f"  {i+1}. {stock_name} ({stock_symbol}) - {weight:.2%}")
            if len(holdings) > 5:
                print(f"  ... 还有 {len(holdings) - 5} 个持仓")
        else:
            print("❌ 未能获取到持仓数据")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数"""
    # 设置日志
    logger = setup_logging()
    
    try:
        # 显示启动横幅
        print_banner()
        
        # 安全确认
        if not safety_confirmation():
            return
        
        # 加载配置
        config = load_config()
        if not config:
            return
        
        # 显示配置信息
        print("\n📋 真实交易配置:")
        account_settings = config['settings'].get('account', {})
        trading_settings = config['settings'].get('trading', {})

        account_id = account_settings.get('account_id', '未配置')
        qmt_path = account_settings.get('qmt_path', '未配置')

        print(f"   🏦 交易账号: {account_id}")
        print(f"   📁 QMT路径: {qmt_path}")

        # 获取启用的组合（使用配置管理器）
        try:
            from strategies.xueqiu_follow.core.config_manager import ConfigManager
            config_manager = ConfigManager("strategies/xueqiu_follow/config/unified_config.json")
            config_manager.load_all_configs()  # 确保加载所有配置
            enabled_portfolios = config_manager.get_setting("portfolios", [])
            
            if enabled_portfolios:
                # 过滤启用的组合
                enabled_list = [p for p in enabled_portfolios if p.get('enabled', True)]
                if enabled_list:
                    portfolio = enabled_list[0]
                    portfolio_code = portfolio.get('code', portfolio.get('symbol', '未知'))
                    print(f"   📊 跟单组合: {portfolio.get('url', f'https://xueqiu.com/P/{portfolio_code}')}")
                    follow_ratio = portfolio.get('follow_ratio')
                    if follow_ratio is not None:
                        print(f"   📈 跟随比例: {follow_ratio:.1%}")
                    print(f"   💰 最大仓位: {portfolio.get('max_position', 8000)}元")
        except Exception as e:
            print(f"⚠️ 组合配置加载警告: {e}")
            # 回退到直接读取配置
            enabled_portfolios = []
            for portfolio_code, portfolio_config in config.get('portfolios', {}).items():
                if portfolio_config.get('enabled', False):
                    enabled_portfolios.append((portfolio_code, portfolio_config))
            
            if enabled_portfolios:
                portfolio_code, portfolio = enabled_portfolios[0]
                print(f"   📊 跟单组合: {portfolio.get('url', f'https://xueqiu.com/P/{portfolio_code}')}")
                follow_ratio = portfolio.get('follow_ratio')
                if follow_ratio is not None:
                    print(f"   📈 跟随比例: {follow_ratio:.1%}")
                print(f"   💰 最大仓位: {portfolio.get('max_position', 8000)}元")

        print(f"   💸 最大单笔: {trading_settings.get('max_single_amount', 5000)}元")
        print(f"   💰 最小交易: {trading_settings.get('min_trade_amount', 100)}元")

        
        # 测试 EasyXT 连接
        if not test_easyxt_connection(config):
            print("❌ EasyXT 连接测试失败，无法启动真实交易")
            return
        
        print("\n🚀 启动雪球跟单系统...")

        # 初始化配置管理器，使用真实交易配置
        from strategies.xueqiu_follow.core.config_manager import ConfigManager
        config_manager = ConfigManager("strategies/xueqiu_follow/config/unified_config.json")
        
        # 手动设置账户ID到配置管理器
        config_manager.set_setting('settings.account.account_id', config['settings']['account']['account_id'])
        config_manager.set_setting('account.account_id', config['settings']['account']['account_id'])
        
        # 使用统一配置管理器，无需额外加载
        
        # 初始化策略引擎
        from strategies.xueqiu_follow.core.strategy_engine import StrategyEngine
        strategy_engine = StrategyEngine(config_manager)
        
        # 初始化策略引擎
        print("🔧 初始化策略引擎...")
        if not await strategy_engine.initialize():
            print("❌ 策略引擎初始化失败")
            return
        
        print("✅ 策略引擎初始化成功")
        print("\n🔄 系统将首先执行初始同步调仓，然后开始监控组合变化...")
        # 获取启用的组合代码（使用配置管理器）
        portfolio_code = None
        try:
            # 正确获取组合列表：从_portfolios字典中获取portfolios键的值
            if isinstance(config_manager._portfolios, dict) and 'portfolios' in config_manager._portfolios:
                all_portfolios = config_manager._portfolios['portfolios']
            else:
                all_portfolios = []
            
            # 过滤启用的组合
            enabled_portfolios = [p for p in all_portfolios if p.get('enabled', False)]
            
            if enabled_portfolios:
                portfolio = enabled_portfolios[0]
                portfolio_code = portfolio.get('code', portfolio.get('symbol', None))
                print(f"✅ 使用组合: {portfolio.get('name', '未知')} ({portfolio_code})")
            else:
                portfolio_code = None
                print("❌ 没有启用的组合")
        except Exception as e:
            print(f"⚠️ 组合配置加载警告: {e}")
            # 回退到直接读取配置
            for code, portfolio_config in config.get('portfolios', {}).items():
                if portfolio_config.get('enabled', False):
                    portfolio_code = code
                    break
        
        if not portfolio_code:
            print("❌ 没有启用的组合")
            return
        
        print(f"📊 正在获取雪球组合 {portfolio_code} 的当前持仓...")
        
        # 启动策略（包含初始同步）
        print("\n🎯 开始执行策略...")
        await strategy_engine.start()
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️ 收到停止信号，正在安全关闭系统...")
        if 'strategy_engine' in locals():
            await strategy_engine.stop()
        print("👋 系统已安全关闭")
        
    except Exception as e:
        logger.error(f"系统运行异常: {e}")
        print(f"❌ 系统异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_portfolio_data())
    else:
        asyncio.run(main())