"""
ETF 趋势轮动策略
================

基于均线多头排列 + 溢价率保护，轮动持有趋势最强的 ETF。

策略逻辑:
  1. 扫描全市场 ETF，计算均线多头得分 (MA5>MA10>MA20>MA30>MA60)
  2. 按得分降序排列，选择前 buy_n 只
  3. 买入条件: 均线得分 >= min_score 且 溢价率 <= max_premium
  4. 卖出条件:
     - 跌出排名 hold_rank 之外
     - 跌破 N 日均线
     - 溢价率超过阈值（防止大幅溢价买入）

数据来源: DuckDB etf_daily（本地，毫秒级）

使用方式:
  from strategies.quant_strategies.etf_trend import ETFTrendStrategy
  strategy = ETFTrendStrategy(api, buy_n=5)
  strategy.run(dry_run=True)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Dict, List, Optional

from .data_utils import get_etf_list, get_etf_premium, get_easyxt_api
from easy_xt.indicators import ma as calc_ma, hhv, llv


class ETFTrendStrategy:
    """
    ETF 趋势轮动策略。

    参数:
      api            : EasyXT API 实例
      buy_n          : 持有 ETF 数量上限
      min_score      : 买入最低均线得分 (0~100)
      hold_rank      : 持仓排名阈值（超出此排名才考虑卖出）
      break_ma_n     : 跌破 N 日均线触发卖出
      max_premium    : 最大可接受溢价率 (%)
      deviation_up   : 向上偏离均线触发卖出 (%)
      deviation_down : 向下缓冲区 (%)
      exclude_style  : 排除的 ETF 类型列表（如 ['债券', '货币']）
      only_stock_etf : 仅保留股票型 ETF
    """

    def __init__(self, api=None, account_id=None, **kwargs):
        self.api = api or get_easyxt_api()
        self.account_id = account_id

        self.buy_n = kwargs.get('buy_n', 5)
        self.min_score = kwargs.get('min_score', 50)
        self.hold_rank = kwargs.get('hold_rank', 15)
        self.break_ma_n = kwargs.get('break_ma_n', 20)
        self.max_premium = kwargs.get('max_premium', 3.0)
        self.deviation_up = kwargs.get('deviation_up', 10.0)
        self.deviation_down = kwargs.get('deviation_down', 5.0)
        self.exclude_style = kwargs.get('exclude_style', ['债券', '货币'])
        self.only_stock_etf = kwargs.get('only_stock_etf', True)

        # 状态
        self.etf_pool = None
        self.positions = None
        self.buy_list = None
        self.sell_list = None
        self.score_df = None

    # ================================================================
    # 数据获取
    # ================================================================

    def fetch_etf_list(self) -> pd.DataFrame:
        """
        获取 ETF 列表并过滤。

        过滤:
          - 排除债券型/货币型
          - 排除成交额低于 100 万的（流动性不足）
        """
        print('[*] 获取 ETF 列表...')
        from .data_utils import get_etf_from_duckdb
        df = get_etf_from_duckdb()
        if df.empty:
            df = get_etf_list()
        if df.empty:
            raise RuntimeError('获取 ETF 数据失败')

        pool = df.copy()

        # 排除指定类型（通过名称关键词过滤）
        if self.only_stock_etf and 'fund_name' in pool.columns:
            for keyword in self.exclude_style:
                pool = pool[~pool['fund_name'].str.contains(keyword, na=False)]

        # 排除流动性差的 ETF（日成交额 < 100 万）
        if 'amount' in pool.columns:
            pool = pool[pool['amount'] >= 100_0000]

        # 排除价格异常
        if 'price' in pool.columns:
            pool = pool[pool['price'].between(0.1, 100)]

        print(f'    全市场 ETF 过滤后: {len(pool)} 只')
        self.etf_pool = pool
        return pool

    # ================================================================
    # 核心打分
    # ================================================================

    def calc_trend_score(self, pool: pd.DataFrame) -> pd.DataFrame:
        """
        计算 ETF 趋势得分。

        对每只 ETF:
          1. 取最近 120 天日线 K 线
          2. 计算 MA5, MA10, MA20, MA30, MA60
          3. 检查多头排列: 满足一层 +20 分，满分 100

        返回附加 trend_score 的 DataFrame。
        """
        scores = {}
        codes = pool['fund_code'].tolist()

        print(f'[*] 计算 {len(codes)} 只 ETF 趋势得分 (DuckDB 批量)...')

        # ── DuckDB 批量查询所有 ETF 最近 120 天 K 线 ──
        kline_map = {}  # code → close_series
        try:
            import duckdb
            con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)
            in_clause = ','.join(f"'{c}'" for c in codes)
            df = con.execute(f"""
                SELECT ts_code, trade_date, close
                FROM etf_daily
                WHERE ts_code IN ({in_clause}) AND close > 0
                ORDER BY ts_code, trade_date DESC
            """).fetchdf()
            con.close()
            if not df.empty:
                for code in codes:
                    code_df = df[df['ts_code'] == code].head(120)
                    if len(code_df) >= 60:
                        kline_map[code] = code_df['close'].values[::-1]  # 升序
        except Exception as e:
            print(f'    批量查询失败: {e}')

        # ── 计算趋势得分 ──
        for code in codes:
            close = kline_map.get(code)
            if close is None or len(close) < 60:
                scores[code] = 0
                continue

            close_arr = np.array(close)
            ma5 = calc_ma(close_arr, 5)[-1]
            ma10 = calc_ma(close_arr, 10)[-1]
            ma20 = calc_ma(close_arr, 20)[-1]
            ma30 = calc_ma(close_arr, 30)[-1]
            ma60 = calc_ma(close_arr, 60)[-1]

            s = 0
            if ma5 > ma10: s += 20
            if ma10 > ma20: s += 20
            if ma20 > ma30: s += 20
            if ma30 > ma60: s += 20
            if ma5 > ma60: s += 20
            scores[code] = s

        pool['trend_score'] = pool['fund_code'].map(scores).fillna(0)
        pool = pool.sort_values('trend_score', ascending=False)
        pool['trend_rank'] = range(1, len(pool) + 1)
        return pool

    # ================================================================
    # 信号生成
    # ================================================================

    def generate_signals(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        pool = self.fetch_etf_list()
        pool = self.calc_trend_score(pool)

        # 过滤得分不足的
        pool = pool[pool['trend_score'] >= self.min_score]

        # 读取持仓
        self.positions = self._get_positions()
        held_codes = set(self.positions['fund_code'].tolist()) if len(self.positions) > 0 else set()
        current_count = len(held_codes)

        # 买入候选
        buy_list = []
        for _, row in pool.iterrows():
            code = row['fund_code']
            if code in held_codes:
                continue
            if current_count >= self.buy_n:
                break

            # 溢价率检查
            premium = get_etf_premium(code)
            if premium is not None and abs(premium) > self.max_premium:
                continue

            buy_list.append({
                'fund_code': code,
                'fund_name': row.get('fund_name', ''),
                'price': row.get('price', 0),
                'trend_score': row['trend_score'],
                'trend_rank': row['trend_rank'],
                'premium': round(premium, 2) if premium else None,
            })
            current_count += 1

        # 卖出判断
        sell_list = []
        top_ranks = pool.head(self.hold_rank)
        for _, pos in self.positions.iterrows():
            code = pos['fund_code']
            reason = None

            # 跌出排名
            if code not in top_ranks['fund_code'].values:
                reason = f'跌出前{self.hold_rank}'
            else:
                # 检查均线跌破
                ma_broken = self._check_ma_break(code)
                if ma_broken:
                    reason = f'跌破{self.break_ma_n}日均线'

            if reason:
                # 从持仓或池子取价格
                price = float(pos.get('open_price', 0) or 0)
                if price <= 0 and self.etf_pool is not None:
                    price_info = self.etf_pool[self.etf_pool['fund_code'] == str(code)]
                    price = price_info['price'].values[0] if len(price_info) > 0 else 0

                sell_list.append({
                    'fund_code': code,
                    'fund_name': pos.get('fund_name', ''),
                    'price': price,
                    'trend_score': pos.get('trend_score', 0),
                    'reason': reason,
                })

        self.buy_list = pd.DataFrame(buy_list) if buy_list else pd.DataFrame(
            columns=['fund_code', 'fund_name', 'price', 'trend_score', 'trend_rank', 'premium'])
        self.sell_list = pd.DataFrame(sell_list) if sell_list else pd.DataFrame(
            columns=['fund_code', 'fund_name', 'trend_score', 'reason'])
        self.score_df = pool

        return self.buy_list, self.sell_list

    # ================================================================
    # 辅助
    # ================================================================

    def _check_ma_break(self, code: str) -> bool:
        """检查是否跌破 N 日均线（DuckDB 查询）"""
        try:
            import duckdb
            con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)
            rows = con.execute("""
                SELECT close FROM etf_daily
                WHERE ts_code = ? AND close > 0
                ORDER BY trade_date DESC LIMIT ?
            """, [code, 60]).fetchall()
            con.close()

            if not rows or len(rows) < self.break_ma_n:
                return False

            close = np.array([r[0] for r in rows[::-1]])
            ma_val = calc_ma(close, self.break_ma_n)[-1]
            return close[-1] < ma_val
        except Exception:
            return False

    def _get_positions(self) -> pd.DataFrame:
        empty = pd.DataFrame(columns=['fund_code', 'fund_name', 'volume'])
        account_id = self.account_id or ''
        if not account_id or not self.api:
            return empty
        try:
            if not hasattr(self.api, 'trade') or self.api.trade is None:
                return empty
            df = self.api.trade.get_positions(account_id)
            if df is None or df.empty:
                return empty
            if 'code' in df.columns:
                df['fund_code'] = df['code'].astype(str)
                etf_prefixes = ('51','56','58','588','159','501','16')
                df = df[df['fund_code'].str[:3].isin(etf_prefixes) |
                        df['fund_code'].str[:4].isin(('5880',))]
                return df
            return df
        except Exception:
            return empty

    # ================================================================
    # 执行
    # ================================================================

    def run(self, dry_run: bool = True):
        print(f'\n{"="*60}')
        print(f'[ETF 趋势轮动策略] {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        print(f'{"="*60}')

        buy_list, sell_list = self.generate_signals()

        print(f'\n--- 持仓 ({len(self.positions)} 只) ---')
        if len(self.positions) > 0:
            cols = [c for c in ['code', 'fund_code', 'fund_name', 'volume', 'can_use_volume']
                    if c in self.positions.columns]
            print(self.positions[cols].head(10).to_string(index=False))

        print(f'\n--- 卖出信号 ---')
        if len(sell_list) > 0:
            print(sell_list.to_string(index=False))
        else:
            print('  无')

        print(f'\n--- 买入信号 (前 {self.buy_n}) ---')
        if len(buy_list) > 0:
            print(buy_list.to_string(index=False))
        else:
            print('  无')

        if not dry_run:
            self._execute_orders(buy_list, sell_list)

    def _execute_orders(self, buy_list, sell_list):
        from .data_utils import round_price, get_safe_sell_volume

        if not self.account_id or not hasattr(self.api, 'trade') or self.api.trade is None:
            print('[提示] 交易服务未初始化，跳过下单。')
            return
        acc = self.account_id
        positions = self.positions if self.positions is not None else pd.DataFrame()

        for _, row in sell_list.iterrows():
            try:
                code = str(row['fund_code'])
                if not code.endswith(('.SH', '.SZ')):
                    code = code + ('.SH' if code.startswith(('51','56','58')) else '.SZ')
                price = float(row.get('price', 0) or 0)
                if price <= 0:
                    print(f'  [跳过] {code} 无法获取价格')
                    continue
                vol = get_safe_sell_volume(positions, code, 100)
                price = round_price(code, price)
                self.api.trade.sell(account_id=acc, code=code, volume=vol,
                                   price=price, price_type='limit')
                print(f'  [卖出] {code} @{price:.3f} vol={vol}')
            except Exception as e:
                print(f'  [卖出失败] {row["fund_code"]}: {e}')

        for _, row in buy_list.iterrows():
            try:
                code = str(row['fund_code'])
                if not code.endswith(('.SH', '.SZ')):
                    code = code + ('.SH' if code.startswith(('51','56','58')) else '.SZ')
                price = round_price(code, float(row.get('price', 0)))
                self.api.trade.buy(account_id=acc, code=code, volume=100,
                                  price=price, price_type='limit')
                print(f'  [买入] {row["fund_code"]} @{price:.3f}')
            except Exception as e:
                print(f'  [买入失败] {row["fund_code"]}: {e}')

    def get_scoreboard(self) -> pd.DataFrame:
        if self.score_df is None:
            self.generate_signals()
        cols = ['fund_code', 'fund_name', 'price', 'pct_change',
                'amount', 'trend_score', 'trend_rank']
        available = [c for c in cols if c in self.score_df.columns]
        return self.score_df[available].head(20).reset_index(drop=True)


def run_etf_trend(api=None, dry_run: bool = True, **kwargs):
    strategy = ETFTrendStrategy(api=api, **kwargs)
    strategy.run(dry_run=dry_run)
    return strategy
