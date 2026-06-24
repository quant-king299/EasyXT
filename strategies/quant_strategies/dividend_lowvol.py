import logging

logger = logging.getLogger(__name__)
"""
红利低波策略
============

经典 Smart Beta 策略：优选高股息 + 低波动股票，定期轮动。

策略逻辑:
  1. 从全市场筛选股息率 > min_yield 的股票
  2. 计算 60 日波动率，排除波动过高的
  3. 综合打分 = 股息率排名 × w1 + 波动率排名(逆向) × w2
  4. 选择得分最高的前 buy_n 只
  5. 卖出: 股息率下降或波动率飙升

数据源: DuckDB (stock_daily + dividend_data)

使用方式:
  python strategies/quant_strategies/run_dividend_lowvol.py
  python strategies/quant_strategies/run_dividend_lowvol.py --trade
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Dict, List


def get_dividend_data() -> pd.DataFrame:
    """从 DuckDB 读取分红数据"""
    try:
        import duckdb
        con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)
        df = con.execute("""
            SELECT ts_code as code, cash_div,
                   stk_div, record_date, ex_date
            FROM dividend_data
            WHERE cash_div > 0
            ORDER BY ex_date DESC
        """).fetchdf()
        con.close()
        return df
    except Exception:
        return pd.DataFrame()


def calc_dividend_yield(div_df: pd.DataFrame, stock_price_map: Dict[str, float]) -> pd.DataFrame:
    """
    计算股息率 = 最近年度每股分红 / 当前股价

    Args:
        div_df: 分红数据
        stock_price_map: {code: current_price}

    Returns:
        DataFrame with code, dividend_yield
    """
    if div_df.empty:
        return pd.DataFrame(columns=['code', 'dividend_yield'])

    # 取每只股票最近一年的分红
    latest_div = div_df.sort_values('ex_date').groupby('code').last().reset_index()

    results = []
    for _, row in latest_div.iterrows():
        code = row['code']
        price = stock_price_map.get(code, 0)
        if price <= 0:
            continue
        cash_div = float(row.get('cash_div', 0) or 0)
        if cash_div <= 0:
            continue
        yld = cash_div / price * 100  # 股息率 %
        if yld > 0:
            results.append({'code': code, 'dividend_yield': round(yld, 2),
                           'cash_div': cash_div, 'ex_date': row.get('ex_date', '')})

    return pd.DataFrame(results)


def calc_volatility(code_list: List[str], period: int = 60) -> Dict[str, float]:
    """计算年化波动率，优先 DuckDB，降级 QMT"""
    vol_map = {}
    try:
        import duckdb
        con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)
        for code in code_list:
            try:
                rows = con.execute("""
                    SELECT close FROM stock_daily
                    WHERE stock_code = ? AND close > 0
                    ORDER BY date DESC LIMIT ?
                """, [code, period]).fetchall()
                if rows and len(rows) >= 20:
                    closes = np.array([r[0] for r in rows[::-1]])
                    returns = np.diff(np.log(closes))
                    vol = np.std(returns) * np.sqrt(252) * 100  # 年化波动率 %
                    vol_map[code] = round(vol, 2)
            except Exception:
                pass
        con.close()
    except Exception:
        pass
    return vol_map


def get_stock_prices_from_duckdb() -> Dict[str, float]:
    """从 DuckDB 获取全市场最新收盘价"""
    try:
        import duckdb
        con = duckdb.connect('D:/StockData/stock_data.ddb', read_only=True)
        latest = con.execute("SELECT MAX(date) FROM stock_daily").fetchone()[0]
        rows = con.execute(f"""
            SELECT stock_code, close FROM stock_daily
            WHERE date = '{latest}' AND close > 0
        """).fetchall()
        con.close()
        return {r[0]: r[1] for r in rows}
    except Exception:
        return {}


class DividendLowVolStrategy:
    """
    红利低波轮动策略。

    参数:
      buy_n        : 持有数量
      min_yield    : 最低股息率(%)
      max_vol      : 最大年化波动率(%)
      yield_w      : 股息率权重
      vol_w        : 波动率权重(逆向)
      min_mkt_cap  : 最低市值(亿)
    """

    def __init__(self, api=None, account_id=None, **kwargs):
        self.api = api
        self.account_id = account_id
        self.buy_n = kwargs.get('buy_n', 20)
        self.min_yield = kwargs.get('min_yield', 2.0)
        self.max_vol = kwargs.get('max_vol', 50.0)
        self.yield_w = kwargs.get('yield_w', 1.0)
        self.vol_w = kwargs.get('vol_w', 0.5)
        self.min_mkt_cap = kwargs.get('min_mkt_cap', 50)

        self.score_df = None
        self.positions = None
        self.buy_list = None
        self.sell_list = None

    def generate_signals(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        logger.info('[*] 获取股价数据...')
        price_map = get_stock_prices_from_duckdb()
        logger.info(f'    全市场 {len(price_map)} 只股票')

        logger.info('[*] 获取分红数据...')
        div_df = get_dividend_data()
        if div_df.empty:
            logger.info('[警告] 无分红数据，请先在 GUI 下载 Tushare 分红数据')
            return pd.DataFrame(), pd.DataFrame()

        logger.info('[*] 计算股息率...')
        yield_df = calc_dividend_yield(div_df, price_map)
        yield_df = yield_df[yield_df['dividend_yield'] >= self.min_yield]
        logger.info(f'    股息率 >= {self.min_yield}%: {len(yield_df)} 只')

        logger.info('[*] 计算波动率...')
        code_list = yield_df['code'].tolist()
        vol_map = calc_volatility(code_list)
        yield_df['volatility'] = yield_df['code'].map(vol_map)
        yield_df['volatility'] = yield_df['volatility'].fillna(99)

        # 过滤高波动
        pool = yield_df[yield_df['volatility'] <= self.max_vol].copy()
        logger.info(f'    波动率 <= {self.max_vol}%: {len(pool)} 只')

        if pool.empty:
            return pd.DataFrame(), pd.DataFrame()

        # 排名打分
        pool['yield_rank'] = pool['dividend_yield'].rank(ascending=False)
        pool['vol_rank'] = pool['volatility'].rank(ascending=True)  # 低波动排名靠前
        pool['score'] = pool['yield_rank'] * self.yield_w + pool['vol_rank'] * self.vol_w
        pool = pool.sort_values('score')
        pool['final_rank'] = range(1, len(pool) + 1)

        # 持仓
        self.positions = self._get_positions()
        held_codes = set(self.positions['code'].tolist()) if len(self.positions) > 0 else set()
        current_count = len(held_codes)

        # 买入
        buy_list = []
        for _, row in pool.iterrows():
            if row['code'] not in held_codes and current_count < self.buy_n:
                buy_list.append({
                    'code': row['code'],
                    'price': price_map.get(row['code'], 0),
                    'dividend_yield': row['dividend_yield'],
                    'volatility': row['volatility'],
                    'score': round(row['score'], 1),
                })
                current_count += 1
            if current_count >= self.buy_n:
                break

        # 卖出
        sell_list = []
        top_ranks = pool.head(self.buy_n * 2)
        for _, pos in self.positions.iterrows():
            code = pos['code']
            if code not in top_ranks['code'].values:
                price = float(pos.get('open_price', 0) or price_map.get(code, 0))
                sell_list.append({'code': code, 'price': price, 'reason': '跌出排名'})

        self.buy_list = pd.DataFrame(buy_list) if buy_list else pd.DataFrame()
        self.sell_list = pd.DataFrame(sell_list) if sell_list else pd.DataFrame()
        self.score_df = pool
        return self.buy_list, self.sell_list

    def run(self, dry_run: bool = True):
        logger.info(f'\n{"="*60}')
        logger.info(f'[红利低波策略] {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        logger.info(f'{"="*60}')

        buy_list, sell_list = self.generate_signals()

        logger.info(f'\n--- 持仓 ({len(self.positions) if self.positions is not None else 0} 只) ---')
        if self.positions is not None and len(self.positions) > 0:
            logger.info(self.positions.head(10).to_string(index=False))

        logger.info(f'\n--- 卖出信号 ({len(sell_list)} 只) ---')
        if len(sell_list) > 0:
            logger.info(sell_list.to_string(index=False))
        else:
            logger.info('  无')

        logger.info(f'\n--- 买入信号 (前 {self.buy_n}) ---')
        if len(buy_list) > 0:
            logger.info(buy_list.to_string(index=False))
        else:
            logger.info('  无')

        if not dry_run:
            self._execute_orders(buy_list, sell_list)

    def _get_positions(self) -> pd.DataFrame:
        if not self.account_id or not self.api:
            return pd.DataFrame()
        try:
            if not hasattr(self.api, 'trade') or self.api.trade is None:
                return pd.DataFrame()
            df = self.api.trade.get_positions(self.account_id)
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def _execute_orders(self, buy_list, sell_list):
        from .data_utils import round_price, get_safe_sell_volume

        if not self.account_id or not hasattr(self.api, 'trade') or self.api.trade is None:
            logger.info('[提示] 交易服务未初始化')
            return
        acc = self.account_id
        positions = self.positions if hasattr(self, 'positions') and self.positions is not None else pd.DataFrame()

        for _, row in sell_list.iterrows():
            try:
                vol = get_safe_sell_volume(positions, row['code'], 100)
                price = round_price(row['code'], row.get('price', 0))
                self.api.trade.sell(account_id=acc, code=row['code'],
                                   volume=vol, price=price, price_type='limit')
                logger.info(f'  [卖出] {row["code"]} @{price:.2f} vol={vol}')
            except Exception as e:
                logger.info(f'  [卖出失败] {row["code"]}: {e}')

        for _, row in buy_list.iterrows():
            try:
                price = round_price(row['code'], row.get('price', 0))
                if price <= 0:
                    logger.info(f'  [买入跳过] {row["code"]}: 价格无效 ({price})')
                    continue
                self.api.trade.buy(account_id=acc, code=row['code'],
                                  volume=100, price=price, price_type='limit')
                logger.info(f'  [买入] {row["code"]} @{price:.2f}')
            except Exception as e:
                logger.info(f'  [买入失败] {row["code"]}: {e}')
