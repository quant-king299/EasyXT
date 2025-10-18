#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第一个MiniQMT + JQ2QMT集成示例
演示如何在策略中使用JQ2QMT功能
"""

import requests
import json
import time
from datetime import datetime

class MiniQMTJQ2QMTStrategy:
    def __init__(self, jq2qmt_url="http://localhost:5000"):
        self.jq2qmt_url = jq2qmt_url
        self.positions = []
        
    def sync_positions_to_jq2qmt(self, positions):
        """将持仓同步到JQ2QMT"""
        try:
            response = requests.post(
                f"{self.jq2qmt_url}/sync_positions",
                json={"positions": positions},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ 持仓同步成功: {result.get('message')}")
                    return True
                else:
                    print(f"❌ 持仓同步失败: {result.get('message')}")
                    return False
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 同步异常: {e}")
            return False
    
    def get_positions_from_jq2qmt(self):
        """从JQ2QMT获取持仓"""
        try:
            response = requests.get(f"{self.jq2qmt_url}/get_positions", timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    positions = result.get('positions', [])
                    print(f"✅ 获取持仓成功: {len(positions)} 条")
                    return positions
                else:
                    print(f"❌ 获取失败: {result.get('message')}")
                    return []
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ 获取异常: {e}")
            return []
    
    def run_example_strategy(self):
        """运行示例策略"""
        print("🚀 启动MiniQMT + JQ2QMT集成策略示例")
        print("="*50)
        
        # 模拟策略产生的持仓
        strategy_positions = [
            {
                "symbol": "000001.SZ",
                "name": "平安银行",
                "quantity": 1000,
                "price": 12.50,
                "value": 12500,
                "strategy": "双均线策略"
            },
            {
                "symbol": "600036.SH", 
                "name": "招商银行",
                "quantity": 500,
                "price": 35.20,
                "value": 17600,
                "strategy": "MACD策略"
            }
        ]
        
        print("📊 策略生成的持仓:")
        for pos in strategy_positions:
            print(f"   • {pos['name']}({pos['symbol']}): {pos['quantity']}股 @ ¥{pos['price']}")
        
        # 1. 同步持仓到JQ2QMT
        print("\n🔄 步骤1: 同步持仓到JQ2QMT...")
        sync_success = self.sync_positions_to_jq2qmt(strategy_positions)
        
        if sync_success:
            # 2. 从JQ2QMT获取持仓验证
            print("\n📥 步骤2: 从JQ2QMT获取持仓验证...")
            retrieved_positions = self.get_positions_from_jq2qmt()
            
            if retrieved_positions:
                print("\n✅ 集成测试成功！")
                print("📋 JQ2QMT中的持仓:")
                for pos in retrieved_positions:
                    print(f"   • {pos.get('name', 'N/A')}({pos.get('symbol', 'N/A')}): {pos.get('quantity', 0)}股")
                
                # 3. 模拟策略决策
                print("\n🧠 步骤3: 模拟策略决策...")
                self.make_strategy_decision(retrieved_positions)
            else:
                print("❌ 无法获取持仓数据")
        else:
            print("❌ 持仓同步失败，无法继续")
    
    def make_strategy_decision(self, positions):
        """模拟策略决策过程"""
        print("   🤔 分析当前持仓...")
        
        total_value = sum(pos.get('value', 0) for pos in positions)
        print(f"   💰 总持仓价值: ¥{total_value:,.2f}")
        
        # 模拟决策逻辑
        if total_value > 20000:
            print("   📈 决策: 持仓较重，考虑减仓")
            action = "减仓"
        elif total_value < 10000:
            print("   📉 决策: 持仓较轻，考虑加仓")
            action = "加仓"
        else:
            print("   ⚖️ 决策: 持仓适中，保持观望")
            action = "观望"
        
        # 记录决策
        decision = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_value": total_value,
            "action": action,
            "positions_count": len(positions)
        }
        
        print(f"   📝 决策记录: {decision}")
        return decision

def main():
    """主函数"""
    print("🎯 MiniQMT + JQ2QMT 集成策略示例")
    print(f"⏰ 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 创建策略实例
    strategy = MiniQMTJQ2QMTStrategy()
    
    # 运行示例
    strategy.run_example_strategy()
    
    print("\n" + "="*50)
    print("🎉 示例运行完成！")
    print("\n💡 这个示例展示了:")
    print("   • 如何将策略持仓同步到JQ2QMT")
    print("   • 如何从JQ2QMT获取持仓数据")
    print("   • 如何基于持仓数据做策略决策")
    print("\n📋 您可以基于这个模板开发自己的策略！")

if __name__ == "__main__":
    main()