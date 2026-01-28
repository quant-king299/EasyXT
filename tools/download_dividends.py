#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载分红数据工具
支持从QMT下载分红数据并保存到本地数据库
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# 添加路径
project_root = Path(__file__).parents[1]
factor_platform_path = project_root / "101因子" / "101因子分析平台" / "src"
sys.path.insert(0, str(factor_platform_path))

from data_manager.local_data_manager_with_adjustment import LocalDataManager


def download_dividends_from_qmt(stock_code: str, years: int = 3):
    """
    从QMT下载分红数据

    Args:
        stock_code: 股票代码
        years: 下载最近几年的分红数据
    """
    try:
        import easy_xt
        api = easy_xt.get_api()

        # 初始化数据服务
        try:
            api.init_data()
        except:
            pass

        print(f"📥 下载 {stock_code} 分红数据...")

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)

        # QMT分红数据API
        # 注意：这里需要根据实际的QMT API调整
        # 通常分红数据在不同的接口

        # 方式1：尝试获取分红数据
        try:
            # 获取财务数据（包含分红）
            # 这部分需要根据实际API调整
            dividends = api.get_financial_data(
                stock_code,
                start_time=start_date.strftime('%Y%m%d'),
                end_time=end_date.strftime('%Y%m%d'),
                # 添加分红相关参数
            )

            if dividends is not None and not dividends.empty:
                # 提取分红信息
                df = _extract_dividends(dividends, stock_code)
                return df
        except Exception as e:
            print(f"  [WARNING] 方式1失败: {e}")

        # 方式2：从财经接口获取（备用）
        print(f"  [INFO] 尝试使用备用数据源...")

        # 这里可以集成其他数据源，如akshare
        try:
            import akshare as ak

            # akshare 分红数据
            df = ak.stock_dividents(symbol=stock_code[:6])

            if not df.empty:
                # 格式化数据
                df = _format_akshare_dividends(df)
                return df

        except ImportError:
            print("  [X] akshare 未安装")

        except Exception as e:
            print(f"  [X] 备用数据源失败: {e}")

        return pd.DataFrame()

    except ImportError:
        print("[X] easy_xt 未安装")
        return pd.DataFrame()

    except Exception as e:
        print(f"[X] 下载失败: {e}")
        return pd.DataFrame()


def _extract_dividends(data, stock_code: str) -> pd.DataFrame:
    """从QMT数据中提取分红信息"""
    # 这里需要根据实际返回的数据结构来提取
    # 这是一个示例实现

    if isinstance(data, pd.DataFrame):
        # 假设返回的是DataFrame
        # 过滤分红相关的数据
        if 'dividend' in data.columns:
            df = data[data['dividend'] > 0].copy()

            if not df.empty:
                # 格式化
                df_result = pd.DataFrame({
                    'ex_date': df.index.strftime('%Y-%m-%d'),
                    'dividend_per_share': df['dividend'],
                    'record_date': df.get('record_date', ''),
                    'payout_date': df.get('payout_date', '')
                })
                return df_result

    return pd.DataFrame()


def _format_akshare_dividends(df: pd.DataFrame) -> pd.DataFrame:
    """格式化akshare的分红数据"""
    # akshare返回的列名可能需要调整
    # 常见列名：['股票代码', '除权除息日', '每10股派息(元)', ...]

    if '除权除息日' in df.columns:
        df_result = pd.DataFrame({
            'ex_date': pd.to_datetime(df['除权除息日']).dt.strftime('%Y-%m-%d'),
            'dividend_per_share': df['每10股派息(元)'] / 10.0,  # 转换为每股
            'record_date': df.get('股权登记日', ''),
            'payout_date': df.get('除权除息日', '')
        })
        return df_result

    # 如果列名不匹配，尝试通用列名
    return df


def save_dividends_batch(stock_list: list, years: int = 3):
    """批量下载分红数据"""
    print("=" * 60)
    print(f"批量下载分红数据")
    print(f"股票数量: {len(stock_list)}")
    print(f"年份范围: 最近{years}年")
    print("=" * 60)
    print()

    manager = LocalDataManager()

    success_count = 0
    failed_count = 0
    total_dividends = 0

    for i, stock_code in enumerate(stock_list, 1):
        try:
            print(f"[{i}/{len(stock_list)}] {stock_code}")

            # 下载分红数据
            df = download_dividends_from_qmt(stock_code, years)

            if not df.empty:
                # 保存到数据库
                manager.save_dividends(stock_code, df)
                success_count += 1
                total_dividends += len(df)
            else:
                print(f"  [WARNING] 无分红数据")
                failed_count += 1

        except Exception as e:
            print(f"  [X] 失败: {e}")
            failed_count += 1

        print()

    manager.close()

    print("=" * 60)
    print("下载完成统计:")
    print(f"  总股票数: {len(stock_list)}")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    print(f"  总分红记录: {total_dividends}")
    print("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='下载分红数据')
    parser.add_argument('--stocks', help='股票代码，多个用逗号分隔')
    parser.add_argument('--years', type=int, default=3, help='下载最近几年的数据（默认3年）')
    parser.add_argument('--demo', action='store_true', help='演示模式（下载几只股票）')

    args = parser.parse_args()

    # 演示模式
    if args.demo or not args.stocks:
        print("[INFO] 演示模式：下载常用ETF的分红数据")
        stock_list = [
            '511380.SH',  # 可转债ETF
            '512100.SH',  # 中证1000ETF
            '510300.SH',  # 沪深300ETF
            '510500.SH',  # 中证500ETF
            '159915.SZ'   # 深证ETF
        ]
    else:
        # 解析股票列表
        stock_list = [s.strip() for s in args.stocks.split(',') if s.strip()]

    save_dividends_batch(stock_list, args.years)


if __name__ == '__main__':
    main()
