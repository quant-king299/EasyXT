import logging

logger = logging.getLogger(__name__)
#!/usr/bin/env python3
"""
调整跟随比例脚本
根据可用资金自动调整合适的跟随比例
"""

import json
import sys
from pathlib import Path

def adjust_follow_ratio():
    """调整跟随比例"""
    config_file = Path(__file__).parent / "config" / "real_trading.json"
    
    try:
        # 读取配置
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        logger.info("🔧 当前配置:")
        current_ratio = config['portfolios']['ZH2863835']['follow_ratio']
        logger.info(f"   当前跟随比例: {current_ratio:.1%}")
        
        # 根据测试结果计算建议比例
        total_asset = 20770442.60  # 总资产
        available_cash = 50000.00  # 可用资金
        target_positions = 10      # 目标持仓数
        
        # 计算安全的跟随比例
        safe_ratio_by_cash = (available_cash * 0.8) / total_asset  # 80%安全边际
        safe_ratio_per_position = safe_ratio_by_cash / target_positions
        
        logger.info(f"\n📊 资金分析:")
        logger.info(f"   总资产: {total_asset:,.2f} 元")
        logger.info(f"   可用资金: {available_cash:,.2f} 元")
        logger.info(f"   目标持仓数: {target_positions} 个")
        
        logger.info(f"\n💡 建议跟随比例:")
        logger.info(f"   基于可用资金: {safe_ratio_by_cash:.2%}")
        logger.info(f"   保守建议: {safe_ratio_by_cash * 0.5:.2%}")
        logger.info(f"   激进建议: {safe_ratio_by_cash:.2%}")
        
        # 提供选项
        logger.info(f"\n🎯 请选择跟随比例:")
        logger.info(f"   1. 保守 (1%): 每个持仓约 {total_asset * 0.01 / target_positions:,.0f} 元")
        logger.info(f"   2. 适中 (2%): 每个持仓约 {total_asset * 0.02 / target_positions:,.0f} 元")
        logger.info(f"   3. 基于可用资金 ({safe_ratio_by_cash:.1%}): 每个持仓约 {total_asset * safe_ratio_by_cash / target_positions:,.0f} 元")
        logger.info(f"   4. 自定义")
        logger.info(f"   5. 保持当前 ({current_ratio:.1%})")
        
        choice = input("\n请输入选择 (1-5): ").strip()
        
        new_ratio = current_ratio
        if choice == "1":
            new_ratio = 0.01
        elif choice == "2":
            new_ratio = 0.02
        elif choice == "3":
            new_ratio = safe_ratio_by_cash
        elif choice == "4":
            try:
                custom_percent = float(input("请输入跟随比例百分比 (如输入2表示2%): "))
                new_ratio = custom_percent / 100
            except ValueError:
                logger.info("❌ 输入无效，保持当前比例")
                return
        elif choice == "5":
            logger.info("✅ 保持当前跟随比例")
            return
        else:
            logger.info("❌ 选择无效，保持当前比例")
            return
        
        # 验证新比例
        estimated_per_position = total_asset * new_ratio / target_positions
        if estimated_per_position > available_cash * 0.8:
            logger.info(f"⚠️ 警告: 每个持仓需要约 {estimated_per_position:,.0f} 元，可能超出可用资金")
            confirm = input("是否继续? (y/N): ").strip().lower()
            if confirm != 'y':
                logger.info("❌ 用户取消")
                return
        
        # 更新配置
        config['portfolios']['ZH2863835']['follow_ratio'] = new_ratio
        
        # 保存配置
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✅ 跟随比例已更新:")
        logger.info(f"   从 {current_ratio:.1%} 调整为 {new_ratio:.1%}")
        logger.info(f"   每个持仓预计: {estimated_per_position:,.0f} 元")
        logger.info(f"   配置文件已保存: {config_file}")
        
    except Exception as e:
        logger.info(f"❌ 调整失败: {e}")

if __name__ == "__main__":
    adjust_follow_ratio()