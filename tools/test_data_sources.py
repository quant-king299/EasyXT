#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试所有数据源的连接状态
验证QMT、TDX、Eastmoney是否正常工作
"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def test_all_data_sources():
    """测试所有数据源的连接状态"""
    print("=" * 80)
    print("数据源连接状态测试")
    print("=" * 80)

    # 设置日志级别为DEBUG，以便查看详细信息
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

    try:
        from easy_xt import get_api

        # 1. 初始化API
        print("\n[步骤1] 初始化数据API")
        print("-" * 80)
        api = get_api()
        success = api.init_data()

        if not success:
            print("\n[X] 数据服务初始化失败，无法继续测试")
            return

        # 2. 检查当前使用的数据源
        print("\n[步骤2] 检查当前数据源")
        print("-" * 80)
        if hasattr(api, 'get_active_source'):
            active_source = api.get_active_source()
            print(f"当前主数据源: {active_source.upper()}")
        else:
            print("当前数据源: unknown")

        # 3. 检查备用数据源状态
        print("\n[步骤3] 检查备用数据源状态")
        print("-" * 80)

        # 检查TDX
        if hasattr(api, 'data') and hasattr(api.data, '_tdx_provider'):
            tdx_provider = api.data._tdx_provider
            if tdx_provider is not None:
                if hasattr(tdx_provider, 'connected'):
                    tdx_connected = tdx_provider.connected
                    print(f"TDX状态: {'[OK] 已连接' if tdx_connected else '[X] 未连接'}")
                else:
                    print("TDX状态: [!] 连接状态未知")
            else:
                print("TDX状态: [X] 未初始化")
        else:
            print("TDX状态: [X] 不可用")

        # 检查Eastmoney
        if hasattr(api, 'data') and hasattr(api.data, '_eastmoney_provider'):
            eastmoney_provider = api.data._eastmoney_provider
            if eastmoney_provider is not None:
                if hasattr(eastmoney_provider, 'connected'):
                    eastmoney_connected = eastmoney_provider.connected
                    print(f"Eastmoney状态: {'[OK] 已连接' if eastmoney_connected else '[X] 未连接'}")
                else:
                    print("Eastmoney状态: [!] 连接状态未知")
            else:
                print("Eastmoney状态: [X] 未初始化")
        else:
            print("Eastmoney状态: [X] 不可用")

        # 4. 测试每个数据源
        print("\n[步骤4] 测试每个数据源")
        print("-" * 80)
        test_code = '000001.SZ'

        # 测试QMT
        print("\n1. 测试 QMT 数据源")
        try:
            if hasattr(api, 'data') and api.data._active_source == 'qmt':
                print("  QMT是主数据源，跳过测试")
            else:
                # 尝试使用QMT
                from easy_xt.data_api import TDX_AVAILABLE
                if not TDX_AVAILABLE:
                    print("  QMT不可用")
                else:
                    print("  QMT已连接")
        except Exception as e:
            print(f"  QMT测试失败: {e}")

        # 测试TDX
        print("\n2. 测试 TDX 数据源")
        print("  提示: 使用 count 参数获取最近数据（更可靠）")
        try:
            # 使用count而不是日期范围，TDX对count支持更好
            test_data = api.data._get_price_tdx(
                codes=[test_code],
                start='',  # 留空，使用count
                end='',    # 留空，使用count
                period='1d',
                count=10,  # 获取最近10条
                fields=['open', 'high', 'low', 'close', 'volume'],
                adjust='front'
            )
            if test_data is not None and len(test_data) > 0:
                print(f"  [OK] TDX 测试成功！获取 {len(test_data)} 条数据")
                print(f"     时间范围: {test_data['time'].min()} 到 {test_data['time'].max()}")
            else:
                print("  [X] TDX 测试失败：返回空数据")
        except Exception as e:
            print(f"  [X] TDX 测试失败: {str(e)[:100]}")

        # 测试Eastmoney
        print("\n3. 测试 Eastmoney 数据源")
        print("  提示: Eastmoney需要日期范围，使用2024年数据")
        try:
            # Eastmoney需要日期范围，使用一个较大的范围
            import datetime
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

            test_data = api.data._get_price_eastmoney(
                codes=[test_code],
                start=start_date,
                end=end_date,
                period='1d',
                count=10,
                fields=['open', 'high', 'low', 'close', 'volume'],
                adjust='front'
            )
            if test_data is not None and len(test_data) > 0:
                print(f"  [OK] Eastmoney 测试成功！获取 {len(test_data)} 条数据")
                print(f"     时间范围: {test_data['time'].min()} 到 {test_data['time'].max()}")
            else:
                print("  [X] Eastmoney 测试失败：返回空数据")
        except Exception as e:
            print(f"  [X] Eastmoney 测试失败: {str(e)[:100]}")

        print("\n" + "=" * 80)
        print("测试完成")
        print("=" * 80)

        # 5. 使用建议
        print("\n[TIP] 使用建议：")
        print("   - QMT：最稳定，数据最全，推荐优先使用")
        print("   - TDX：QMT关闭时的备用，支持实时和历史数据")
        print("   - Eastmoney：QMT和TDX都失败时的最后选择")
        print("\n[CHART] 降级顺序：")
        print("   (1) QMT (主数据源)")
        print("   (2) TDX (备用数据源)")
        print("   (3) Eastmoney (最后备用)")

    except Exception as e:
        print(f"\n[X] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_all_data_sources()
