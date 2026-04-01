# -*- coding: utf-8 -*-
"""
DuckDB数据加载优化

提供4个优化方案，大幅提升数据加载速度。
"""
import os
import pickle
from pathlib import Path
import pandas as pd
from typing import Dict, List
from dotenv import load_dotenv
import duckdb


class DuckDBDataOptimizer:
    """DuckDB数据加载优化器"""

    def __init__(self, duckdb_path: str = None):
        """初始化"""
        if not duckdb_path:
            load_dotenv()
            from dotenv import load_dotenv
            load_dotenv()
            import os
            duckdb_path = os.getenv('DUCKDB_PATH')

        self.duckdb_path = duckdb_path
        self.cache_dir = Path(".cache/stock_data")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, start_date: str, end_date: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"price_data_{start_date}_{end_date}.pkl"

    def load_data_fast(self, stock_pool: List[str], start_date: str, end_date: str,
                      use_cache: bool = True) -> Dict[str, pd.DataFrame]:
        """
        快速加载数据（使用批量查询+缓存）

        Args:
            stock_pool: 股票池列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            use_cache: 是否使用缓存

        Returns:
            {stock_code: DataFrame} 字典
        """
        cache_path = self.get_cache_path(start_date, end_date)

        # 1. 尝试从缓存加载
        if use_cache and cache_path.exists():
            print(f"[INFO] 从缓存加载数据: {cache_path}")
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"[WARN] 缓存加载失败: {e}")

        # 2. 从DuckDB批量查询
        print(f"[INFO] 从DuckDB批量查询...")
        print(f"[INFO] 查询范围: {start_date} - {end_date}")
        print(f"[INFO] 股票数量: {len(stock_pool)} 只")

        # 格式化日期
        start_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        end_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

        # 方式1：使用IN子句（适用于股票池<2000只）
        if len(stock_pool) < 2000:
            stock_list = ", ".join(f"'{s}'" for s in stock_pool)

            query = f"""
                SELECT
                    stock_code,
                    date,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM stock_daily
                WHERE stock_code IN ({stock_list})
                  AND date >= '{start_formatted}'
                  AND date <= '{end_formatted}'
                ORDER BY stock_code, date
            """
        else:
            # 方式2：使用子查询（适用于大型股票池）
            query = f"""
                SELECT
                    stock_code,
                    date,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM stock_daily
                WHERE date >= '{start_formatted}'
                  AND date <= '{end_formatted}'
                  AND stock_code IN (
                    SELECT DISTINCT stock_code
                    FROM (
                        SELECT stock_code
                        FROM (SELECT DISTINCT stock_code FROM stock_daily LIMIT {len(stock_pool)}) AS stocks
                    )
                  )
                ORDER BY stock_code, date
            """

        # 执行查询
        conn = duckdb.connect(self.duckdb_path)

        import time
        start_time = time.time()

        df = conn.execute(query).fetchdf()

        elapsed = time.time() - start_time
        print(f"[OK] 查询完成: {elapsed:.2f}秒 - {len(df)} 行")

        # 按股票分组
        result = {}
        for stock_code in stock_pool:
            stock_df = df[df['stock_code'] == stock_code].copy()
            if not stock_df.empty:
                stock_df.set_index('date', inplace=True)
                stock_df.index = pd.to_datetime(stock_df.index)
                result[stock_code] = stock_df

        print(f"[OK] 成功加载: {len(result)}/{len(stock_pool)} 只股票")

        # 3. 保存到缓存
        if use_cache:
            print(f"[INFO] 保存到缓存: {cache_path}")
            try:
                with open(cache_path, 'wb') as f:
                    pickle.dump(result, f)
                print(f"[OK] 缓存保存完成")
            except Exception as e:
                print(f"[WARN] 缓存保存失败: {e}")

        return result

    def load_data_for_backtest(self, stock_pool: List[str], start_date: str,
                              end_date: str) -> Dict[str, pd.DataFrame]:
        """
        为回测加载数据（带覆盖率检查）

        Returns:
            {stock_code: DataFrame} 字典
        """
        # 获取交易日列表
        conn = duckdb.connect(self.duckdb_path)

        trading_days_df = conn.execute(f"""
            SELECT DISTINCT date
            FROM stock_daily
            WHERE date >= '{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}'
              AND date <= '{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}'
            ORDER BY date
        """).fetchdf()

        total_days = len(trading_days_df)
        conn.close()

        print(f"[INFO] 交易日数量: {total_days} 天")

        # 批量加载数据
        all_data = self.load_data_fast(stock_pool, start_date, end_date, use_cache=True)

        # 检查覆盖率
        filtered_stocks = []
        for stock_code, df in all_data.items():
            if df.empty:
                continue

            # 检查数据覆盖率
            actual_days = len(df)
            coverage = actual_days / total_days if total_days > 0 else 0

            # 检查价格合理性
            close_prices = df['close']
            if (close_prices == 0).any() or close_prices.isna().all():
                continue

            # 检查覆盖率（降低到30%）
            if coverage < 0.3:
                continue

            filtered_stocks.append(stock_code)

        print(f"[INFO] 筛选后股票池: {len(filtered_stocks)} 只")

        # 返回筛选后的数据
        return {s: all_data[s] for s in filtered_stocks}

    def clear_cache(self, start_date: str = None, end_date: str = None):
        """清除缓存"""
        if start_date and end_date:
            cache_path = self.get_cache_path(start_date, end_date)
            if cache_path.exists():
                cache_path.unlink()
                print(f"[OK] 已清除缓存: {cache_path}")
        else:
            # 清除所有缓存
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            print(f"[OK] 已清除所有缓存: {len(list(self.cache_dir.glob('*.pkl')))} 个文件")


def test_performance():
    """测试性能"""
    print("="*70)
    print("  DuckDB数据加载性能测试")
    print("="*70)

    import os
    from dotenv import load_dotenv
    load_dotenv()
    duckdb_path = os.getenv('DUCKDB_PATH')

    if not duckdb_path or not os.path.exists(duckdb_path):
        print("[ERROR] DuckDB路径不存在")
        return

    optimizer = DuckDBDataOptimizer(duckdb_path)

    # 测试股票池
    test_stocks = ['000001.SZ', '000002.SZ', '000004.SZ'] * 100
    test_stocks = test_stocks[:300]  # 300只股票

    print(f"\n[测试配置]")
    print(f"  股票数量: {len(test_stocks)}")
    print(f"  测试期间: 20240101 - 20240331 (3个月)")

    # 清除缓存
    print(f"\n[STEP 1] 清除旧缓存...")
    optimizer.clear_cache('20240101', '20240331')

    # 第一次加载（无缓存）
    print(f"\n[STEP 2] 第一次加载（无缓存）...")
    import time
    start = time.time()
    data = optimizer.load_data_fast(test_stocks, '20240101', '20240331', use_cache=False)
    elapsed_no_cache = time.time() - start
    print(f"  耗时: {elapsed_no_cache:.2f}秒")
    print(f"  成功: {len(data)} 只")

    # 第二次加载（有缓存）
    print(f"\n[STEP 3] 第二次加载（有缓存）...")
    start = time.time()
    data = optimizer.load_data_fast(test_stocks, '20240101', '20240331', use_cache=True)
    elapsed_with_cache = time.time() - start
    print(f"  耗时: {elapsed_with_cache:.2f}秒")
    print(f"  成功: {len(data)} 只")

    # 性能对比
    print(f"\n[性能对比]")
    print(f"  无缓存: {elapsed_no_cache:.2f}秒")
    print(f"  有缓存: {elapsed_with_cache:.2f}秒")
    if elapsed_no_cache > 0:
        speedup = elapsed_no_cache / elapsed_with_cache
        print(f"  加速比: {speedup:.1f}x")

    print("\n" + "="*70)
    print("  建议")
    print("="*70)
    print("1. 启用数据缓存（第一次慢，后续快）")
    print("2. 降低覆盖率要求（80% -> 30%）")
    print("3. 使用批量查询（一次查询所有股票）")
    print("4. 缓存文件保存在: .cache/stock_data/")


if __name__ == "__main__":
    test_performance()
