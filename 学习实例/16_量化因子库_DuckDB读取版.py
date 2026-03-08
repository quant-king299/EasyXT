"""
量化因子库 - DuckDB数据读取版

功能：
1. 直接从DuckDB读取历史数据
2. 进行完整的因子分析
3. 支持自定义股票列表

使用方法：
1. 确保DuckDB数据库存在: D:/StockData/stock_data.ddb
2. 修改要分析的股票列表
3. 运行脚本

作者：EasyXT团队
日期：2026-02-06
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

easy_xt_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'easy_xt'))
if easy_xt_dir not in sys.path:
    sys.path.insert(0, easy_xt_dir)

# ============================================================
# 配置
# ============================================================

# DuckDB数据库路径
DUCKDB_PATH = r'D:/StockData/stock_data.ddb'

# 要分析的股票列表
# 可用股票查询方法：
# SELECT DISTINCT stock_code FROM stock_daily ORDER BY stock_code LIMIT 100;
STOCK_LIST = [
    '000001.SZ',  # 平安银行
    '000002.SZ',  # 万科A
    '000004.SZ',  # 国华网安
    '600000.SH',  # 浦发银行
    '600036.SH',  # 招商银行
    '600519.SH',  # 贵州茅台
    '000858.SZ',  # 五粮液
    '002475.SZ',  # 立讯精密
]

# 分析参数
START_DATE = '2024-01-01'
END_DATE = None  # None表示到今天

# ============================================================
# DuckDB数据读取器
# ============================================================

class DuckDBDataReader:
    """DuckDB数据读取器"""

    def __init__(self, duckdb_path):
        self.duckdb_path = duckdb_path
        self.conn = None
        self._connect()

    def _log(self, msg):
        print(f"[数据读取器] {msg}")

    def _connect(self):
        """连接DuckDB"""
        try:
            import duckdb
            self.conn = duckdb.connect(self.duckdb_path)
            self._log(f"成功连接数据库: {self.duckdb_path}")
        except ImportError:
            self._log("错误：duckdb未安装，请运行: pip install duckdb")
        except Exception as e:
            self._log(f"连接失败: {e}")

    def get_stock_list(self, limit=None):
        """获取数据库中的股票列表"""
        if self.conn is None:
            return []

        try:
            sql = "SELECT DISTINCT stock_code FROM stock_daily ORDER BY stock_code"
            if limit:
                sql += f" LIMIT {limit}"

            df = self.conn.execute(sql).fetchdf()
            return df['stock_code'].tolist()

        except Exception as e:
            self._log(f"获取股票列表失败: {e}")
            return []

    def get_market_data(self, stock_list, start_date, end_date=None):
        """读取市场数据"""
        if self.conn is None:
            return pd.DataFrame()

        try:
            # 构建SQL查询
            stocks_str = "', '".join(stock_list)
            sql = f"""
                SELECT * FROM stock_daily
                WHERE stock_code IN ('{stocks_str}')
                  AND date >= '{start_date}'
            """

            if end_date:
                sql += f" AND date <= '{end_date}'"

            sql += " ORDER BY stock_code, date"

            # 执行查询
            df = self.conn.execute(sql).fetchdf()

            if not df.empty:
                self._log(f"读取到 {len(df)} 条数据，{df['stock_code'].nunique()} 只股票")

            return df

        except Exception as e:
            self._log(f"查询失败: {e}")
            import traceback
            self._log(traceback.format_exc()[:500])
            return pd.DataFrame()

    def get_stock_info(self, stock_code):
        """获取单个股票的信息"""
        if self.conn is None:
            return None

        try:
            sql = f"""
                SELECT
                    stock_code,
                    MIN(date) as first_date,
                    MAX(date) as last_date,
                    COUNT(*) as data_count
                FROM stock_daily
                WHERE stock_code = '{stock_code}'
                GROUP BY stock_code
            """

            result = self.conn.execute(sql).fetchdf()
            return result.iloc[0] if not result.empty else None

        except Exception as e:
            self._log(f"查询股票信息失败: {e}")
            return None

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()


# ============================================================
# 因子计算器
# ============================================================

class FactorCalculator:
    """因子计算器"""

    def __init__(self, data_reader):
        self.dr = data_reader

    def calculate_all_factors(self, stock_list, start_date, end_date=None):
        """计算所有因子"""
        print("\n" + "=" * 70)
        print("因子分析开始")
        print("=" * 70)

        # 读取数据
        print(f"\n[读取数据] {len(stock_list)} 只股票")
        data = self.dr.get_market_data(stock_list, start_date, end_date)

        if data.empty:
            print("[错误] 未读取到数据")
            return None

        # 计算各类因子
        results = {}

        # 1. 动量因子
        results['momentum'] = self._calculate_momentum(data)

        # 2. 波动率因子
        results['volatility'] = self._calculate_volatility(data)

        # 3. 量价因子
        results['volume_price'] = self._calculate_volume_price(data)

        # 4. 技术指标
        results['technical'] = self._calculate_technical(data)

        # 5. 综合评分
        results['scores'] = self._calculate_composite_score(data, results)

        return results

    def _calculate_momentum(self, data):
        """计算动量因子"""
        print("\n[计算] 动量因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                recent_close = stock_data['close'].iloc[-1]

                for period in [5, 10, 20, 60]:
                    if len(stock_data) >= period:
                        past_close = stock_data['close'].iloc[-period]
                        momentum = (recent_close - past_close) / past_close * 100

                        results.append({
                            'stock_code': stock,
                            'period': f'{period}日',
                            'momentum_pct': round(momentum, 2),
                            'current_price': round(recent_close, 2)
                        })

        return pd.DataFrame(results)

    def _calculate_volatility(self, data):
        """计算波动率因子"""
        print("\n[计算] 波动率因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20:
                recent_data = stock_data.tail(20)
                returns = recent_data['close'].pct_change().dropna()

                if len(returns) > 0:
                    volatility = returns.std() * np.sqrt(252) * 100
                    max_drawdown = self._calculate_max_drawdown(recent_data['close'])

                    results.append({
                        'stock_code': stock,
                        'volatility_pct': round(volatility, 2),
                        'max_drawdown_pct': round(max_drawdown, 2),
                        'price_range': round(recent_data['high'].max() / recent_data['low'].min() - 1, 4)
                    })

        return pd.DataFrame(results)

    def _calculate_max_drawdown(self, price_series):
        """计算最大回撤"""
        cummax = price_series.cummax()
        drawdown = (price_series - cummax) / cummax
        return drawdown.min() * 100

    def _calculate_volume_price(self, data):
        """计算量价因子"""
        print("\n[计算] 量价因子...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 20 and 'volume' in stock_data.columns:
                recent_data = stock_data.tail(20)
                avg_volume = recent_data['volume'].mean()
                recent_volume = recent_data['volume'].iloc[-1]
                volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0

                # 计算价量趋势
                price_change = stock_data['close'].pct_change().iloc[-1]
                volume_change = stock_data['volume'].pct_change().iloc[-1]
                trend = 'positive' if (price_change > 0 and volume_change > 0) or (price_change < 0 and volume_change < 0) else 'negative'

                results.append({
                    'stock_code': stock,
                    'volume_ratio': round(volume_ratio, 2),
                    'trend': trend
                })

        return pd.DataFrame(results)

    def _calculate_technical(self, data):
        """计算技术指标"""
        print("\n[计算] 技术指标...")
        results = []

        for stock in data['stock_code'].unique():
            stock_data = data[data['stock_code'] == stock].sort_values('date')

            if len(stock_data) >= 60:
                current_price = stock_data['close'].iloc[-1]

                for period in [5, 10, 20, 60]:
                    if len(stock_data) >= period:
                        ma = stock_data['close'].tail(period).mean()

                        results.append({
                            'stock_code': stock,
                            'period': f'MA{period}',
                            'ma_value': round(ma, 2),
                            'price_vs_ma_pct': round((current_price - ma) / ma * 100, 2),
                            'signal': 'above' if current_price > ma else 'below'
                        })

        return pd.DataFrame(results)

    def _calculate_composite_score(self, data, factor_results):
        """计算综合评分"""
        print("\n[计算] 综合评分...")
        scores = {}

        momentum_20 = factor_results['momentum']
        volatility = factor_results['volatility']
        volume_price = factor_results['volume_price']
        technical = factor_results['technical']

        for stock in data['stock_code'].unique():
            score = 0
            count = 0

            # 动量得分
            if not momentum_20.empty:
                stock_mom = momentum_20[momentum_20['period'] == '20日']
                if not stock_mom.empty and stock in stock_mom['stock_code'].values:
                    mom_val = stock_mom[stock_mom['stock_code'] == stock]['momentum_pct'].iloc[0]
                    score += min(mom_val / 5, 10)
                    count += 1

            # 波动率得分（低波动率加分）
            if not volatility.empty:
                stock_vol = volatility[volatility['stock_code'] == stock]
                if not stock_vol.empty:
                    vol_val = stock_vol['volatility_pct'].iloc[0]
                    score += max(10 - vol_val / 3, 0)
                    count += 1

            # 量价得分
            if not volume_price.empty:
                stock_vp = volume_price[volume_price['stock_code'] == stock]
                if not stock_vp.empty and stock_vp['trend'].iloc[0] == 'positive':
                    score += 5
                    count += 1

            # 技术指标得分
            if not technical.empty:
                stock_tech = technical[(technical['stock_code'] == stock) & (technical['period'] == 'MA20')]
                if not stock_tech.empty and stock_tech['signal'].iloc[0] == 'above':
                    score += 5
                    count += 1

            scores[stock] = {
                'total_score': round(score, 2),
                'max_score': count * 10,
                'rating': self._get_rating(score, count * 10)
            }

        return pd.DataFrame(scores).T

    def _get_rating(self, score, max_score):
        """获取评级"""
        ratio = score / max_score if max_score > 0 else 0
        if ratio > 0.7:
            return 'A (强烈推荐)'
        elif ratio > 0.5:
            return 'B (推荐)'
        elif ratio > 0.3:
            return 'C (中性)'
        else:
            return 'D (不推荐)'


# ============================================================
# 报告生成器
# ============================================================

def generate_report(factor_results):
    """生成分析报告"""
    print("\n" + "=" * 70)
    print("因子分析报告")
    print("=" * 70)

    if factor_results is None:
        print("\n[错误] 无分析结果")
        return

    # 1. 综合评分排行
    if 'scores' in factor_results and not factor_results['scores'].empty:
        print("\n[1] 综合评分排行")
        print("-" * 70)
        scores_sorted = factor_results['scores'].sort_values('total_score', ascending=False)
        for idx, row in scores_sorted.iterrows():
            print(f"\n股票: {idx}")
            print(f"  评分: {row['total_score']:.2f} / {row['max_score']:.2f}")
            print(f"  评级: {row['rating']}")

    # 2. 动量分析
    if 'momentum' in factor_results and not factor_results['momentum'].empty:
        print("\n\n[2] 动量分析（20日收益率）")
        print("-" * 70)
        momentum_20 = factor_results['momentum'][factor_results['momentum']['period'] == '20日']
        print(momentum_20.sort_values('momentum_pct', ascending=False).to_string(index=False))

    # 3. 风险分析
    if 'volatility' in factor_results and not factor_results['volatility'].empty:
        print("\n\n[3] 风险分析（波动率与回撤）")
        print("-" * 70)
        print(factor_results['volatility'].sort_values('volatility_pct').to_string(index=False))

    # 4. 量价分析
    if 'volume_price' in factor_results and not factor_results['volume_price'].empty:
        print("\n\n[4] 量价分析")
        print("-" * 70)
        print(factor_results['volume_price'].to_string(index=False))

    # 5. 技术指标
    if 'technical' in factor_results and not factor_results['technical'].empty:
        print("\n\n[5] 技术指标（MA20信号）")
        print("-" * 70)
        ma20 = factor_results['technical'][factor_results['technical']['period'] == 'MA20']
        print(ma20[['stock_code', 'ma_value', 'signal']].to_string(index=False))

    print("\n" + "=" * 70)
    print("报告生成完成")
    print("=" * 70)


# ============================================================
# 主程序
# ============================================================

def main():
    """主程序"""
    print("=" * 70)
    print("量化因子库 - DuckDB数据读取版")
    print("=" * 70)

    # 1. 连接数据库
    print("\n[步骤1] 连接数据库")
    print("-" * 70)
    reader = DuckDBDataReader(DUCKDB_PATH)

    if reader.conn is None:
        print("\n[错误] 无法连接数据库")
        return

    # 2. 查看可用股票
    print("\n[步骤2] 查看可用股票")
    print("-" * 70)
    all_stocks = reader.get_stock_list(limit=20)
    print(f"[OK] 数据库中有股票: {len(all_stocks)} 只（显示前20只）")
    print(f"  {', '.join(all_stocks)}")

    # 显示股票信息
    print(f"\n[股票信息示例]")
    for stock in STOCK_LIST[:3]:
        info = reader.get_stock_info(stock)
        if info is not None:
            print(f"  {stock}: {info['first_date']} 至 {info['last_date']}, {info['data_count']} 条数据")

    # 3. 因子分析
    print(f"\n[步骤3] 因子分析 ({len(STOCK_LIST)} 只股票)")
    print("-" * 70)
    calculator = FactorCalculator(reader)

    results = calculator.calculate_all_factors(STOCK_LIST, START_DATE, END_DATE)

    # 4. 生成报告
    print(f"\n[步骤4] 生成报告")
    print("-" * 70)
    generate_report(results)

    # 5. 关闭连接
    reader.close()

    print(f"\n[提示]")
    print(f"1. 数据来源: {DUCKDB_PATH}")
    print(f"2. 分析股票数: {len(STOCK_LIST)}")
    print(f"3. 时间范围: {START_DATE} 至今")
    print(f"4. 可修改 STOCK_LIST 来分析更多股票")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
