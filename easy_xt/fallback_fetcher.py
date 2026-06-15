"""
多级数据源降级获取器
====================

当主数据源不可用时，自动按优先级尝试备用数据源，实现数据获取的高可用性。

降级链优先级 (从快到慢 / 从主到备):
  第1级: QMT xtdata 本地数据 — 最快、功能最完整、支持全部周期和复权方式
  第2级: 东方财富 HTTP API  — 免费、无需 QMT、全网可达
  第3级: TDX pytdx 服务器   — 免费、TCP 协议、中等速度
  第4级: 保底兜底模式       — 返回空数据或部分数据，不抛异常

设计原则:
  - 每级失败自动尝试下一级，对调用方完全透明
  - 结果中标记数据来源 (source 列)，便于事后审计
  - 可配置各数据源的超时和重试次数
  - 支持结果缓存，避免重复降级消耗

使用方式:
    from easy_xt.fallback_fetcher import FallbackFetcher

    fetcher = FallbackFetcher(qmt_api=api, tdx_available=True)
    df = fetcher.fetch(
        codes=['000001.SZ', '600000.SH'],
        start='20240101',
        end='20240601',
        period='1d'
    )
    # df 中包含 'source' 列，标记实际使用的数据源
"""

import pandas as pd
import numpy as np
from typing import Union, List, Optional, Dict, Any, Tuple, Callable
from datetime import datetime, timedelta
import time
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 数据源级别常量
# ============================================================================

class SourceLevel:
    """数据源优先级常量（值越小越优先）"""
    QMT = 0         # QMT 本地数据（最快、功能最全、EasyXT 主数据源）
    EASTMONEY = 1   # 东方财富 HTTP（免费、无需本地环境）
    TDX = 2         # TDX 通达信（TCP 行情服务器）
    BACKUP = 3      # 保底兜底（空数据 / 部分数据）

    _NAMES = {
        0: 'QMT',
        1: 'EASTMONEY',
        2: 'TDX',
        3: 'BACKUP',
    }

    @classmethod
    def name(cls, level: int) -> str:
        return cls._NAMES.get(level, f'LEVEL_{level}')


# ============================================================================
# 单只股票 K 线的 EastMoney HTTP 获取器（不依赖任何第三方库）
# ============================================================================

class EastMoneyKlineFetcher:
    """
    通过东方财富公开 HTTP API 获取个股 K 线数据。

    特点:
      - 零依赖：只用 requests + pandas
      - 免费：无需任何 token 或注册
      - 覆盖：沪深北全部 A 股 + 指数
      - 周期：1/5/15/30/60 分钟、日/周/月/季/年

    注意:
      - 单次请求最多返回约 1000 条数据
      - 请求频率不宜过高（建议 200ms 以上间隔）
    """

    BASE_URL = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'

    # 周期映射: EasyXT period → EastMoney klt 参数
    PERIOD_MAP = {
        '1m': '1',    '1min': '1',
        '5m': '5',    '5min': '5',
        '15m': '15',  '15min': '15',
        '30m': '30',  '30min': '30',
        '60m': '60',  '60min': '60',  '1h': '60',
        '1d': '101',  'day': '101',   'daily': '101',
        '1w': '102',  'week': '102',  'weekly': '102',
        '1M': '103',  'month': '103', 'monthly': '103',
        '1q': '104',  'quarter': '104',
        '1y': '105',  'year': '105',
    }

    def __init__(self, timeout: float = 15.0, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = None
        self._last_request_time = 0
        self._min_interval = 0.2  # 200ms 最小请求间隔

    def _get_session(self):
        """懒加载 requests session"""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Referer': 'https://quote.eastmoney.com/',
            })
        return self._session

    def _rate_limit(self):
        """请求频率控制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _resolve_secid(self, code: str) -> str:
        """
        将股票代码转换为东方财富 secid 格式。

        Examples:
            '000001.SZ' → '0.000001'
            '600000.SH' → '1.600000'
            '000001'    → '0.000001'  (默认深圳)
        """
        clean = code.replace('.SZ', '').replace('.SH', '').replace('.BJ', '')
        if '.' in clean:
            clean = clean.split('.')[0]

        if clean.startswith(('60', '68')):
            return f'1.{clean}'  # 上海
        elif clean.startswith(('8', '4')):
            return f'0.{clean}'  # 北京（使用深圳市场 ID）
        else:
            return f'0.{clean}'  # 深圳

    def _parse_kline_response(self, raw_data: dict, code: str) -> pd.DataFrame:
        """
        解析东方财富 K 线接口返回的 JSON 数据。

        原始格式: "2024-01-02,10.50,10.80,10.40,10.70,1500000,16000000.0,1.92,0.5,0.3"
        字段顺序: 日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
        """
        if not raw_data or 'data' not in raw_data:
            return pd.DataFrame()

        data = raw_data['data']
        if not data or 'klines' not in data or not data['klines']:
            return pd.DataFrame()

        klines = data['klines']
        rows = []
        for line in klines:
            parts = line.split(',')
            if len(parts) < 7:
                continue
            rows.append({
                'date': parts[0],
                'open': float(parts[1]) if parts[1] != '-' else np.nan,
                'close': float(parts[2]) if parts[2] != '-' else np.nan,
                'high': float(parts[3]) if parts[3] != '-' else np.nan,
                'low': float(parts[4]) if parts[4] != '-' else np.nan,
                'volume': float(parts[5]) if parts[5] != '-' else 0.0,
                'amount': float(parts[6]) if parts[6] != '-' else 0.0,
                'amplitude': float(parts[7]) if len(parts) > 7 and parts[7] != '-' else np.nan,
                'pct_change': float(parts[8]) if len(parts) > 8 and parts[8] != '-' else np.nan,
                'change': float(parts[9]) if len(parts) > 9 and parts[9] != '-' else np.nan,
                'turnover': float(parts[10]) if len(parts) > 10 and parts[10] != '-' else np.nan,
            })

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        df['code'] = code
        df['source'] = 'EASTMONEY'
        return df

    def fetch_single(self, code: str, period: str = '1d',
                     start: str = '', end: str = '',
                     count: int = 0) -> pd.DataFrame:
        """
        获取单只股票的 K 线数据。

        Args:
            code: 股票代码 ('000001.SZ' 或 '000001')
            period: 周期 ('1d', '1m', '5m', '1w' 等)
            start: 起始日期 (YYYYMMDD)
            end: 结束日期 (YYYYMMDD)
            count: 获取最近 N 条（与 start/end 互斥）

        Returns:
            DataFrame，列含 date/open/high/low/close/volume/amount/source
        """
        import requests as req_lib

        secid = self._resolve_secid(code)
        klt = self.PERIOD_MAP.get(period, '101')

        # 确定 limit
        if count > 0:
            limit = count
        elif start:
            limit = 1000  # 日期范围模式
        else:
            limit = 100   # 默认最近 100 条

        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': klt,
            'fqt': '1',  # 前复权
            'beg': start if start else '0',
            'end': end if end else '20500101',
            'lmt': str(limit),
        }

        for attempt in range(self.max_retries + 1):
            try:
                self._rate_limit()
                session = self._get_session()
                resp = session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self.timeout,
                    allow_redirects=True,
                )

                if resp.status_code != 200:
                    if attempt < self.max_retries:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    logger.warning(f"EastMoney HTTP {resp.status_code} for {code}")
                    return pd.DataFrame()

                raw = resp.json()
                # 检查返回码
                if raw.get('rc') != 0 or raw.get('data') is None:
                    if attempt < self.max_retries:
                        time.sleep(1.0)
                        continue
                    return pd.DataFrame()

                df = self._parse_kline_response(raw, code)
                if df.empty and attempt < self.max_retries:
                    time.sleep(1.0)
                    continue
                return df

            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                logger.debug(f"EastMoney fetch failed for {code}: {e}")
                return pd.DataFrame()

        return pd.DataFrame()

    def fetch_batch(self, codes: List[str], period: str = '1d',
                    start: str = '', end: str = '',
                    count: int = 0) -> pd.DataFrame:
        """
        批量获取多只股票的 K 线数据（逐只请求并合并）。

        Args:
            codes: 股票代码列表
            period: 周期
            start: 起始日期
            end: 结束日期
            count: 获取数量

        Returns:
            DataFrame，含 code 列用于区分不同股票
        """
        all_frames = []
        for i, code in enumerate(codes):
            if i > 0:
                # 批量请求间隔控制
                time.sleep(self._min_interval)
            df = self.fetch_single(code, period, start, end, count)
            if not df.empty:
                all_frames.append(df)

        if not all_frames:
            return pd.DataFrame()

        result = pd.concat(all_frames, ignore_index=True)
        return result


# ============================================================================
# 多级降级获取器
# ============================================================================

class FallbackFetcher:
    """
    多级数据源降级获取器。

    按优先级依次尝试各数据源获取 K 线数据，任一成功即返回。
    结果中包含 'source' 列标明实际数据来源。

    使用示例:
        fetcher = FallbackFetcher(
            qmt_api=your_data_api,
            tdx_provider=your_tdx_provider,
        )
        df = fetcher.fetch(
            codes=['000001.SZ'],
            start='20240101',
            end='20240601',
            period='1d'
        )
        print(f"数据来源: {df['source'].iloc[0]}")
    """

    def __init__(self,
                 qmt_api=None,
                 tdx_provider=None,
                 eastmoney_fetcher: Optional[EastMoneyKlineFetcher] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Args:
            qmt_api: DataAPI 实例或具有 get_price 方法的对象（可选）
            tdx_provider: TdxDataProvider 实例（可选）
            eastmoney_fetcher: EastMoneyKlineFetcher 实例（可选，默认自动创建）
            config: 配置字典
                - timeout_per_level: dict, 每级超时秒数
                - retry_per_level: dict, 每级重试次数
                - skip_levels: list, 跳过的数据源级别
                - cache_ttl: int, 结果缓存秒数（0 表示不缓存）
        """
        self.qmt_api = qmt_api
        self.tdx_provider = tdx_provider
        self.eastmoney_fetcher = eastmoney_fetcher or EastMoneyKlineFetcher()
        self.config = config or {}

        # 超时配置
        self._timeouts = self.config.get('timeout_per_level', {
            SourceLevel.EASTMONEY: 15.0,
            SourceLevel.QMT: 30.0,
            SourceLevel.TDX: 10.0,
        })

        # 重试配置
        self._retries = self.config.get('retry_per_level', {
            SourceLevel.EASTMONEY: 2,
            SourceLevel.QMT: 3,
            SourceLevel.TDX: 1,
        })

        # 要跳过的数据源
        self._skip_levels = set(self.config.get('skip_levels', []))

        # 统计信息
        self.stats = {
            'total_calls': 0,
            'success_by_source': {},
            'fail_count': 0,
            'avg_latency_ms': 0,
        }

    def _should_try(self, level: int) -> bool:
        """检查某级数据源是否应该尝试"""
        if level in self._skip_levels:
            return False
        if level == SourceLevel.QMT and self.qmt_api is None:
            return False
        if level == SourceLevel.TDX and self.tdx_provider is None:
            return False
        return True

    def _mark_success(self, source_name: str, latency_ms: float):
        """记录成功统计"""
        self.stats['total_calls'] += 1
        self.stats['success_by_source'][source_name] = (
            self.stats['success_by_source'].get(source_name, 0) + 1
        )
        # 滑动平均延迟
        prev_avg = self.stats['avg_latency_ms']
        n = self.stats['total_calls']
        self.stats['avg_latency_ms'] = prev_avg + (latency_ms - prev_avg) / max(n, 1)

    def _mark_fail(self):
        """记录失败统计"""
        self.stats['fail_count'] += 1

    # ---- 第 1 级: 东方财富 HTTP API ----

    def _try_eastmoney(self, codes: List[str], start: str, end: str,
                       period: str, count: int, fields: List[str]) -> Optional[pd.DataFrame]:
        """
        通过东方财富公开 HTTP API 获取 K 线数据。

        优势: 免费、无需本地环境、覆盖全市场
        劣势: 单次 1000 条上限、需网络、无 Level2
        """
        if not self._should_try(SourceLevel.EASTMONEY):
            return None

        logger.info(f"[Fallback] Level 1: Trying EastMoney HTTP API...")
        t0 = time.time()

        try:
            df = self.eastmoney_fetcher.fetch_batch(
                codes=codes, period=period, start=start, end=end, count=count
            )
            if df is not None and not df.empty:
                elapsed = (time.time() - t0) * 1000
                self._mark_success('EASTMONEY', elapsed)
                logger.info(f"[Fallback] EastMoney OK ({len(df)} rows, {elapsed:.0f}ms)")
                return df
        except Exception as e:
            logger.debug(f"[Fallback] EastMoney failed: {e}")

        return None

    # ---- 第 2 级: QMT xtdata ----

    def _try_qmt(self, codes: List[str], start: str, end: str,
                 period: str, count: int, fields: List[str], adjust: str) -> Optional[pd.DataFrame]:
        """
        通过 QMT xtdata 获取数据。

        优势: 本地数据最快、支持所有周期和复权方式
        劣势: 必须启动 QMT/miniQMT 客户端
        """
        if not self._should_try(SourceLevel.QMT):
            return None

        logger.info(f"[Fallback] Level 2: Trying QMT xtdata...")
        t0 = time.time()

        for attempt in range(self._retries.get(SourceLevel.QMT, 3)):
            try:
                # 尝试使用 DataAPI 的 get_price 方法
                if hasattr(self.qmt_api, 'get_price'):
                    df = self.qmt_api.get_price(
                        codes=codes, start=start, end=end,
                        period=period, count=count if count > 0 else None,
                        fields=fields, adjust=adjust
                    )
                elif hasattr(self.qmt_api, 'get_market_data_ex'):
                    # 裸 xtdata 接口
                    df = self.qmt_api.get_market_data_ex(
                        stock_list=codes,
                        period=period,
                        start_time=start,
                        end_time=end,
                        field_list=fields
                    )
                    if isinstance(df, dict):
                        # 转换为 DataFrame
                        frames = []
                        for code, data in df.items():
                            if data is not None and len(data) > 0:
                                f = pd.DataFrame(data)
                                f['code'] = code
                                frames.append(f)
                        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
                else:
                    logger.debug(f"[Fallback] QMT API has no usable method")
                    return None

                if df is not None and not df.empty:
                    elapsed = (time.time() - t0) * 1000
                    self._mark_success('QMT', elapsed)
                    logger.info(f"[Fallback] QMT OK ({len(df)} rows, {elapsed:.0f}ms)")
                    # 添加 source 标记（如果还没有）
                    if 'source' not in df.columns:
                        df['source'] = 'QMT'
                    return df

                # 空结果也视为失败，重试
                if attempt < self._retries.get(SourceLevel.QMT, 3) - 1:
                    time.sleep(1.0 * (attempt + 1))

            except Exception as e:
                logger.debug(f"[Fallback] QMT attempt {attempt + 1} failed: {e}")
                if attempt < self._retries.get(SourceLevel.QMT, 3) - 1:
                    time.sleep(1.0 * (attempt + 1))

        return None

    # ---- 第 3 级: TDX pytdx ----

    def _try_tdx(self, codes: List[str], start: str, end: str,
                 period: str, count: int) -> Optional[pd.DataFrame]:
        """
        通过 TDX (通达信) pytdx TCP 行情服务器获取数据。

        优势: 免费、无需本地环境、多服务器自动切换
        劣势: 仅日线数据可靠、分钟线有限、速度中等
        """
        if not self._should_try(SourceLevel.TDX):
            return None

        # TDX 仅支持日线及更长周期
        supported_tdx_periods = {'1d', '1w', '1M', 'day', 'week', 'month', 'daily', 'weekly', 'monthly'}
        if period not in supported_tdx_periods:
            logger.debug(f"[Fallback] TDX does not support period: {period}")
            return None

        logger.info(f"[Fallback] Level 3: Trying TDX pytdx...")
        t0 = time.time()

        try:
            if not self.tdx_provider or not hasattr(self.tdx_provider, 'get_kline_data'):
                return None

            if not self.tdx_provider.is_connected():
                self.tdx_provider.connect()

            all_frames = []
            for code in codes:
                try:
                    kline_data = self.tdx_provider.get_kline_data(
                        code, period='D' if period in ('1d', 'day', 'daily') else period,
                        start_date=start, end_date=end, count=count
                    )

                    if kline_data and len(kline_data) > 0:
                        df = pd.DataFrame(kline_data)
                        df['code'] = code
                        all_frames.append(df)

                except Exception as e:
                    logger.debug(f"[Fallback] TDX failed for {code}: {e}")
                    continue

            if all_frames:
                df = pd.concat(all_frames, ignore_index=True)
                elapsed = (time.time() - t0) * 1000
                self._mark_success('TDX', elapsed)
                logger.info(f"[Fallback] TDX OK ({len(df)} rows, {elapsed:.0f}ms)")
                df['source'] = 'TDX'
                return df

        except Exception as e:
            logger.debug(f"[Fallback] TDX failed: {e}")

        return None

    # ---- 第 4 级: 保底兜底 ----

    def _try_backup(self, codes: List[str], start: str, end: str,
                    period: str) -> pd.DataFrame:
        """
        保底兜底：所有数据源都失败时，返回空 DataFrame 并记录错误。

        不抛异常，返回带 source='BACKUP_FAILED' 的空 DataFrame。
        调用方可通过检查 df.empty 或 source 列来判断是否失败。
        """
        self._mark_fail()
        logger.error(
            f"[Fallback] ALL SOURCES FAILED for {len(codes)} codes, "
            f"period={period}, {start}~{end}"
        )
        return pd.DataFrame({'source': ['BACKUP_FAILED']})

    # ---- 主入口 ----

    def fetch(self,
              codes: Union[str, List[str]],
              start: str = '',
              end: str = '',
              period: str = '1d',
              count: int = 0,
              fields: Optional[List[str]] = None,
              adjust: str = 'front') -> pd.DataFrame:
        """
        多级降级获取 K 线数据。

        按优先级依次尝试: EastMoney → QMT → TDX → 兜底返回空数据。
        任一数据源成功即返回，结果包含 'source' 列标示来源。

        Args:
            codes: 股票代码或列表
            start: 起始日期 (YYYYMMDD 或 YYYY-MM-DD)
            end: 结束日期
            period: 数据周期 ('1d', '1m', '5m', '1w' 等)
            count: 获取数量（与 start/end 互斥）
            fields: 需要的字段列表
            adjust: 复权类型 (仅 QMT 支持)

        Returns:
            DataFrame，列含 date/open/high/low/close/volume/amount/source。

            所有数据源均失败时返回含 source='BACKUP_FAILED' 的空 DataFrame。
            调用方应检查 df.empty 或 df['source'].iloc[0] 来判断数据可用性。
        """
        # 标准化参数
        if isinstance(codes, str):
            codes = [codes]
        codes = [c.strip() for c in codes if c and c.strip()]
        if not codes:
            return pd.DataFrame()

        start = str(start).replace('-', '') if start else ''
        end = str(end).replace('-', '') if end else ''

        if fields is None:
            fields = ['open', 'high', 'low', 'close', 'volume', 'amount']

        total_t0 = time.time()

        # ---- 第 1 级: QMT（主数据源，最快最全） ----
        result = self._try_qmt(codes, start, end, period, count, fields, adjust)
        if result is not None and not result.empty:
            return result

        # ---- 第 2 级: 东方财富 HTTP（免费备用） ----
        result = self._try_eastmoney(codes, start, end, period, count, fields)
        if result is not None and not result.empty:
            return result

        # ---- 第 3 级: TDX pytdx（TCP 行情备用） ----
        result = self._try_tdx(codes, start, end, period, count)
        if result is not None and not result.empty:
            return result

        # ---- 第 4 级: 兜底 ----
        return self._try_backup(codes, start, end, period)

    def get_stats(self) -> Dict[str, Any]:
        """获取降级获取器的运行统计信息"""
        return {
            **self.stats,
            'skip_levels': [SourceLevel.name(l) for l in self._skip_levels],
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_calls': 0,
            'success_by_source': {},
            'fail_count': 0,
            'avg_latency_ms': 0,
        }


# ============================================================================
# 便捷函数
# ============================================================================

def create_fallback_fetcher(qmt_data_api=None,
                            tdx_provider=None,
                            **config) -> FallbackFetcher:
    """
    快速创建降级获取器。

    自动检测可用的数据源，配置合理的超时和重试参数。

    Args:
        qmt_data_api: DataAPI 实例（可选）
        tdx_provider: TdxDataProvider 实例（可选）
        **config: 额外配置参数

    Returns:
        配置好的 FallbackFetcher 实例

    Example:
        from easy_xt import get_api
        api = get_api()
        fetcher = create_fallback_fetcher(qmt_data_api=api.data)
        df = fetcher.fetch(['000001.SZ'], start='20240101', period='1d')
    """
    # 如果没有传入 TDX provider，尝试自动导入
    if tdx_provider is None:
        try:
            from easy_xt.realtime_data.providers.tdx_provider import TdxDataProvider
            tdx_provider = TdxDataProvider()
        except ImportError:
            pass

    return FallbackFetcher(
        qmt_api=qmt_data_api,
        tdx_provider=tdx_provider,
        config=config,
    )
