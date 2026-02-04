#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全数据更新工具
可以在GUI运行时安全更新数据
"""

import sys
import os
import psutil
import time
import duckdb
import pandas as pd
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'data_manager'))

from duckdb_connection_pool import get_db_manager


class SafeDataUpdater:
    """
    安全数据更新器

    功能：
    1. 检测GUI进程
    2. 请求关闭GUI或等待
    3. 使用连接管理器安全更新
    """

    def __init__(self, duckdb_path: str = r'D:/StockData/stock_data.ddb'):
        self.duckdb_path = duckdb_path
        self.manager = get_db_manager(duckdb_path)

    def find_gui_processes(self):
        """查找正在运行的GUI进程"""
        gui_processes = []

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline:
                    cmdline_str = ' '.join(cmdline)
                    # 查找包含GUI的Python进程
                    if 'python' in proc.info['name'].lower() and any(x in cmdline_str for x in ['gui_app', 'duckdb_data_manager', 'local_data_manager']):
                        gui_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': cmdline_str
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return gui_processes

    def check_database_lock(self):
        """检查数据库是否被锁定"""
        try:
            # 尝试以写模式连接
            con = duckdb.connect(self.duckdb_path, read_only=False)
            con.close()
            return False  # 未锁定
        except Exception as e:
            if "lock" in str(e).lower() or "already open" in str(e).lower():
                return True  # 已锁定
            raise

    def wait_for_lock_release(self, timeout: int = 60):
        """
        等待数据库锁释放

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功释放
        """
        print(f"等待数据库锁释放...（最多 {timeout} 秒）")

        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.check_database_lock():
                print("[OK] 数据库锁已释放")
                return True

            elapsed = int(time.time() - start_time)
            print(f"  等待中... {elapsed}/{timeout} 秒", end='\r')
            time.sleep(2)

        print("\n[ERROR] 等待超时")
        return False

    def safe_update(self, update_func, *args, **kwargs):
        """
        安全执行更新操作

        Args:
            update_func: 更新函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            更新结果
        """
        print("=" * 80)
        print("安全数据更新")
        print("=" * 80)

        # 1. 检查GUI进程
        print("\n[1] 检查GUI进程...")
        gui_procs = self.find_gui_processes()

        if gui_procs:
            print(f"发现 {len(gui_procs)} 个GUI进程正在运行:")
            for proc in gui_procs:
                print(f"  PID {proc['pid']}: {proc['cmdline'][:80]}")

            print("\n建议操作:")
            print("  1. 关闭GUI窗口")
            print("  2. 或者等待此工具自动检测锁释放")

            response = input("\n是否继续？(y/n): ").strip().lower()
            if response != 'y':
                print("已取消更新")
                return None
        else:
            print("[OK] 未发现GUI进程")

        # 2. 检查数据库锁
        print("\n[2] 检查数据库锁...")
        if self.check_database_lock():
            print("数据库已被锁定")
            if not self.wait_for_lock_release(timeout=60):
                print("\n无法获取数据库访问权限")
                print("请手动关闭所有GUI程序后重试")
                return None
        else:
            print("[OK] 数据库未被锁定")

        # 3. 执行更新
        print("\n[3] 执行更新...")
        try:
            result = update_func(*args, **kwargs)
            print("\n[OK] 更新成功")
            return result
        except Exception as e:
            print(f"\n[ERROR] 更新失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def fill_adjustment_batch():
    """批量填充复权数据（用于安全更新）"""

    manager = get_db_manager()

    # 检查当前状态
    print("检查当前状态...")
    stats = manager.execute_read_query("""
        SELECT
            COUNT(DISTINCT stock_code) as stock_count,
            COUNT(*) as total_rows,
            COUNT(open_front) as has_front_data
        FROM stock_daily
        WHERE adjust_type = 'none'
    """)

    print(f"股票数量: {stats['stock_count'].iloc[0]:,}")
    print(f"总记录数: {stats['total_rows'].iloc[0]:,}")
    print(f"已有复权数据: {stats['has_front_data'].iloc[0]:,}")

    if stats['has_front_data'].iloc[0] > 0:
        print("\n已有部分复权数据，跳过更新")
        return {'success': True, 'message': '已有数据，跳过'}

    # 批量更新
    print("\n开始批量更新...")
    import time
    start_time = time.time()

    with manager.get_write_connection() as con:
        result = con.execute("""
            UPDATE stock_daily
            SET
                open_front = open,
                high_front = high,
                low_front = low,
                close_front = close,
                open_back = open,
                high_back = high,
                low_back = low,
                close_back = close,
                open_geometric_front = open,
                high_geometric_front = high,
                low_geometric_front = low,
                close_geometric_front = close,
                open_geometric_back = open,
                high_geometric_back = high,
                low_geometric_back = low,
                close_geometric_back = close
            WHERE adjust_type = 'none'
              AND open_front IS NULL
        """)

        affected_rows = result.rowcount
        elapsed = time.time() - start_time

        print(f"\n[OK] 更新完成！")
        print(f"更新记录数: {affected_rows:,}")
        print(f"耗时: {elapsed:.1f} 秒")

    return {'success': True, 'affected_rows': affected_rows}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='安全数据更新工具')
    parser.add_argument('--fill-adjustment', action='store_true', help='填充复权数据')
    parser.add_argument('--test-lock', action='store_true', help='测试数据库锁检测')

    args = parser.parse_args()

    updater = SafeDataUpdater()

    if args.test_lock:
        print("=" * 80)
        print("数据库锁检测测试")
        print("=" * 80)

        gui_procs = updater.find_gui_processes()
        print(f"\n发现GUI进程: {len(gui_procs)}")

        is_locked = updater.check_database_lock()
        print(f"数据库锁定状态: {'已锁定' if is_locked else '未锁定'}")

    elif args.fill_adjustment:
        updater.safe_update(fill_adjustment_batch)

    else:
        print("使用方法:")
        print("  测试数据库锁: python safe_data_updater.py --test-lock")
        print("  填充复权数据: python safe_data_updater.py --fill-adjustment")
