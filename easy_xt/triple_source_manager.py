"""
三数据源混合管理器

智能整合 QMT、akshare、qstock 三大数据源

数据源策略：
1. QMT/xtdata - 行情、板块（最快、最稳定）
2. akshare - 财务、资金流向、龙虎榜（最全面）
3. qstock - 补充数据源（轻量、快速）

主要功能：
1. 自动检测三数据源可用性
2. 智能选择最佳数据源
3. 自动降级（QMT → qstock → akshare）
4. 统一缓存管理
5. 性能监控
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from functools import wraps
import time


def cache_result(ttl_seconds=3600):
    """数据缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}_{args}_{kwargs}"

            # 检查缓存
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if time.time() - cached_time < ttl_seconds:
                    return cached_data

            # 获取数据
            result = func(self, *args, **kwargs)

            # 缓存数据
            if result is not None and not (isinstance(result, pd.DataFrame) and result.empty):
                self.cache[cache_key] = (result, time.time())

            return result
        return wrapper
    return decorator


class TripleSourceDataManager:
    """三数据源混合管理器"""

    def __init__(self, priority='qmt,qstock,akshare'):
        """
        初始化三数据源管理器

        Args:
            priority: 数据源优先级，用逗号分隔
                    默认: 'qmt,qstock,akshare'
        """
        self.priority = priority.split(',')
        self.cache = {}
        self.stats = {
            'qmt_hits': 0,
            'qstock_hits': 0,
            'akshare_hits': 0,
            'failures': 0
        }

        # 检测数据源可用性
        self.sources = {
            'qmt': self._check_qmt(),
            'qstock': self._check_qstock(),
            'akshare': self._check_akshare()
        }

        # 初始化客户端
        self._init_clients()

        print("=" * 70)
        print("三数据源管理器初始化")
        print("=" * 70)
        for source, available in self.sources.items():
            status = "OK" if available else "N/A"
            print(f"  {source:12s} : {status}")
        print(f"  优先级       : {' → '.join(self.priority)}")
        print("=" * 70)

    def _check_qmt(self) -> bool:
        """检查QMT是否可用"""
        try:
            import xtdata
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def _check_qstock(self) -> bool:
        """检查qstock是否可用"""
        try:
            import qstock as qs
            # 测试基本接口
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def _check_akshare(self) -> bool:
        """检查akshare是否可用"""
        try:
            import akshare as ak
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def _init_clients(self):
        """初始化所有客户端"""
        self.xt = None
        self.qs = None
        self.ak = None
        self.tdx_client = None

        # QMT
        if self.sources['qmt']:
            try:
                import xtdata
                self.xt = xtdata
                self.xt.connect()
            except Exception as e:
                print(f"[WARNING] QMT初始化失败: {e}")
                self.sources['qmt'] = False

        # qstock
        if self.sources['qstock']:
            try:
                import qstock as qs
                self.qs = qs
            except Exception as e:
                print(f"[WARNING] qstock初始化失败: {e}")
                self.sources['qstock'] = False

        # akshare
        if self.sources['akshare']:
            try:
                import akshare as ak
                self.ak = ak
            except Exception as e:
                print(f"[WARNING] akshare初始化失败: {e}")
                self.sources['akshare'] = False

        # tdx_client (行情数据)
        if self.sources['qmt']:
            try:
                from tdx_client import TdxClient
                self.tdx_client = TdxClient
            except Exception:
                pass

    # ============================================================
    # 行情数据 - QMT > qstock > akshare
    # ============================================================

    @cache_result(ttl_seconds=60)
    def get_market_data(self,
                       stock_codes: Union[str, List[str]],
                       start_time: str,
                       end_time: str,
                       period: str = '1d') -> pd.DataFrame:
        """
        获取行情数据

        优先级: QMT > qstock > akshare

        Args:
            stock_codes: 股票代码
            start_time: 开始时间
            end_time: 结束时间
            period: 周期

        Returns:
            pd.DataFrame: 行情数据
        """
        # 尝试QMT
        if self.sources['qmt'] and 'qmt' in self.priority:
            try:
                if self.tdx_client:
                    with self.tdx_client() as tdx:
                        codes = stock_codes if isinstance(stock_codes, list) else [stock_codes]
                        df = tdx.get_market_data(
                            stock_list=codes,
                            start_time=start_time,
                            end_time=end_time,
                            period=period
                        )
                        if not df.empty:
                            self.stats['qmt_hits'] += 1
                            return df
            except Exception as e:
                print(f"[INFO] QMT获取行情失败: {e}")

        # 尝试qstock
        if self.sources['qstock'] and 'qstock' in self.priority:
            try:
                if isinstance(stock_codes, str):
                    code = stock_codes.split('.')[0]
                    df = self.qs.get_data(code, start=start_time, end=end_time)
                    if df is not None and not df.empty:
                        df['stock_code'] = stock_codes
                        self.stats['qstock_hits'] += 1
                        return df
            except Exception as e:
                print(f"[INFO] qstock获取行情失败: {e}")

        # 尝试akshare
        if self.sources['akshare'] and 'akshare' in self.priority:
            try:
                df = self._get_market_from_akshare(stock_codes, start_time, end_time, period)
                if not df.empty:
                    self.stats['akshare_hits'] += 1
                    return df
            except Exception as e:
                print(f"[INFO] akshare获取行情失败: {e}")

        self.stats['failures'] += 1
        return pd.DataFrame()

    def _get_market_from_akshare(self,
                                 stock_codes,
                                 start_time,
                                 end_time,
                                 period) -> pd.DataFrame:
        """从akshare获取行情"""
        # 简化实现，需要根据实际情况调整
        return pd.DataFrame()

    # ============================================================
    # 板块数据 - QMT > qstock > akshare
    # ============================================================

    @cache_result(ttl_seconds=3600)
    def get_sector_list(self) -> Dict[str, List[str]]:
        """
        获取板块列表

        优先级: QMT > qstock > akshare

        Returns:
            Dict: {'industry': [...], 'concept': [...]}
        """
        result = {'industry': [], 'concept': []}

        # QMT行业板块
        if self.sources['qmt']:
            try:
                sectors = self.xt.get_sector_list()
                if sectors:
                    result['industry'] = sectors
                    self.stats['qmt_hits'] += 1
                    return result
            except Exception:
                pass

        # qstock (如果支持板块)
        if self.sources['qstock']:
            # qstock可能没有直接的板块列表接口
            pass

        # akshare
        if self.sources['akshare']:
            try:
                df = self.ak.stock_board_industry_name_em()
                if not df.empty:
                    result['industry'] = df['板块名称'].tolist()
                    self.stats['akshare_hits'] += 1
                    return result
            except Exception:
                pass

        return result

    @cache_result(ttl_seconds=1800)
    def get_sector_stocks(self,
                         sector_name: str,
                         sector_type: str = 'industry') -> pd.DataFrame:
        """
        获取板块成分股

        优先级: QMT > qstock > akshare

        Args:
            sector_name: 板块名称
            sector_type: 板块类型

        Returns:
            pd.DataFrame: 成分股
        """
        # QMT
        if self.sources['qmt']:
            try:
                stock_list = self.xt.get_stock_list_in_sector(sector_name)
                if stock_list:
                    df = self.get_market_data(stock_list,
                                           datetime.now().strftime('%Y%m%d'),
                                           datetime.now().strftime('%Y%m%d'))
                    self.stats['qmt_hits'] += 1
                    return df
            except Exception:
                pass

        # qstock (指数成分股)
        if self.sources['qstock'] and sector_type == 'index':
            try:
                df = self.qs.index_member(sector_name)
                if df is not None and not df.empty:
                    self.stats['qstock_hits'] += 1
                    return df
            except Exception:
                pass

        # akshare
        if self.sources['akshare']:
            try:
                if sector_type == 'industry':
                    df = self.ak.stock_board_industry_cons_em(symbol=sector_name)
                else:
                    df = self.ak.stock_board_concept_cons_em(symbol=sector_name)

                if not df.empty:
                    df = df.rename(columns={'代码': 'stock_code', '名称': 'stock_name'})
                    self.stats['akshare_hits'] += 1
                    return df
            except Exception:
                pass

        return pd.DataFrame()

    # ============================================================
    # 资金流向 - qstock > akshare
    # ============================================================

    @cache_result(ttl_seconds=600)
    def get_money_flow(self,
                      stock_code: str,
                      days: int = 5) -> pd.DataFrame:
        """
        获取资金流向

        优先级: akshare > qstock

        Args:
            stock_code: 股票代码
            days: 天数

        Returns:
            pd.DataFrame: 资金流向
        """
        # akshare优先（qstock的moneyflow_stock需要付费）
        if self.sources['akshare']:
            try:
                from money_flow import MoneyFlowAnalyzer
                analyzer = MoneyFlowAnalyzer()
                df = analyzer.get_stock_money_flow(stock_code, days)
                if not df.empty:
                    self.stats['akshare_hits'] += 1
                    return df
            except Exception as e:
                print(f"[INFO] akshare获取资金流向失败: {e}")

        # qstock备用
        if self.sources['qstock'] and 'qstock' in self.priority:
            try:
                code = stock_code.split('.')[0]
                # qstock的接口：需要w_list参数
                df = self.qs.moneyflow_stock(code, w_list=[5, 10, 20])
                if df is not None and not df.empty:
                    df['stock_code'] = stock_code
                    self.stats['qstock_hits'] += 1
                    return df
            except Exception as e:
                print(f"[INFO] qstock获取资金流向失败: {e}")

        return pd.DataFrame()

    # ============================================================
    # 龙虎榜 - qstock > akshare
    # ============================================================

    @cache_result(ttl_seconds=43200)  # 12小时
    def get_dragon_tiger(self, date: str = None) -> pd.DataFrame:
        """
        获取龙虎榜

        优先级: qstock > akshare

        Args:
            date: 日期

        Returns:
            pd.DataFrame: 龙虎榜
        """
        # qstock优先
        if self.sources['qstock'] and 'qstock' in self.priority:
            try:
                df = self.qs.stock_billboard()
                if df is not None and not df.empty:
                    self.stats['qstock_hits'] += 1
                    return df
            except Exception as e:
                print(f"[INFO] qstock获取龙虎榜失败: {e}")

        # akshare备用
        if self.sources['akshare']:
            try:
                from dragon_tiger import DragonTigerData
                dt = DragonTigerData()
                df = dt.get_daily_list(date)
                if not df.empty:
                    self.stats['akshare_hits'] += 1
                    return df
            except Exception as e:
                print(f"[INFO] akshare获取龙虎榜失败: {e}")

        return pd.DataFrame()

    # ============================================================
    # 股票指标/基本面 - qstock > akshare > QMT
    # ============================================================

    @cache_result(ttl_seconds=86400)  # 24小时
    def get_stock_indicator(self, stock_code: str) -> pd.DataFrame:
        """
        获取股票指标

        优先级: qstock > akshare > QMT

        Args:
            stock_code: 股票代码

        Returns:
            pd.DataFrame: 股票指标
        """
        # qstock优先
        if self.sources['qstock']:
            try:
                code = stock_code.split('.')[0]
                df = self.qs.stock_indicator(code)
                if df is not None and not df.empty:
                    df['stock_code'] = stock_code
                    self.stats['qstock_hits'] += 1
                    return df
            except Exception:
                pass

        # akshare备用
        if self.sources['akshare']:
            try:
                from factor_library import FactorLibrary
                lib = FactorLibrary()
                df = lib.get_quality_factors([stock_code])
                if not df.empty:
                    self.stats['akshare_hits'] += 1
                    return df
            except Exception:
                pass

        return pd.DataFrame()

    # ============================================================
    # 实时数据 - QMT > qstock
    # ============================================================

    @cache_result(ttl_seconds=10)  # 10秒缓存
    def get_realtime_data(self, stock_codes: Union[str, List[str]] = None) -> pd.DataFrame:
        """
        获取实时行情

        优先级: QMT > qstock

        Args:
            stock_codes: 股票代码，None表示全市场

        Returns:
            pd.DataFrame: 实时行情
        """
        # QMT优先
        if self.sources['qmt']:
            try:
                if stock_codes:
                    if isinstance(stock_codes, str):
                        stock_codes = [stock_codes]
                    df = self.xt.get_market_data_ex(stock_codes, period='tick')
                    if not df.empty:
                        self.stats['qmt_hits'] += 1
                        return df
            except Exception:
                pass

        # qstock备用
        if self.sources['qstock']:
            try:
                df = self.qs.realtime_data()
                if df is not None and not df.empty:
                    if stock_codes:
                        codes = [c.split('.')[0] for c in stock_codes] if isinstance(stock_codes, list) else [stock_codes.split('.')[0]]
                        df = df[df['code'].isin(codes)]
                    self.stats['qstock_hits'] += 1
                    return df
            except Exception:
                pass

        return pd.DataFrame()

    # ============================================================
    # 统计和工具方法
    # ============================================================

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        print("[OK] 缓存已清空")

    def get_stats(self) -> Dict:
        """获取使用统计"""
        total_hits = sum([v for k, v in self.stats.items() if k.endswith('_hits')])

        return {
            'total_requests': total_hits + self.stats['failures'],
            'qmt_hits': self.stats['qmt_hits'],
            'qstock_hits': self.stats['qstock_hits'],
            'akshare_hits': self.stats['akshare_hits'],
            'failures': self.stats['failures'],
            'cache_size': len(self.cache),
            'qmt_ratio': f"{self.stats['qmt_hits']/total_hits*100:.1f}%" if total_hits > 0 else "0%",
            'qstock_ratio': f"{self.stats['qstock_hits']/total_hits*100:.1f}%" if total_hits > 0 else "0%",
            'akshare_ratio': f"{self.stats['akshare_hits']/total_hits*100:.1f}%" if total_hits > 0 else "0%",
        }

    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        print("\n" + "=" * 70)
        print("数据源使用统计")
        print("=" * 70)
        print(f"  总请求数: {stats['total_requests']}")
        print(f"  QMT命中:  {stats['qmt_hits']:6d} ({stats['qmt_ratio']})")
        print(f"  qstock命中: {stats['qstock_hits']:6d} ({stats['qstock_ratio']})")
        print(f"  akshare命中: {stats['akshare_hits']:6d} ({stats['akshare_ratio']})")
        print(f"  失败次数: {stats['failures']:6d}")
        print(f"  缓存项数: {stats['cache_size']}")
        print("=" * 70)


# ============================================================
# 全局单例
# ============================================================
_triple_source_manager = None


def get_triple_source_manager(priority='qmt,qstock,akshare') -> TripleSourceDataManager:
    """
    获取三数据源管理器实例（单例模式）

    Args:
        priority: 数据源优先级

    Returns:
        TripleSourceDataManager: 管理器实例
    """
    global _triple_source_manager

    if _triple_source_manager is None:
        _triple_source_manager = TripleSourceDataManager(priority=priority)

    return _triple_source_manager


if __name__ == "__main__":
    """测试代码"""
    print("=" * 70)
    print("三数据源管理器测试")
    print("=" * 70)

    # 创建管理器
    manager = get_triple_source_manager(priority='qmt,qstock,akshare')

    # 测试1: 获取行情数据
    print("\n[测试1] 获取行情数据...")
    try:
        df = manager.get_market_data(['000001.SZ'], '20240101', '20240131')
        if not df.empty:
            print(f"[OK] 获取到 {len(df)} 条数据")
            print(df.head().to_string())
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试2: 获取板块列表
    print("\n[测试2] 获取板块列表...")
    try:
        sectors = manager.get_sector_list()
        print(f"[OK] 行业板块: {len(sectors['industry'])} 个")
        print(f"  前5个: {sectors['industry'][:5]}")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试3: 获取资金流向
    print("\n[测试3] 获取资金流向...")
    try:
        df = manager.get_money_flow('000001.SZ', days=5)
        if not df.empty:
            print(f"[OK] 获取到 {len(df)} 条数据")
        else:
            print("[FAIL] 数据为空")
    except Exception as e:
        print(f"[ERROR] {e}")

    # 测试4: 打印统计
    print("\n[测试4] 使用统计...")
    try:
        manager.print_stats()
    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)
