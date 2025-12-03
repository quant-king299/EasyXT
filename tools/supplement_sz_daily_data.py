#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
补充深圳股票日线数据工具
专门为补充 D:\国金QMT交易端模拟\userdata_mini\datadir\SZ\86400 目录下的深圳股票日线数据而设计
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import time

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from xtquant import xtdata
    logging.info("成功导入xtquant模块")
except ImportError as e:
    logging.error(f"导入xtquant模块失败: {e}")
    print(f"导入xtquant模块失败: {e}")
    sys.exit(1)

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('supplement_sz_data.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def get_sz_stock_list():
    """
    获取深圳股票列表
    
    Returns:
        list: 深圳股票代码列表
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("正在获取深圳股票列表...")
        
        # 下载板块数据
        xtdata.download_sector_data()
        
        # 获取深圳A股
        sz_stocks = xtdata.get_stock_list_in_sector('深证A股')
        
        if not sz_stocks:
            logger.warning("未获取到深圳A股列表，尝试获取全部股票...")
            # 如果获取不到，尝试其他方式
            all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
            # 筛选出深圳股票（以000、002、300、301开头的股票）
            sz_stocks = [stock for stock in all_stocks if stock.startswith(('000', '002', '300', '301')) and stock.endswith('.SZ')]
        
        logger.info(f"获取到 {len(sz_stocks)} 只深圳股票")
        
        # 过滤掉非标准格式的股票代码
        valid_stocks = []
        for stock in sz_stocks:
            if stock.endswith('.SZ') and len(stock.split('.')[0]) == 6:
                valid_stocks.append(stock)
        
        logger.info(f"有效深圳股票数量: {len(valid_stocks)}")
        return valid_stocks
        
    except Exception as e:
        logger.error(f"获取深圳股票列表失败: {e}")
        return []

def check_data_file_exists(stock_code, data_dir):
    """
    检查股票数据文件是否已存在
    
    Args:
        stock_code (str): 股票代码，如 '000001.SZ'
        data_dir (str): 数据目录路径
        
    Returns:
        bool: True表示数据文件已存在，False表示需要下载
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 构造数据文件路径
        stock_prefix = stock_code.split('.')[0]  # 获取股票代码前缀，如'000001'
        dat_file = f"{stock_prefix}.DAT"
        file_path = os.path.join(data_dir, dat_file)
        
        # 检查文件是否存在且不为空
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            if file_size > 0:
                logger.debug(f"股票 {stock_code} 数据文件已存在: {file_path}")
                return True
            else:
                logger.warning(f"股票 {stock_code} 数据文件为空: {file_path}")
                return False
        else:
            logger.debug(f"股票 {stock_code} 数据文件不存在: {file_path}")
            return False
            
    except Exception as e:
        logger.error(f"检查股票 {stock_code} 数据文件存在性失败: {e}")
        return False

def download_stock_data(stock_code, start_date="", end_date="", force_download=False):
    """
    下载股票日线数据
    
    Args:
        stock_code (str): 股票代码，如 '000001.SZ'
        start_date (str): 开始日期，格式'YYYYMMDD'
        end_date (str): 结束日期，格式'YYYYMMDD'
        force_download (bool): 是否强制下载
            
    Returns:
        bool: 下载是否成功
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"开始下载股票 {stock_code} 的日线数据...")
        
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
        
        logger.info(f"股票 {stock_code} 日线数据下载完成")
        return True
        
    except Exception as e:
        logger.error(f"下载股票 {stock_code} 数据失败: {e}")
        return False

def supplement_sz_daily_data(data_dir="D:/国金QMT交易端模拟/userdata_mini/datadir/SZ/86400", 
                           force_download=False, 
                           stock_list=None,
                           start_date="",
                           end_date=""):
    """
    补充深圳股票日线数据
    
    Args:
        data_dir (str): 深圳股票日线数据目录
        force_download (bool): 是否强制下载已存在的数据
        stock_list (list): 指定股票代码列表，如果为None则获取所有深圳股票
        start_date (str): 开始日期，格式'YYYYMMDD'
        end_date (str): 结束日期，格式'YYYYMMDD'
        
    Returns:
        dict: 下载结果统计
    """
    logger = setup_logging()
    
    try:
        # 验证数据目录
        if not os.path.exists(data_dir):
            logger.info(f"创建数据目录: {data_dir}")
            os.makedirs(data_dir, exist_ok=True)
        
        logger.info(f"开始补充深圳股票日线数据到目录: {data_dir}")
        
        # 获取股票列表
        if stock_list is None:
            stock_list = get_sz_stock_list()
        
        if not stock_list:
            logger.error("未获取到股票列表")
            return {"total": 0, "downloaded": 0, "skipped": 0, "failed": 0}
        
        # 统计变量
        total_count = len(stock_list)
        downloaded_count = 0
        skipped_count = 0
        failed_count = 0
        
        logger.info(f"开始处理 {total_count} 只股票...")
        
        # 处理每只股票
        for i, stock_code in enumerate(stock_list, 1):
            try:
                logger.info(f"[{i}/{total_count}] 处理股票 {stock_code}")
                
                # 检查数据是否已存在
                if not force_download and check_data_file_exists(stock_code, data_dir):
                    logger.info(f"股票 {stock_code} 数据已存在，跳过下载")
                    skipped_count += 1
                    continue
                
                # 下载数据
                if download_stock_data(stock_code, start_date, end_date, force_download):
                    logger.info(f"股票 {stock_code} 数据下载成功")
                    downloaded_count += 1
                else:
                    logger.error(f"股票 {stock_code} 数据下载失败")
                    failed_count += 1
                
                # 添加延迟避免请求过于频繁
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"处理股票 {stock_code} 时出错: {e}")
                failed_count += 1
        
        # 输出统计结果
        result = {
            "total": total_count,
            "downloaded": downloaded_count,
            "skipped": skipped_count,
            "failed": failed_count
        }
        
        logger.info("=" * 60)
        logger.info("深圳股票日线数据补充完成:")
        logger.info(f"  总股票数: {total_count}")
        logger.info(f"  成功下载: {downloaded_count}")
        logger.info(f"  跳过下载: {skipped_count}")
        logger.info(f"  下载失败: {failed_count}")
        logger.info("=" * 60)
        
        return result
        
    except Exception as e:
        logger.error(f"补充深圳股票日线数据失败: {e}")
        return {"total": 0, "downloaded": 0, "skipped": 0, "failed": 0}

def main():
    """主函数"""
    print("深圳股票日线数据补充工具")
    print("=" * 50)
    print("功能: 补充 D:\\国金QMT交易端模拟\\userdata_mini\\datadir\\SZ\\86400 目录下的深圳股票日线数据")
    print()
    
    try:
        # 获取用户输入
        print("请选择操作模式:")
        print("1. 补充所有深圳股票日线数据（跳过已存在的）")
        print("2. 强制重新下载所有深圳股票日线数据")
        print("3. 补充指定股票的日线数据")
        print("4. 补充指定日期范围的数据")
        
        choice = input("请输入选项 (1-4): ").strip()
        
        if choice == "1":
            # 补充所有深圳股票（跳过已存在的）
            print("开始补充所有深圳股票日线数据...")
            result = supplement_sz_daily_data(force_download=False)
            print(f"补充完成: 成功 {result['downloaded']}, 跳过 {result['skipped']}, 失败 {result['failed']}")
            
        elif choice == "2":
            # 强制重新下载所有深圳股票
            confirm = input("确定要强制重新下载所有数据吗？这会重新下载所有股票数据 (y/N): ").strip().lower()
            if confirm == 'y':
                print("开始强制重新下载所有深圳股票日线数据...")
                result = supplement_sz_daily_data(force_download=True)
                print(f"补充完成: 成功 {result['downloaded']}, 跳过 {result['skipped']}, 失败 {result['failed']}")
            else:
                print("操作已取消")
                
        elif choice == "3":
            # 补充指定股票
            stock_input = input("请输入股票代码（多个股票用逗号分隔）: ").strip()
            if stock_input:
                stock_list = [code.strip() for code in stock_input.split(',') if code.strip()]
                # 标准化股票代码格式
                normalized_stocks = []
                for stock in stock_list:
                    if '.' not in stock:
                        # 自动添加交易所后缀（深圳股票）
                        if stock.startswith(('000', '002', '300', '301')) and len(stock) == 6:
                            normalized_stocks.append(f"{stock}.SZ")
                        else:
                            print(f"警告: 股票代码 {stock} 格式可能不正确")
                            normalized_stocks.append(stock)
                    else:
                        normalized_stocks.append(stock)
                
                print(f"开始补充指定股票: {normalized_stocks}")
                result = supplement_sz_daily_data(stock_list=normalized_stocks)
                print(f"补充完成: 成功 {result['downloaded']}, 跳过 {result['skipped']}, 失败 {result['failed']}")
            else:
                print("未输入股票代码")
                
        elif choice == "4":
            # 补充指定日期范围的数据
            start_date = input("请输入开始日期 (YYYYMMDD，回车使用默认): ").strip()
            end_date = input("请输入结束日期 (YYYYMMDD，回车使用默认): ").strip()
            
            print(f"开始补充指定日期范围的数据...")
            print(f"开始日期: {start_date if start_date else '默认'}")
            print(f"结束日期: {end_date if end_date else '默认'}")
            
            result = supplement_sz_daily_data(start_date=start_date, end_date=end_date)
            print(f"补充完成: 成功 {result['downloaded']}, 跳过 {result['skipped']}, 失败 {result['failed']}")
            
        else:
            print("无效选项")
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()