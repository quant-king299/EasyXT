"""
资金流向因子模块

基于qstock提供资金流向分析功能

主要功能：
1. 同花顺行业/概念资金流向
2. 北向资金流向（外资）
3. 同花顺个股资金流向
4. 智能缓存（DuckDB）
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


class MoneyFlowAnalyzer:
    """资金流向分析器（基于qstock）"""

    def __init__(self):
        """初始化"""
        self._init_qstock()

    def _init_qstock(self):
        """初始化qstock"""
        try:
            import qstock as qs
            self.qs = qs
            self.qs_available = True
        except ImportError:
            self.qs = None
            self.qs_available = False

    # ============================================================
    # 同花顺行业/概念资金流向
    # ============================================================

    def get_ths_industry_money_flow(self, top_n: int = 20,
                                   use_cache: bool = True,
                                   duckdb_reader=None) -> pd.DataFrame:
        """
        获取同花顺行业资金流向

        Args:
            top_n: 返回前N个行业
            use_cache: 是否使用DuckDB缓存
            duckdb_reader: DuckDBDataReader实例

        Returns:
            pd.DataFrame: 行业资金流向数据
            - 行业名称: 行业名称
            - 昨日涨跌: 昨日涨跌幅
            - 行业指数: 指数点位
            - 涨跌幅: 涨跌幅
            - 净流入(万): 主力净流入金额（万元）
            - 上涨家数: 板块内上涨股票数
            - 下跌家数: 板块内下跌股票数
            - 领涨股票: 领涨股票
        """
        if not self.qs_available:
            raise ImportError("请先安装qstock: pip install qstock")

        # 尝试从DuckDB读取缓存
        if use_cache and duckdb_reader is not None and duckdb_reader.conn is not None:
            try:
                # 检查表是否存在
                check_table = duckdb_reader.conn.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_name = 'ths_industry_money_flow'
                """).fetchdf()

                if not check_table.empty:
                    import json
                    query = """
                    SELECT raw_data FROM ths_industry_money_flow
                    ORDER BY date DESC
                    LIMIT 1
                    """
                    result = duckdb_reader.conn.execute(query).fetchdf()

                    if not result.empty:
                        print(f"[OK] 从DuckDB缓存读取行业资金流向数据")
                        data_json = result.iloc[0]['raw_data']
                        df = pd.DataFrame(json.loads(data_json))
                        return df.head(top_n)
            except Exception as e:
                print(f"[INFO] DuckDB缓存读取失败: {e}，从qstock获取...")

        # 从qstock获取数据
        try:
            df = self.qs.ths_industry_money()

            if df.empty:
                print("[INFO] 行业资金流向数据为空")
                return pd.DataFrame()

            print(f"[OK] 从qstock下载行业资金流向: {len(df)} 个行业")

            # 保存到DuckDB（如果提供了reader）
            if use_cache and duckdb_reader is not None and duckdb_reader.conn is not None:
                try:
                    import json
                    from datetime import datetime
                    today = datetime.now().strftime('%Y-%m-%d')

                    # 创建表（如果不存在）
                    create_table_sql = """
                    CREATE TABLE IF NOT EXISTS ths_industry_money_flow (
                        date DATE,
                        raw_data VARCHAR,
                        PRIMARY KEY (date)
                    )
                    """
                    duckdb_reader.conn.execute(create_table_sql)

                    # 删除今日旧数据
                    duckdb_reader.conn.execute(f"DELETE FROM ths_industry_money_flow WHERE date = '{today}'")

                    # 保存为JSON字符串
                    data_json = df.to_json(orient='records', force_ascii=False)
                    insert_sql = f"INSERT INTO ths_industry_money_flow VALUES ('{today}', '{data_json}')"
                    duckdb_reader.conn.execute(insert_sql)

                    print(f"[OK] 已保存到DuckDB")
                except Exception as e:
                    print(f"[WARNING] 保存到DuckDB失败: {e}")

            return df.head(top_n)

        except Exception as e:
            print(f"[ERROR] 获取行业资金流向失败: {e}")
            return pd.DataFrame()

    def get_ths_concept_money_flow(self, top_n: int = 20,
                                   use_cache: bool = True,
                                   duckdb_reader=None) -> pd.DataFrame:
        """
        获取同花顺概念资金流向

        Args:
            top_n: 返回前N个概念
            use_cache: 是否使用DuckDB缓存
            duckdb_reader: DuckDBDataReader实例

        Returns:
            pd.DataFrame: 概念资金流向数据
            - 板块名称: 概念名称
            - 昨日涨跌: 昨日涨跌幅
            - 板块指数: 指数点位
            - 涨跌幅: 涨跌幅
            - 净流入(万): 主力净流入金额（万元）
            - 上涨家数: 板块内上涨股票数
            - 下跌家数: 板块内下跌股票数
            - 领涨股票: 领涨股票
        """
        if not self.qs_available:
            raise ImportError("请先安装qstock: pip install qstock")

        # 尝试从DuckDB读取缓存
        if use_cache and duckdb_reader is not None and duckdb_reader.conn is not None:
            try:
                # 检查表是否存在
                check_table = duckdb_reader.conn.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_name = 'ths_concept_money_flow'
                """).fetchdf()

                if not check_table.empty:
                    import json
                    query = """
                    SELECT raw_data FROM ths_concept_money_flow
                    ORDER BY date DESC
                    LIMIT 1
                    """
                    result = duckdb_reader.conn.execute(query).fetchdf()

                    if not result.empty:
                        print(f"[OK] 从DuckDB缓存读取概念资金流向数据")
                        data_json = result.iloc[0]['raw_data']
                        df = pd.DataFrame(json.loads(data_json))
                        return df.head(top_n)
            except Exception as e:
                print(f"[INFO] DuckDB缓存读取失败: {e}，从qstock获取...")

        # 从qstock获取数据
        try:
            df = self.qs.ths_concept_money()

            if df.empty:
                print("[INFO] 概念资金流向数据为空")
                return pd.DataFrame()

            print(f"[OK] 从qstock下载概念资金流向: {len(df)} 个概念")

            # 保存到DuckDB（如果提供了reader）
            if use_cache and duckdb_reader is not None and duckdb_reader.conn is not None:
                try:
                    import json
                    from datetime import datetime
                    today = datetime.now().strftime('%Y-%m-%d')

                    # 创建表（如果不存在）
                    create_table_sql = """
                    CREATE TABLE IF NOT EXISTS ths_concept_money_flow (
                        date DATE,
                        raw_data VARCHAR,
                        PRIMARY KEY (date)
                    )
                    """
                    duckdb_reader.conn.execute(create_table_sql)

                    # 删除今日旧数据
                    duckdb_reader.conn.execute(f"DELETE FROM ths_concept_money_flow WHERE date = '{today}'")

                    # 保存为JSON字符串
                    data_json = df.to_json(orient='records', force_ascii=False)
                    insert_sql = f"INSERT INTO ths_concept_money_flow VALUES ('{today}', '{data_json}')"
                    duckdb_reader.conn.execute(insert_sql)

                    print(f"[OK] 已保存到DuckDB")
                except Exception as e:
                    print(f"[WARNING] 保存到DuckDB失败: {e}")

            return df.head(top_n)

        except Exception as e:
            print(f"[ERROR] 获取概念资金流向失败: {e}")
            return pd.DataFrame()

    def update_ths_money_flow(self, duckdb_reader=None) -> Dict[str, int]:
        """
        更新同花顺行业/概念资金流向数据到DuckDB

        Args:
            duckdb_reader: DuckDBDataReader实例

        Returns:
            Dict[str, int]: 更新结果
            - industry: 行业数量
            - concept: 概念数量
        """
        if not self.qs_available:
            raise ImportError("请先安装qstock: pip install qstock")

        result = {'industry': 0, 'concept': 0}

        # 更新行业资金流向
        print("\n[1] 更新行业资金流向")
        print("-" * 70)
        try:
            df_industry = self.qs.ths_industry_money()

            if not df_industry.empty:
                print(f"[OK] 下载成功！共 {len(df_industry)} 个行业")

                # 保存到DuckDB
                if duckdb_reader is not None and duckdb_reader.conn is not None:
                    import json
                    from datetime import datetime
                    today = datetime.now().strftime('%Y-%m-%d')

                    # 创建表
                    create_table_sql = """
                    CREATE TABLE IF NOT EXISTS ths_industry_money_flow (
                        date DATE,
                        raw_data VARCHAR,
                        PRIMARY KEY (date)
                    )
                    """
                    duckdb_reader.conn.execute(create_table_sql)

                    # 删除今日旧数据
                    duckdb_reader.conn.execute(f"DELETE FROM ths_industry_money_flow WHERE date = '{today}'")

                    # 保存为JSON字符串
                    data_json = df_industry.to_json(orient='records', force_ascii=False)
                    insert_sql = f"INSERT INTO ths_industry_money_flow VALUES ('{today}', '{data_json}')"
                    duckdb_reader.conn.execute(insert_sql)

                    print(f"[OK] 已保存到DuckDB")
                    result['industry'] = len(df_industry)

                    # 显示TOP10
                    print("\n行业资金流向TOP10：")
                    print(df_industry.head(10))
                else:
                    print("[WARNING] 未提供DuckDB连接，数据未保存")
            else:
                print("[INFO] 行业资金流向数据为空")

        except Exception as e:
            print(f"[ERROR] 更新行业资金流向失败: {e}")
            import traceback
            traceback.print_exc()

        # 更新概念资金流向
        print("\n\n[2] 更新概念资金流向")
        print("-" * 70)
        try:
            df_concept = self.qs.ths_concept_money()

            if not df_concept.empty:
                print(f"[OK] 下载成功！共 {len(df_concept)} 个概念")

                # 保存到DuckDB
                if duckdb_reader is not None and duckdb_reader.conn is not None:
                    import json
                    from datetime import datetime
                    today = datetime.now().strftime('%Y-%m-%d')

                    # 创建表
                    create_table_sql = """
                    CREATE TABLE IF NOT EXISTS ths_concept_money_flow (
                        date DATE,
                        raw_data VARCHAR,
                        PRIMARY KEY (date)
                    )
                    """
                    duckdb_reader.conn.execute(create_table_sql)

                    # 删除今日旧数据
                    duckdb_reader.conn.execute(f"DELETE FROM ths_concept_money_flow WHERE date = '{today}'")

                    # 保存为JSON字符串
                    data_json = df_concept.to_json(orient='records', force_ascii=False)
                    insert_sql = f"INSERT INTO ths_concept_money_flow VALUES ('{today}', '{data_json}')"
                    duckdb_reader.conn.execute(insert_sql)

                    print(f"[OK] 已保存到DuckDB")
                    result['concept'] = len(df_concept)

                    # 显示TOP10
                    print("\n概念资金流向TOP10：")
                    print(df_concept.head(10))
                else:
                    print("[WARNING] 未提供DuckDB连接，数据未保存")
            else:
                print("[INFO] 概念资金流向数据为空")

        except Exception as e:
            print(f"[ERROR] 更新概念资金流向失败: {e}")
            import traceback
            traceback.print_exc()

        return result

    # ============================================================
    # 北向资金流向
    # ============================================================

    def get_north_money_flow(self, days: int = 30,
                            use_cache: bool = True,
                            duckdb_reader=None) -> pd.DataFrame:
        """
        获取北向资金历史流向

        Args:
            days: 历史天数
            use_cache: 是否使用DuckDB缓存
            duckdb_reader: DuckDBDataReader实例

        Returns:
            pd.DataFrame: 北向资金流向历史数据
            - date: 日期
            - 净流入(亿): 净流入金额（亿元）
        """
        if not self.qs_available:
            raise ImportError("请先安装qstock: pip install qstock")

        # 尝试从DuckDB读取缓存
        if use_cache and duckdb_reader is not None and duckdb_reader.conn is not None:
            try:
                # 检查表是否存在
                check_table = duckdb_reader.conn.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_name = 'north_money_flow'
                """).fetchdf()

                if not check_table.empty:
                    query = f"""
                    SELECT * FROM north_money_flow
                    ORDER BY date DESC
                    LIMIT {days}
                    """
                    df_cached = duckdb_reader.conn.execute(query).fetchdf()

                    if not df_cached.empty and len(df_cached) >= days:
                        print(f"[OK] 从DuckDB缓存读取北向资金流向: {len(df_cached)} 条")
                        return df_cached.sort_values('date')
            except Exception as e:
                print(f"[INFO] DuckDB缓存读取失败: {e}，从qstock获取...")

        # 从qstock获取数据
        try:
            df = self.qs.north_money_flow()

            if df.empty:
                print("[INFO] 北向资金流向数据为空")
                return pd.DataFrame()

            print(f"[OK] 从qstock下载北向资金流向: {len(df)} 条记录")

            # 保存到DuckDB
            if use_cache and duckdb_reader is not None and duckdb_reader.conn is not None:
                try:
                    from datetime import datetime

                    # 创建表
                    create_table_sql = """
                    CREATE TABLE IF NOT EXISTS north_money_flow (
                        date DATE,
                        net_flow DOUBLE,
                        PRIMARY KEY (date)
                    )
                    """
                    duckdb_reader.conn.execute(create_table_sql)

                    # 插入数据
                    for _, row in df.iterrows():
                        insert_sql = f"""
                        INSERT OR REPLACE INTO north_money_flow VALUES
                        ('{row['date']}', {row['净流入(亿)']})
                        """
                        duckdb_reader.conn.execute(insert_sql)

                    print(f"[OK] 已保存到DuckDB")
                except Exception as e:
                    print(f"[WARNING] 保存到DuckDB失败: {e}")

            # 重命名列
            df = df.rename(columns={'净流入(亿)': 'net_flow'})

            # 返回最近days条
            if days and len(df) > days:
                df = df.tail(days)

            return df.sort_values('date')

        except Exception as e:
            print(f"[ERROR] 获取北向资金流向失败: {e}")
            return pd.DataFrame()

    def get_north_money_sector(self, top_n: int = 20) -> pd.DataFrame:
        """
        获取北向资金行业流向

        Args:
            top_n: 返回前N个行业

        Returns:
            pd.DataFrame: 北向资金行业流向
            - 日期: 日期
            - 行业: 行业名称
            - 净流入: 净流入金额
            - 增持股票只数: 增持股票数量
            - 减持股票只数: 减持股票数量
            - 增持市值: 增持市值
            - 减持市值: 减持市值
        """
        if not self.qs_available:
            raise ImportError("请先安装qstock: pip install qstock")

        try:
            df = self.qs.north_money_sector()

            if df.empty:
                print("[INFO] 北向资金行业流向数据为空")
                return pd.DataFrame()

            print(f"[OK] 获取北向资金行业流向: {len(df)} 个行业")

            return df.head(top_n)

        except Exception as e:
            print(f"[ERROR] 获取北向资金行业流向失败: {e}")
            return pd.DataFrame()

    def get_north_money_stock(self, stock_code: str = None, top_n: int = 20) -> pd.DataFrame:
        """
        获取北向资金个股流向

        Args:
            stock_code: 股票代码，None表示返回全部
            top_n: 返回前N只股票

        Returns:
            pd.DataFrame: 北向资金个股流向
            - 代码: 股票代码
            - 名称: 股票名称
            - 最新价: 最新价格
            - 涨跌幅: 涨跌幅
            - 持股数量: 持股数量
            - 持股市值: 持股市值
            - 持股占流通股本: 持股占流通股本比例
            - 持股占总股本: 持股占总股本比例
        """
        if not self.qs_available:
            raise ImportError("请先安装qstock: pip install qstock")

        try:
            df = self.qs.north_money_stock()

            if df.empty:
                print("[INFO] 北向资金个股流向数据为空")
                return pd.DataFrame()

            print(f"[OK] 获取北向资金个股流向: {len(df)} 只股票")

            # 如果指定了股票代码，筛选
            if stock_code:
                df_filtered = df[df['代码'] == stock_code]
                return df_filtered

            return df.head(top_n)

        except Exception as e:
            print(f"[ERROR] 获取北向资金个股流向失败: {e}")
            return pd.DataFrame()

    # ============================================================
    # 同花顺个股资金流向
    # ============================================================

    def get_ths_stock_money_flow(self, stock_code: str = None,
                                  top_n: int = 20,
                                  use_cache: bool = True,
                                  duckdb_reader=None) -> pd.DataFrame:
        """
        获取同花顺个股资金流向（全市场或指定股票）

        Args:
            stock_code: 股票代码，None表示返回全市场排行
            top_n: 返回前N只股票（仅当stock_code为None时有效）
            use_cache: 是否使用DuckDB缓存（仅全市场数据支持缓存）
            duckdb_reader: DuckDBDataReader实例

        Returns:
            pd.DataFrame: 个股资金流向
            - 代码: 股票代码
            - 名称: 股票名称
            - 最新价: 最新价格
            - 涨跌幅: 涨跌幅
            - 换手率: 换手率
            - 净流入(万): 净流入金额（万元）
        """
        if not self.qs_available:
            raise ImportError("请先安装qstock: pip install qstock")

        # 如果没有指定股票代码，获取全市场排行
        if stock_code is None:
            # 尝试从DuckDB读取缓存
            if use_cache and duckdb_reader is not None and duckdb_reader.conn is not None:
                try:
                    # 检查表是否存在
                    check_table = duckdb_reader.conn.execute("""
                        SELECT table_name FROM information_schema.tables
                        WHERE table_name = 'ths_stock_money_flow'
                    """).fetchdf()

                    if not check_table.empty:
                        from datetime import datetime
                        today = datetime.now().strftime('%Y-%m-%d')
                        query = f"""
                        SELECT raw_data FROM ths_stock_money_flow
                        WHERE date = '{today}'
                        LIMIT 1
                        """
                        result = duckdb_reader.conn.execute(query).fetchdf()

                        if not result.empty:
                            print(f"[OK] 从DuckDB缓存读取个股资金流向数据")
                            import json
                            data_json = result.iloc[0]['raw_data']
                            df = pd.DataFrame(json.loads(data_json))
                            return df.head(top_n)
                except Exception as e:
                    print(f"[INFO] DuckDB缓存读取失败: {e}，从qstock获取...")

            # 从qstock获取全市场数据
            try:
                df = self.qs.ths_stock_money()

                if df.empty:
                    print("[INFO] 个股资金流向数据为空")
                    return pd.DataFrame()

                print(f"[OK] 从qstock下载个股资金流向: {len(df)} 只股票")

                # 保存到DuckDB
                if use_cache and duckdb_reader is not None and duckdb_reader.conn is not None:
                    try:
                        import json
                        from datetime import datetime
                        today = datetime.now().strftime('%Y-%m-%d')

                        # 创建表
                        create_table_sql = """
                        CREATE TABLE IF NOT EXISTS ths_stock_money_flow (
                            date DATE,
                            raw_data VARCHAR,
                            PRIMARY KEY (date)
                        )
                        """
                        duckdb_reader.conn.execute(create_table_sql)

                        # 删除今日旧数据
                        duckdb_reader.conn.execute(f"DELETE FROM ths_stock_money_flow WHERE date = '{today}'")

                        # 保存为JSON字符串
                        data_json = df.to_json(orient='records', force_ascii=False)
                        insert_sql = f"INSERT INTO ths_stock_money_flow VALUES ('{today}', '{data_json}')"
                        duckdb_reader.conn.execute(insert_sql)

                        print(f"[OK] 已保存到DuckDB")
                    except Exception as e:
                        print(f"[WARNING] 保存到DuckDB失败: {e}")

                return df.head(top_n)

            except Exception as e:
                print(f"[ERROR] 获取个股资金流向失败: {e}")
                return pd.DataFrame()
        else:
            # 指定了股票代码，从全市场数据中筛选
            try:
                df_all = self.qs.ths_stock_money()

                if df_all.empty:
                    return pd.DataFrame()

                # 筛选指定股票
                df_filtered = df_all[df_all['代码'] == stock_code]

                if df_filtered.empty:
                    print(f"[INFO] 未找到股票 {stock_code} 的资金流向数据")
                    return pd.DataFrame()

                return df_filtered

            except Exception as e:
                print(f"[ERROR] 获取个股资金流向失败: {e}")
                return pd.DataFrame()


# ============================================================
# 便捷函数
# ============================================================

def get_ths_industry_money_flow(top_n: int = 20) -> pd.DataFrame:
    """快捷函数：获取同花顺行业资金流向"""
    analyzer = MoneyFlowAnalyzer()
    return analyzer.get_ths_industry_money_flow(top_n)


def get_ths_concept_money_flow(top_n: int = 20) -> pd.DataFrame:
    """快捷函数：获取同花顺概念资金流向"""
    analyzer = MoneyFlowAnalyzer()
    return analyzer.get_ths_concept_money_flow(top_n)


def get_north_money_flow(days: int = 30) -> pd.DataFrame:
    """快捷函数：获取北向资金流向"""
    analyzer = MoneyFlowAnalyzer()
    return analyzer.get_north_money_flow(days)


def get_north_money_sector(top_n: int = 20) -> pd.DataFrame:
    """快捷函数：获取北向资金行业流向"""
    analyzer = MoneyFlowAnalyzer()
    return analyzer.get_north_money_sector(top_n)


def get_north_money_stock(stock_code: str = None, top_n: int = 20) -> pd.DataFrame:
    """快捷函数：获取北向资金个股流向"""
    analyzer = MoneyFlowAnalyzer()
    return analyzer.get_north_money_stock(stock_code, top_n)


def get_ths_stock_money_flow(stock_code: str = None, top_n: int = 20) -> pd.DataFrame:
    """快捷函数：获取同花顺个股资金流向"""
    analyzer = MoneyFlowAnalyzer()
    return analyzer.get_ths_stock_money_flow(stock_code, top_n)


if __name__ == "__main__":
    """测试代码"""
    print("=" * 70)
    print("  资金流向因子测试（qstock版）")
    print("=" * 70)

    analyzer = MoneyFlowAnalyzer()

    # 测试1: 行业资金流向
    print("\n[测试1] 获取行业资金流向...")
    try:
        df = analyzer.get_ths_industry_money_flow(top_n=10)
        if not df.empty:
            print("[OK] 成功!")
            print(f"  共 {len(df)} 个行业")
            print(df.head(5).to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试2: 概念资金流向
    print("\n[测试2] 获取概念资金流向...")
    try:
        df = analyzer.get_ths_concept_money_flow(top_n=10)
        if not df.empty:
            print("[OK] 成功!")
            print(f"  共 {len(df)} 个概念")
            print(df.head(5).to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试3: 北向资金流向
    print("\n[测试3] 获取北向资金流向...")
    try:
        df = analyzer.get_north_money_flow(days=10)
        if not df.empty:
            print("[OK] 成功!")
            print(f"  共 {len(df)} 条记录")
            print(df.head(5).to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试4: 北向资金行业流向
    print("\n[测试4] 获取北向资金行业流向...")
    try:
        df = analyzer.get_north_money_sector(top_n=10)
        if not df.empty:
            print("[OK] 成功!")
            print(f"  共 {len(df)} 个行业")
            print(df.head(5).to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试5: 个股资金流向
    print("\n[测试5] 获取个股资金流向...")
    try:
        df = analyzer.get_ths_stock_money_flow(top_n=10)
        if not df.empty:
            print("[OK] 成功!")
            print(f"  共 {len(df)} 只股票")
            print(df.head(5).to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n" + "=" * 70)
    print("  测试完成!")
    print("=" * 70)
