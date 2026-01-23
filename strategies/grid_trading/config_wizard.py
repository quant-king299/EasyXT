#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国债ETF网格交易 - 配置向导

帮助用户快速配置参数
"""

import os
import json


def print_banner():
    """打印横幅"""
    print("\n" + "="*60)
    print(" "*15 + "国债ETF网格交易配置向导")
    print("="*60 + "\n")


def load_config():
    """加载现有配置"""
    config_file = 'bond_etf_config.json'

    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {
            "账户ID": "",
            "账户类型": "STOCK",
            "股票池": ["511090.SH", "511130.SH"],
            "股票名称": ["30年国债", "30年国债"],
            "买入涨跌幅": -0.15,
            "卖出涨跌幅": 0.15,
            "单次交易数量": 100,
            "最大持仓数量": 500,
            "价格模式": 5,
            "交易时间段": 8,
            "交易开始时间": 9,
            "交易结束时间": 15,
            "是否参加集合竞价": False,
            "是否测试": True,
            "日志文件路径": "",
            "监控间隔": 3,
            "统计周期": 60
        }


def save_config(config):
    """保存配置"""
    config_file = 'bond_etf_config.json'

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 配置已保存到: {config_file}")


def interactive_config():
    """交互式配置"""
    config = load_config()

    print("📋 当前配置:")
    print("-"*60)
    print(f"账户ID: {'*' * 10 if config['账户ID'] else '未设置'}")
    print(f"股票池: {config['股票池']}")
    print(f"网格阈值: 买入{config['买入涨跌幅']}% / 卖出{config['卖出涨跌幅']}%")
    print(f"交易数量: {config['单次交易数量']}股/次")
    print(f"最大持仓: {config['最大持仓数量']}股")
    print(f"测试模式: {'是' if config['是否测试'] else '否'}")
    print("-"*60)

    print("\n是否修改配置? (y/n): ", end='')
    choice = input().strip().lower()

    if choice != 'y':
        print("配置未修改")
        return config

    # 账户配置
    print("\n" + "="*60)
    print("【账户配置】")
    print("="*60)

    print(f"\n当前账户ID: {'*' * 10 if config['账户ID'] else '未设置'}")
    print("是否修改账户ID? (y/n): ", end='')
    if input().strip().lower() == 'y':
        account_id = input("请输入账户ID: ").strip()
        if account_id:
            config['账户ID'] = account_id
            print("✅ 账户ID已更新")
        else:
            print("⚠️ 账户ID为空，将以测试模式运行")

    # 策略配置
    print("\n" + "="*60)
    print("【策略配置】")
    print("="*60)

    print("\n请选择风险等级:")
    print("  1. 保守型 (网格0.2%, 100股/次)")
    print("  2. 稳健型 (网格0.15%, 200股/次) [推荐]")
    print("  3. 激进型 (网格0.1%, 500股/次)")
    print("  4. 自定义")

    print("\n请选择 (1-4): ", end='')
    risk_level = input().strip()

    if risk_level == '1':
        config['买入涨跌幅'] = -0.2
        config['卖出涨跌幅'] = 0.2
        config['单次交易数量'] = 100
        config['最大持仓数量'] = 300
        print("✅ 已设置为保守型参数")
    elif risk_level == '2':
        config['买入涨跌幅'] = -0.15
        config['卖出涨跌幅'] = 0.15
        config['单次交易数量'] = 200
        config['最大持仓数量'] = 500
        print("✅ 已设置为稳健型参数")
    elif risk_level == '3':
        config['买入涨跌幅'] = -0.1
        config['卖出涨跌幅'] = 0.1
        config['单次交易数量'] = 500
        config['最大持仓数量'] = 2000
        print("✅ 已设置为激进型参数")
    elif risk_level == '4':
        print("\n自定义参数:")
        config['买入涨跌幅'] = float(input("  买入涨跌幅 (如-0.15): "))
        config['卖出涨跌幅'] = float(input("  卖出涨跌幅 (如0.15): "))
        config['单次交易数量'] = int(input("  单次交易数量 (股): "))
        config['最大持仓数量'] = int(input("  最大持仓数量 (股): "))

    # 交易模式
    print("\n" + "="*60)
    print("【交易模式】")
    print("="*60)

    print("\n当前模式:", "测试模式" if config['是否测试'] else "实盘模式")
    print("是否切换到实盘模式? (y/n): ", end='')
    if input().strip().lower() == 'y':
        confirm = input("⚠️ 确认切换到实盘? (yes/no): ")
        if confirm.lower() == 'yes':
            config['是否测试'] = False
            print("✅ 已切换到实盘模式")
        else:
            print("已取消，保持测试模式")
    else:
        print("保持测试模式")

    # 保存配置
    save_config(config)

    # 显示最终配置
    print("\n" + "="*60)
    print("【最终配置】")
    print("="*60)
    print(f"账户ID: {'*' * 10 if config['账户ID'] else '未设置'}")
    print(f"股票池: {config['股票池']}")
    print(f"买入阈值: {config['买入涨跌幅']}%")
    print(f"卖出阈值: {config['卖出涨跌幅']}%")
    print(f"交易数量: {config['单次交易数量']}股/次")
    print(f"最大持仓: {config['最大持仓数量']}股")
    print(f"交易模式: {'测试模式' if config['是否测试'] else '实盘模式'}")
    print("="*60)

    print("\n✅ 配置完成！")
    print("\n下一步:")
    print("  1. 运行测试: python test_bond_etf_grid.py")
    print("  2. 或双击: 启动国债ETF网格测试.bat")

    return config


def main():
    """主函数"""
    print_banner()
    interactive_config()


if __name__ == "__main__":
    main()
