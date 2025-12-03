#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量下载补充深圳股票日线数据工具
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
    from easy_xt import get_api
    logging.info("成功导入xtquant和easy_xt模块")
except ImportError as e:
    logging.error(f"导入模块失败: {e}")
    print(f"导入模块失败: {e}")
    sys.exit(1)

class SZStockDataDownloader:
    """深圳股票数据下载器"""
    
    def __init__(self, data_dir="D:/国金QMT交易端模拟/userdata_mini/datadir"):
        self.data_dir = data_dir
        self.sz_data_dir = os.path.join(data_dir, "SZ", "86400")
        self.api = None
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('sz_stock_download.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_sz_stock_list(self):
        """
        获取深圳股票列表
        
        Returns:
            list: 深圳股票代码列表
        """
        try:
            self.logger.info("正在获取深圳股票列表...")
            
            # 下载板块数据
            xtdata.download_sector_data()
            
            # 获取深圳A股
            sz_stocks = xtdata.get_stock_list_in_sector('深证A股')
            
            if not sz_stocks:
                self.logger.warning("未获取到深圳A股列表，尝试获取全部股票...")
                # 如果获取不到，尝试其他方式
                all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
                # 筛选出深圳股票（以000、002、300、301开头的股票）
                sz_stocks = [stock for stock in all_stocks if stock.startswith(('000', '002', '300', '301')) and stock.endswith('.SZ')]
            
            self.logger.info(f"获取到 {len(sz_stocks)} 只深圳股票")
            
            # 过滤掉非标准格式的股票代码
            valid_stocks = []
            for stock in sz_stocks:
                if stock.endswith('.SZ') and len(stock.split('.')[0]) == 6:
                    valid_stocks.append(stock)
            
            self.logger.info(f"有效深圳股票数量: {len(valid_stocks)}")
            return valid_stocks
            
        except Exception as e:
            self.logger.error(f"获取深圳股票列表失败: {e}")
            return []
    
    def check_existing_data(self, stock_code):
        """
        检查股票数据是否已存在
        
        Args:
            stock_code (str): 股票代码，如 '000001.SZ'
            
        Returns:
            bool: True表示数据已存在，False表示需要下载
        """
        try:
            # 构造数据文件路径
            stock_prefix = stock_code.split('.')[0]  # 获取股票代码前缀，如'000001'
            dat_file = f"{stock_prefix}.DAT"
            file_path = os.path.join(self.sz_data_dir, dat_file)
            
            # 检查文件是否存在
            if os.path.exists(file_path):
                # 检查文件大小
                file_size = os.path.getsize(file_path)
                if file_size > 0:
                    self.logger.debug(f"股票 {stock_code} 数据已存在: {file_path}")
                    return True
                else:
                    self.logger.warning(f"股票 {stock_code} 数据文件为空: {file_path}")
                    return False
            else:
                self.logger.debug(f"股票 {stock_code} 数据不存在: {file_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"检查股票 {stock_code} 数据存在性失败: {e}")
            return False
    
    def download_single_stock(self, stock_code, force_download=False):
        """
        下载单只股票的日线数据
        
        Args:
            stock_code (str): 股票代码，如 '000001.SZ'
            force_download (bool): 是否强制下载
            
        Returns:
            bool: 下载是否成功
        """
        try:
            # 检查数据是否已存在
            if not force_download and self.check_existing_data(stock_code):
                self.logger.info(f"股票 {stock_code} 数据已存在，跳过下载")
                return True
            
            self.logger.info(f"开始下载股票 {stock_code} 的日线数据...")
            
            # 计算时间范围（最近5年）
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y%m%d')
            
            # 下载历史数据
            xtdata.download_history_data(
                stock_code=stock_code,
                period='1d',
                start_time=start_date,
                end_time=end_date,
                incrementally=True
            )
            
            self.logger.info(f"股票 {stock_code} 日线数据下载完成")
            
            # 验证下载结果
            if self.check_existing_data(stock_code):
                self.logger.info(f"股票 {stock_code} 数据验证通过")
                return True
            else:
                self.logger.warning(f"股票 {stock_code} 数据下载后仍无法验证")
                return False
                
        except Exception as e:
            self.logger.error(f"下载股票 {stock_code} 数据失败: {e}")
            return False
    
    def download_batch_stocks(self, stock_list=None, force_download=False, max_workers=10):
        """
        批量下载股票数据
        
        Args:
            stock_list (list): 股票代码列表，如果为None则获取所有深圳股票
            force_download (bool): 是否强制下载已存在的数据
            max_workers (int): 最大并发下载数
            
        Returns:
            dict: 下载结果统计
        """
        try:
            # 获取股票列表
            if stock_list is None:
                stock_list = self.get_sz_stock_list()
            
            if not stock_list:
                self.logger.error("未获取到股票列表")
                return {"total": 0, "success": 0, "failed": 0, "skipped": 0}
            
            self.logger.info(f"开始批量下载 {len(stock_list)} 只股票的日线数据...")
            
            # 统计变量
            total_count = len(stock_list)
            success_count = 0
            failed_count = 0
            skipped_count = 0
            
            # 按批次下载（避免同时下载太多）
            batch_size = max_workers
            for i in range(0, len(stock_list), batch_size):
                batch = stock_list[i:i+batch_size]
                self.logger.info(f"处理批次 {i//batch_size + 1}/{(len(stock_list)-1)//batch_size + 1}，包含 {len(batch)} 只股票")
                
                # 下载当前批次
                for j, stock_code in enumerate(batch):
                    try:
                        self.logger.info(f"[{i+j+1}/{total_count}] 处理股票 {stock_code}")
                        
                        if self.download_single_stock(stock_code, force_download):
                            success_count += 1
                        else:
                            failed_count += 1
                            
                        # 添加延迟避免请求过于频繁
                        time.sleep(0.1)
                        
                    except Exception as e:
                        self.logger.error(f"处理股票 {stock_code} 时出错: {e}")
                        failed_count += 1
                
                # 批次间稍长延迟
                if i + batch_size < len(stock_list):
                    time.sleep(1)
            
            # 输出统计结果
            result = {
                "total": total_count,
                "success": success_count,
                "failed": failed_count,
                "skipped": skipped_count
            }
            
            self.logger.info("=" * 50)
            self.logger.info("批量下载完成统计:")
            self.logger.info(f"  总股票数: {total_count}")
            self.logger.info(f"  成功下载: {success_count}")
            self.logger.info(f"  下载失败: {failed_count}")
            self.logger.info(f"  跳过下载: {skipped_count}")
            self.logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            self.logger.error(f"批量下载股票数据失败: {e}")
            return {"total": 0, "success": 0, "failed": 0, "skipped": 0}
    
    def verify_data_directory(self):
        """
        验证数据目录是否存在，如果不存在则创建
        
        Returns:
            bool: 目录是否可用
        """
        try:
            # 检查根目录是否存在
            if not os.path.exists(self.data_dir):
                self.logger.error(f"数据根目录不存在: {self.data_dir}")
                return False
            
            # 检查深圳数据目录
            if not os.path.exists(self.sz_data_dir):
                self.logger.info(f"创建深圳股票数据目录: {self.sz_data_dir}")
                os.makedirs(self.sz_data_dir, exist_ok=True)
            
            self.logger.info(f"数据目录验证通过: {self.sz_data_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"验证数据目录失败: {e}")
            return False
    
    def get_download_statistics(self):
        """
        获取已下载数据的统计信息
        
        Returns:
            dict: 统计信息
        """
        try:
            if not os.path.exists(self.sz_data_dir):
                return {"total_files": 0, "total_size_mb": 0}
            
            files = os.listdir(self.sz_data_dir)
            dat_files = [f for f in files if f.upper().endswith('.DAT')]
            
            total_files = len(dat_files)
            total_size = 0
            
            for file in dat_files:
                file_path = os.path.join(self.sz_data_dir, file)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
            
            total_size_mb = round(total_size / (1024 * 1024), 2)
            
            return {
                "total_files": total_files,
                "total_size_mb": total_size_mb
            }
            
        except Exception as e:
            self.logger.error(f"获取下载统计信息失败: {e}")
            return {"total_files": 0, "total_size_mb": 0}

def main():
    """主函数"""
    print("深圳股票日线数据批量下载工具")
    print("=" * 50)
    
    # 创建下载器实例
    downloader = SZStockDataDownloader()
    
    # 验证数据目录
    if not downloader.verify_data_directory():
        print("数据目录验证失败，程序退出")
        return
    
    # 显示当前统计信息
    stats = downloader.get_download_statistics()
    print(f"当前已下载数据统计:")
    print(f"  数据文件数量: {stats['total_files']}")
    print(f"  数据总大小: {stats['total_size_mb']} MB")
    print()
    
    # 获取用户选择
    print("请选择操作:")
    print("1. 下载所有深圳股票日线数据")
    print("2. 强制重新下载所有深圳股票日线数据")
    print("3. 下载指定股票列表的日线数据")
    print("4. 查看当前下载统计")
    
    try:
        choice = input("请输入选项 (1-4): ").strip()
        
        if choice == "1":
            # 下载所有深圳股票
            print("开始下载所有深圳股票日线数据...")
            result = downloader.download_batch_stocks(force_download=False)
            print(f"下载完成: 成功 {result['success']}, 失败 {result['failed']}")
            
        elif choice == "2":
            # 强制重新下载所有深圳股票
            confirm = input("确定要强制重新下载所有数据吗？这可能会覆盖现有数据 (y/N): ").strip().lower()
            if confirm == 'y':
                print("开始强制重新下载所有深圳股票日线数据...")
                result = downloader.download_batch_stocks(force_download=True)
                print(f"下载完成: 成功 {result['success']}, 失败 {result['failed']}")
            else:
                print("操作已取消")
                
        elif choice == "3":
            # 下载指定股票
            stock_input = input("请输入股票代码（多个股票用逗号分隔）: ").strip()
            if stock_input:
                stock_list = [code.strip() for code in stock_input.split(',') if code.strip()]
                # 标准化股票代码格式
                normalized_stocks = []
                for stock in stock_list:
                    if '.' not in stock:
                        # 自动添加交易所后缀
                        if stock.startswith(('000', '002', '300', '301')):
                            normalized_stocks.append(f"{stock}.SZ")
                        else:
                            normalized_stocks.append(stock)
                    else:
                        normalized_stocks.append(stock)
                
                print(f"开始下载指定股票: {normalized_stocks}")
                result = downloader.download_batch_stocks(stock_list=normalized_stocks)
                print(f"下载完成: 成功 {result['success']}, 失败 {result['failed']}")
            else:
                print("未输入股票代码")
                
        elif choice == "4":
            # 显示统计信息
            stats = downloader.get_download_statistics()
            print(f"当前下载统计:")
            print(f"  数据文件数量: {stats['total_files']}")
            print(f"  数据总大小: {stats['total_size_mb']} MB")
            
        else:
            print("无效选项")
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()