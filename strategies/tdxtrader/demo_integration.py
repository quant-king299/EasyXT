"""
TDX与EasyXT集成演示脚本
展示如何使用集成方案进行通达信预警交易
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from easyxt_tdx_integration import TDXEasyXTIntegration

def main():
    """主函数"""
    print("🚀 TDX与EasyXT集成演示")
    print("=" * 50)
    
    # 初始化集成器
    # 注意：账户ID和QMT路径将从统一配置文件中自动读取
    integration = TDXEasyXTIntegration("test_config.json")
    
    # 显示配置信息
    print("配置信息:")
    print(f"  预警文件路径: {integration.config.get('tdx_file_path')}")
    print(f"  轮询间隔: {integration.config.get('interval')}秒")
    print(f"  买入信号: {integration.config.get('buy_signals')}")
    print(f"  卖出信号: {integration.config.get('sell_signals')}")
    
    # 从统一配置中获取账户信息
    from easy_xt.config import config
    account_id = config.get('settings.account.account_id')
    qmt_path = config.get_userdata_path()
    
    print(f"\n交易账户信息:")
    print(f"  账户ID: {account_id}")
    print(f"  QMT路径: {qmt_path}")
    
    # 检查配置是否完整
    if not account_id:
        print("❌ 错误: 未配置账户ID，请在config/unified_config.json中设置")
        return
    
    if not qmt_path:
        print("❌ 错误: 未配置QMT路径，请在config/unified_config.json中设置")
        return
    
    print("\n✅ 配置检查通过")
    print("\n如需启动交易系统，请取消注释下面的代码:")
    # integration.start_trading()

if __name__ == "__main__":
    main()