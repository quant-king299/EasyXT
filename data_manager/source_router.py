# -*- coding: utf-8 -*-
"""数据源路由：按本机 QMT 实际状态自动选择数据通道。

设计目标（一套菜单，多形态用户）：
    MODE_MINI_QMT   miniQMT/极简版 在线        → xtquant 全功能（历史/列表/财务/实时）
    MODE_BIG_QMT    只有大QMT在运行             → 历史走本地 DAT 导入、列表走 DAT 扫描、
                                                 实时走大QMT行情桥（relay 需运行）、财务提示走 Tushare
    MODE_FALLBACK   两者都没有                  → 明确告知失败原因，列表可走 TDX，历史引导 Tushare

路由只做"决策与探测"，不做数据搬运；导入逻辑见 local_data_manager_widget。
"""
import logging
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from data_manager.qmt_paths import resolve_qmt_paths

logger = logging.getLogger(__name__)


class RouteError(Exception):
    """路由探测或列表获取失败（message 面向用户）。"""


class DataRoute:
    MINI_QMT = 'mini_qmt'
    BIG_QMT = 'big_qmt'
    FALLBACK = 'fallback'


MODE_LABELS = {
    DataRoute.MINI_QMT: 'miniQMT (xtquant)',
    DataRoute.BIG_QMT: '大QMT (本地DAT + 行情桥)',
    DataRoute.FALLBACK: '备用源 (TDX/Tushare)',
}

# ETF/基金代码前缀（与数据管理页历史逻辑保持一致）
ETF_PREFIXES = ('51', '159', '150', '588', '50', '56', '58')

# datadir 扫描无法区分指数/股票（上证综指 000001.SH 与平安银行 000001.SZ 同存），
# 按市场白名单过滤：沪市 000xxx 全是指数，深市 399xxx 全是指数
STOCK_PREFIXES_BY_MARKET = {
    'SH': ('600', '601', '603', '605', '688', '689'),
    'SZ': ('000', '001', '002', '003', '300', '301'),
}
ETF_PREFIXES_BY_MARKET = {
    'SH': ('50', '51', '56', '58'),
    'SZ': ('15', '16', '18'),
}


def is_etf_code(code: str) -> bool:
    """按代码前缀判断是否 ETF/基金（code 形如 510300.SH）。"""
    return code.split('.')[0].startswith(ETF_PREFIXES)


def _filter_datadir_codes(codes: List[str], prefixes_by_market: Dict[str, tuple]) -> List[str]:
    """按市场白名单前缀过滤 datadir 扫描出的代码（剔除指数/其他）。"""
    result = []
    for code in codes:
        pure, _, market = code.partition('.')
        prefixes = prefixes_by_market.get(market)
        if prefixes and pure.startswith(prefixes):
            result.append(code)
    return result


# ────────────────────────── 进程与服务探测 ──────────────────────────

_proc_cache: Dict[str, Tuple[float, bool]] = {}
_PROC_CACHE_TTL = 10.0


def is_process_running(image_name: str, force_refresh: bool = False) -> bool:
    """tasklist 快速探测进程是否运行（带 10 秒缓存）。"""
    now = time.time()
    cached = _proc_cache.get(image_name)
    if cached and not force_refresh and now - cached[0] < _PROC_CACHE_TTL:
        return cached[1]
    running = False
    try:
        # 不用 text=True：tasklist 输出为本地编码(GBK)，UTF-8 模式下会解码失败；
        # 进程名是 ASCII，直接在字节层匹配对任何控制台代码页都成立
        result = subprocess.run(
            ['tasklist', '/FI', f'IMAGENAME eq {image_name}'],
            capture_output=True, timeout=5,
        )
        stdout = bytes(result.stdout or b'') + bytes(result.stderr or b'')
        running = image_name.lower().encode('ascii') in stdout.lower()
    except Exception as e:
        logger.debug(f"进程探测失败 {image_name}: {e}")
    _proc_cache[image_name] = (now, running)
    return running


_xtquant_probe_lock = threading.Lock()


def probe_xtquant_connected(timeout: float = 8.0) -> bool:
    """探测 xtquant 数据服务是否真正可连（miniQMT/极简版/投研版在线才有）。

    大QMT (XtItClient.exe) 不会提供 xtquant 服务，该探测对大QMT返回 False。
    """
    def _probe() -> bool:
        try:
            from xtquant import xtdata
            client = xtdata.get_client()
            return bool(client and client.is_connected())
        except Exception as e:
            logger.debug(f"xtquant 探测失败: {e}")
            return False

    with _xtquant_probe_lock:
        result = {'ok': False}
        done = threading.Event()

        def _run():
            result['ok'] = _probe()
            done.set()

        worker = threading.Thread(target=_run, daemon=True)
        worker.start()
        if not done.wait(timeout):
            logger.debug(f"xtquant 探测超时(>{timeout}s)")
            return False
        return result['ok']


def probe_big_qmt_bridge(host: str = '127.0.0.1', port: int = 18766,
                         timeout: float = 1.5) -> bool:
    """探测大QMT实时行情桥（relay 的 WebSocket 端口）是否可连。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


# ────────────────────────── 路由决策 ──────────────────────────

@dataclass
class RoutePlan:
    """一次路由探测的结果。"""
    mode: str
    reasons: List[str] = field(default_factory=list)       # 为什么路由到这里
    notes: List[str] = field(default_factory=list)         # 需要用户知道的事项
    capabilities: Dict[str, bool] = field(default_factory=dict)
    datadir: Optional[Path] = None                         # 大QMT模式使用的行情目录

    @property
    def label(self) -> str:
        return MODE_LABELS.get(self.mode, self.mode)

    def describe(self) -> str:
        lines = [f"数据路由: {self.label}"]
        lines += [f"  · {r}" for r in self.reasons]
        lines += [f"  ⚠ {n}" for n in self.notes]
        return '\n'.join(lines)


def probe_route(force_refresh: bool = False) -> RoutePlan:
    """探测本机 QMT 状态并决定数据路由。"""
    paths = resolve_qmt_paths(force_refresh=force_refresh)
    datadir_big = paths.get('datadir_big')
    datadir_ok = bool(datadir_big and datadir_big.exists())

    xtquant_ok = probe_xtquant_connected()
    big_qmt_running = is_process_running('XtItClient.exe', force_refresh=force_refresh)

    # 1) miniQMT 在线：能力最全，无条件优先
    if xtquant_ok:
        return RoutePlan(
            mode=DataRoute.MINI_QMT,
            reasons=['miniQMT (xtquant) 数据服务已连接'],
            capabilities={
                'history_daily': True, 'stock_list': True,
                'etf_list': True, 'financial': True, 'realtime': True,
            },
        )

    # 2) 只有大QMT：历史走本地 DAT，实时走行情桥，财务走 Tushare
    if big_qmt_running and datadir_ok:
        bridge_ok = probe_big_qmt_bridge()
        plan = RoutePlan(
            mode=DataRoute.BIG_QMT,
            reasons=[
                'miniQMT (xtquant) 未连接（大QMT不提供xtquant服务）',
                f'大QMT 运行中，行情数据目录: {datadir_big}',
            ],
            notes=[
                '历史数据范围 = 你在大QMT「数据管理」中下载过的部分；'
                '缺数据请先在大QMT补充下载',
                '财务数据请使用「Tushare下载」标签页',
            ],
            capabilities={
                'history_daily': True, 'stock_list': True,
                'etf_list': True, 'financial': False, 'realtime': bridge_ok,
            },
            datadir=datadir_big,
        )
        if bridge_ok:
            plan.notes.append('检测到大QMT实时行情桥，实时行情可用')
        else:
            plan.notes.append(
                '实时行情桥未启动（可选）：运行 deploy/start_big_qmt_realtime_relay_windows.ps1 '
                '并在大QMT挂载信号接收器后可用'
            )
        return plan

    # 3) 兜底：给出明确原因，引导可用通道
    reasons = ['miniQMT (xtquant) 未连接']
    if not big_qmt_running:
        reasons.append('大QMT (XtItClient.exe) 未运行')
    if not datadir_ok:
        reasons.append(f'未找到大QMT行情数据目录: {datadir_big or "(未配置)"}')
    return RoutePlan(
        mode=DataRoute.FALLBACK,
        reasons=reasons,
        notes=[
            '本页无法下载历史行情：请启动大QMT或miniQMT，'
            '或使用「Tushare下载」标签页补数据',
        ],
        capabilities={
            'history_daily': False, 'stock_list': True,
            'etf_list': True, 'financial': False, 'realtime': False,
        },
    )


# ────────────────────────── 按路由取列表 ──────────────────────────

def _mini_stock_list() -> List[str]:
    from xtquant import xtdata
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    try:
        bj = xtdata.get_stock_list_in_sector('北交所')
        if bj:
            all_stocks = list(set(all_stocks + bj))
    except Exception:
        pass
    return list(all_stocks or [])


def _datadir_universe(datadir: Path) -> List[str]:
    """扫描大QMT datadir 中的日线 DAT 文件（含ETF），返回带后缀代码。"""
    from core.qmt_local_reader import QMTLocalReader
    reader = QMTLocalReader(data_dir=datadir, big_data_dir=datadir)
    return reader.list_available_stocks('1d')


def _tdx_formatted_list(kind: str) -> List[str]:
    from easy_xt.realtime_data.providers.tdx_provider import TdxDataProvider
    provider = TdxDataProvider()
    return provider.get_formatted_stock_list(kind=kind)


def get_stock_universe(plan: RoutePlan) -> Tuple[List[str], str]:
    """获取A股列表（排除ETF/基金）。返回 (代码列表, 来源说明)。"""
    if plan.mode == DataRoute.MINI_QMT:
        codes = [c for c in _mini_stock_list() if not is_etf_code(c)]
        return codes, 'miniQMT 板块列表'
    if plan.mode == DataRoute.BIG_QMT:
        codes = _filter_datadir_codes(
            _datadir_universe(plan.datadir), STOCK_PREFIXES_BY_MARKET)
        return codes, f'大QMT datadir 扫描 ({plan.datadir})'
    try:
        codes = _tdx_formatted_list('stock')
        if codes:
            return codes, '通达信 TDX 列表'
    except Exception as e:
        logger.warning(f"TDX 列表获取失败: {e}")
    raise RouteError(
        '无法获取A股列表：miniQMT未连接、大QMT数据目录不可用、TDX获取失败。'
        '请启动任一QMT后重试'
    )


def get_etf_universe(plan: RoutePlan) -> Tuple[List[str], str]:
    """获取ETF列表。返回 (代码列表, 来源说明)。"""
    if plan.mode == DataRoute.MINI_QMT:
        from xtquant import xtdata
        etf_list: List[str] = []
        for sector in ['沪深ETF', '上证ETF', '深证ETF']:
            try:
                stocks = xtdata.get_stock_list_in_sector(sector)
                if stocks:
                    etf_list.extend(stocks)
            except Exception:
                pass
        codes = list(set(etf_list))
        if codes:
            return codes, 'miniQMT ETF板块列表'
    if plan.mode == DataRoute.BIG_QMT:
        codes = _filter_datadir_codes(
            _datadir_universe(plan.datadir), ETF_PREFIXES_BY_MARKET)
        if codes:
            return codes, f'大QMT datadir 扫描 ({plan.datadir})'
    try:
        codes = _tdx_formatted_list('etf')
        if codes:
            return codes, '通达信 TDX 基金列表'
    except Exception as e:
        logger.warning(f"TDX ETF列表获取失败: {e}")
    raise RouteError(
        '无法获取ETF列表：miniQMT未连接、大QMT数据目录无ETF数据、TDX获取失败。'
        '请在大QMT「数据管理」中下载ETF数据后重试'
    )
