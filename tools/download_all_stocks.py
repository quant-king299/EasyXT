#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全部A股日线数据下载工具
同时下载深圳和上海A股日线数据
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import time

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from xtquant import xtdata
    print("✓ 成功导入xtquant模块")
except ImportError as e:
    print(f"✗ 导入xtquant模块失败: {e}")
    sys.exit(1)

def get_all_stock_list():
    """
    获取全部A股股票列表（包括深圳和上海）
    
    Returns:
        list: 全部A股股票代码列表
    """
    print("正在获取全部A股股票列表...")
    
    try:
        # 下载板块数据
        xtdata.download_sector_data()
        
        # 获取沪深A股
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        
        if not all_stocks:
            print("未获取到沪深A股列表，尝试分别获取...")
            # 分别获取深圳和上海股票
            sz_stocks = xtdata.get_stock_list_in_sector('深证A股')
            sh_stocks = xtdata.get_stock_list_in_sector('上证A股')
            all_stocks = sz_stocks + sh_stocks
        
        print(f"✓ 获取到 {len(all_stocks)} 只A股股票")
        
        # 过滤掉非标准格式的股票代码
        valid_stocks = []
        for stock in all_stocks:
            # 检查是否为标准A股代码格式
            if (stock.endswith('.SZ') and len(stock.split('.')[0]) == 6 and 
                stock.startswith(('000', '002', '300', '301'))) or \
               (stock.endswith('.SH') and len(stock.split('.')[0]) == 6 and 
                stock.startswith(('600', '601', '603', '605', '688'))):
                valid_stocks.append(stock)
        
        print(f"✓ 有效A股股票数量: {len(valid_stocks)}")
        return valid_stocks
        
    except Exception as e:
        print(f"✗ 获取A股股票列表失败: {e}")
        return []

def download_stock_data(stock_code, start_date="", end_date="", force_download=False):
    """
    下载股票日线数据
    
    Args:
        stock_code (str): 股票代码，如 '000001.SZ' 或 '600000.SH'
        start_date (str): 开始日期，格式'YYYYMMDD'
        end_date (str): 结束日期，格式'YYYYMMDD'
        force_download (bool): 是否强制下载
            
    Returns:
        bool: 下载是否成功
    """
    try:
        print(f"  下载股票 {stock_code} 的日线数据...")
        
        # 如果没有指定日期范围，使用默认范围（最近5年）
        if not start_date:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y%m%d')
        elif not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        # 下载历史数据
        xtdata.download_history_data(
            stock_code=stock_code,
            period='1d',
            start_time=start_date,
            end_time=end_date,
            incrementally=not force_download  # 如果强制下载，则不使用增量下载
        )
        
        print(f"  ✓ 股票 {stock_code} 日线数据下载完成")
        return True
        
    except Exception as e:
        print(f"  ✗ 下载股票 {stock_code} 数据失败: {e}")
        return False

def download_all_stocks(data_dir=None, force_download=False, stocks=None, start_date="", end_date=""):
    """
    下载全部A股日线数据
    
    Args:
        data_dir (str): 数据目录路径（仅用于显示，实际由xtdata管理）
        force_download (bool): 是否强制下载
        stocks (list): 指定股票列表
        start_date (str): 开始日期
        end_date (str): 结束日期
    """
    print("=" * 60)
    print("全部A股日线数据下载工具")
    print("=" * 60)
    
    if data_dir:
        print(f"数据目录: {data_dir}")
    
    print(f"强制下载: {'是' if force_download else '否'}")
    if start_date:
        print(f"开始日期: {start_date}")
    if end_date:
        print(f"结束日期: {end_date}")
    print()
    
    # 获取股票列表
    if stocks:
        stock_list = stocks
        print(f"下载指定 {len(stock_list)} 只股票")
    else:
        stock_list = get_all_stock_list()
        if not stock_list:
            print("✗ 未获取到股票列表")
            return
    
    total_count = len(stock_list)
    success_count = 0
    failed_count = 0
    
    print(f"\n开始下载 {total_count} 只股票的日线数据...")
    print("-" * 60)
    
    # 下载每只股票
    for i, stock_code in enumerate(stock_list, 1):
        try:
            print(f"[{i:4d}/{total_count:4d}] {stock_code}")
            
            # 下载数据
            if download_stock_data(stock_code, start_date, end_date, force_download):
                success_count += 1
            else:
                failed_count += 1
            
            # 添加小延迟避免请求过于频繁
            if i < total_count:
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n\n程序被用户中断")
            break
        except Exception as e:
            print(f"  ✗ 处理股票 {stock_code} 时出错: {e}")
            failed_count += 1
    
    # 输出统计结果
    print("-" * 60)
    print("下载完成统计:")
    print(f"  总股票数: {total_count:4d}")
    print(f"  成功下载: {success_count:4d}")
    print(f"  下载失败: {failed_count:4d}")
    print(f"  成功率:   {success_count/total_count*100:.1f}%" if total_count > 0 else "  成功率:   0.0%")
    print("=" * 60)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='全部A股日线数据下载工具')
    parser.add_argument('--data-dir', help='数据目录路径（仅供参考）')
    parser.add_argument('--force', action='store_true', help='强制重新下载所有数据')
    parser.add_argument('--stocks', help='指定股票代码，多个用逗号分隔')
    parser.add_argument('--start-date', help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end-date', help='结束日期 (YYYYMMDD)')
    parser.add_argument('--demo', action='store_true', help='演示模式（只下载几只股票）')
    
    args = parser.parse_args()
    
    # 处理股票列表参数
    stock_list = None
    if args.stocks:
        stock_list = [code.strip() for code in args.stocks.split(',') if code.strip()]
        # 标准化股票代码
        normalized_stocks = []
        for stock in stock_list:
            if '.' not in stock and len(stock) == 6:
                # 自动添加交易所后缀
                if stock.startswith(('000', '002', '300', '301')):
                    normalized_stocks.append(f"{stock}.SZ")
                elif stock.startswith(('600', '601', '603', '605', '688')):
                    normalized_stocks.append(f"{stock}.SH")
                else:
                    normalized_stocks.append(stock)
            else:
                normalized_stocks.append(stock)
        stock_list = normalized_stocks
    
    # 演示模式
    if args.demo:
        if not stock_list:
            stock_list = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']  # 平安银行、万科A、浦发银行、招商银行
        print("📢 演示模式：只下载以下股票")
        for stock in stock_list:
            print(f"   • {stock}")
        print()
    
    # 执行下载
    download_all_stocks(
        data_dir=args.data_dir,
        force_download=args.force,
        stocks=stock_list,
        start_date=args.start_date,
        end_date=args.end_date
    )

if __name__ == "__main__":
    main()