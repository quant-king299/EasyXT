# DuckDB数据管理器增强模块
# 添加读取市值数据（PE、PB、市值、换手率）的功能

from pathlib import Path
import sys
import pandas as pd
import duckdb
from typing import List, Optional, Dict

# 添加项目路径
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

from src.data_manager.duckdb_data_manager import DuckDBDataManager


class DuckDBDataManagerEnhanced(DuckDBDataManager):
    """增强的DuckDB数据管理器，支持市值数据读取"""

    def load_market_cap_data(self,
                            stock_codes: List[str] = None,
                            start_date: str = None,
                            end_date: str = None) -> pd.DataFrame:
        """
        从stock_market_cap表加载市值数据（PE、PB、市值、换手率）

        Args:
            stock_codes: 股票代码列表（None表示全部）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            包含PE、PB、市值等字段的DataFrame
        """
        try:
            # 检查表是否存在
            check_table = self.storage.conn.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name = 'stock_market_cap'
            """).fetchdf()

            if check_table.empty:
                print("[WARN] stock_market_cap表不存在，请先在GUI中下载市值数据")
                print("       提示：运行GUI -> 📥 Tushare下载 -> 市值数据下载")
                return pd.DataFrame()

            # 构建查询
            query = "SELECT * FROM stock_market_cap WHERE 1=1"
            params = []

            if stock_codes:
                codes_str = ", ".join([f"'{code}'" for code in stock_codes])
                query += f" AND stock_code IN ({codes_str})"

            if start_date:
                query += f" AND date >= '{start_date}'"

            if end_date:
                query += f" AND date <= '{end_date}'"

            query += " ORDER BY date, stock_code"

            # 执行查询
            df = self.storage.conn.execute(query).fetchdf()

            if not df.empty:
                print(f"[OK] 从stock_market_cap加载了 {len(df)} 条记录")
                print(f"     日期范围: {df['date'].min()} - {df['date'].max()}")
                print(f"     股票数量: {df['stock_code'].nunique()}")

                # 显示可用字段
                print(f"     可用字段: {', '.join(df.columns.tolist())}")
            else:
                print("[WARN] 查询结果为空")

            return df

        except Exception as e:
            print(f"[ERROR] 加载市值数据失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def get_market_cap_fields(self) -> List[str]:
        """
        获取stock_market_cap表的字段列表

        Returns:
            字段名列表
        """
        try:
            df = self.storage.conn.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'stock_market_cap'
                ORDER BY ordinal_position
            """).fetchdf()

            if not df.empty:
                return df['column_name'].tolist()
            else:
                return []

        except Exception as e:
            print(f"[ERROR] 获取字段列表失败: {e}")
            return []

    def get_market_cap_statistics(self) -> Dict:
        """
        获取市值数据的统计信息

        Returns:
            统计信息字典
        """
        try:
            # 检查表是否存在
            check_table = self.storage.conn.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name = 'stock_market_cap'
            """).fetchdf()

            if check_table.empty:
                return {
                    'exists': False,
                    'message': 'stock_market_cap表不存在，请先在GUI中下载数据'
                }

            # 获取统计信息
            stats = {}

            # 总记录数
            count = self.storage.conn.execute("SELECT COUNT(*) FROM stock_market_cap").fetchone()[0]
            stats['total_records'] = count

            # 日期范围
            date_range = self.storage.conn.execute(
                "SELECT MIN(date), MAX(date) FROM stock_market_cap"
            ).fetchone()
            stats['date_range'] = f"{date_range[0]} - {date_range[1]}"

            # 股票数量
            stock_count = self.storage.conn.execute(
                "SELECT COUNT(DISTINCT stock_code) FROM stock_market_cap"
            ).fetchone()[0]
            stats['stock_count'] = stock_count

            # 字段列表
            fields = self.get_market_cap_fields()
            stats['fields'] = fields

            # 各字段的数据完整性
            stats['field_completeness'] = {}
            for field in ['pe', 'pb', 'total_mv', 'circ_mv', 'turnover_rate']:
                if field in fields:
                    non_null = self.storage.conn.execute(
                        f"SELECT COUNT({field}) FROM stock_market_cap WHERE {field} IS NOT NULL"
                    ).fetchone()[0]
                    completeness = (non_null / count * 100) if count > 0 else 0
                    stats['field_completeness'][field] = {
                        'non_null': non_null,
                        'completeness': f"{completeness:.1f}%"
                    }

            stats['exists'] = True
            return stats

        except Exception as e:
            return {
                'exists': False,
                'error': str(e)
            }


# 测试代码
if __name__ == '__main__':
    print("=" * 70)
    print("DuckDB数据管理器增强版测试")
    print("=" * 70)

    # 创建增强的管理器
    manager = DuckDBDataManagerEnhanced()

    # 获取统计信息
    print("\n[INFO] 获取stock_market_cap表统计信息...")
    stats = manager.get_market_cap_statistics()

    if stats['exists']:
        print(f"\n✅ stock_market_cap表存在")
        print(f"  总记录数: {stats['total_records']:,}")
        print(f"  日期范围: {stats['date_range']}")
        print(f"  股票数量: {stats['stock_count']:,}")
        print(f"  字段: {', '.join(stats['fields'])}")

        print(f"\n  字段完整性:")
        for field, info in stats['field_completeness'].items():
            print(f"    {field}: {info['non_null']:,} ({info['completeness']})")

        # 测试加载数据
        print(f"\n[INFO] 测试加载最近10条数据...")
        df = manager.load_market_cap_data(start_date='2024-01-01')
        if not df.empty:
            print(f"\n数据预览:")
            print(df.head(10))
    else:
        print(f"\n❌ {stats.get('message', '表不存在')}")

    print("\n" + "=" * 70)
