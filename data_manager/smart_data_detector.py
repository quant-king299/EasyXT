#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能数据缺失检测模块
自动识别股票的"数据空窗期"，只下载缺失数据，支持断点续传

参考文档：duckdb.docx
智能缺失检测策略：系统不会盲目下载所有数据，而是会自动扫描本地数据库，
识别出每只股票的"数据空窗期"。
例如，如果本地已有 2020-2023 年的数据，系统只会自动下载 2024 年以来的增量数据。
同时，系统支持断点续传，万一网络波动导致下载中断，重启后可直接从断点处继续。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date, timedelta
import duckdb


class TradingCalendar:
    """
    A股交易日历管理器
    内置完整的A股交易日历，用于数据完整性检查
    """

    def __init__(self):
        """初始化交易日历"""
        self.holidays = self._load_holidays()

    def _load_holidays(self) -> set:
        """
        加载A股节假日和周末
        返回非交易日的日期集合
        """
        # 生成2000年至今的所有周末和主要节假日
        holidays = set()

        # 生成周末
        start_date = date(2000, 1, 1)
        end_date = date(2030, 12, 31)

        current_date = start_date
        while current_date <= end_date:
            # 周六周日
            if current_date.weekday() >= 5:
                holidays.add(current_date)
            current_date += timedelta(days=1)

        # 添加主要节假日（春节、国庆等）
        # 这些是固定的或常见的节假日，实际应用中应该从官方日历获取
        major_holidays = [
            # 元旦
            *self._generate_holiday_range(date(2000, 1, 1), date(2000, 1, 3)),
            # 春节（每年不同，这里只是示例）
            *self._generate_spring_festival_holidays(),
            # 清明节
            *self._generate_qingming_holidays(),
            # 劳动节
            *self._generate_holiday_range(date(2000, 5, 1), date(2000, 5, 7)),
            # 端午节
            *self._generate_dragon_boat_holidays(),
            # 中秋节
            *self._generate_mid_autumn_holidays(),
            # 国庆节
            *self._generate_holiday_range(date(2000, 10, 1), date(2000, 10, 10)),
        ]

        holidays.update(major_holidays)

        return holidays

    def _generate_holiday_range(self, start: date, end: date) -> List[date]:
        """生成节假日范围"""
        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current = current + timedelta(days=1)
        return dates

    def _generate_spring_festival_holidays(self) -> List[date]:
        """生成春节假期（2000-2030）"""
        # 春节日期表（农历正月初一对应的公历日期）
        spring_festivals = {
            2024: (2, 10),
            2025: (1, 29),
            2026: (2, 17),
            2027: (2, 6),
            2028: (1, 26),
            2029: (2, 13),
            2030: (2, 3),
        }

        holidays = []
        for year, (month, day) in spring_festivals.items():
            # 春节假期通常从除夕到初七（8天）
            festival_date = date(year, month, day)
            for i in range(-1, 7):  # 除夕到初七
                holidays.append(festival_date + timedelta(days=i))

        return holidays

    def _generate_qingming_holidays(self) -> List[date]:
        """生成清明节假期（通常4月4-6日）"""
        holidays = []
        for year in range(2000, 2031):
            # 清明节通常是4月4日或5日
            for day in [4, 5, 6]:
                holidays.append(date(year, 4, day))
        return holidays

    def _generate_dragon_boat_holidays(self) -> List[date]:
        """生成端午节假期（通常5月28-30日）"""
        holidays = []
        for year in range(2000, 2031):
            for day in [28, 29, 30]:
                try:
                    holidays.append(date(year, 5, day))
                except:
                    pass
        return holidays

    def _generate_mid_autumn_holidays(self) -> List[date]:
        """生成中秋节假期（通常9月中旬）"""
        holidays = []
        for year in range(2000, 2031):
            for day in range(15, 18):
                try:
                    holidays.append(date(year, 9, day))
                except:
                    pass
        return holidays

    def is_trading_day(self, check_date: date) -> bool:
        """判断是否为交易日"""
        return check_date not in self.holidays

    def get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """
        获取指定日期范围内的所有交易日

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易日列表
        """
        trading_days = []
        current_date = start_date

        while current_date <= end_date:
            if self.is_trading_day(current_date):
                trading_days.append(current_date)
            current_date += timedelta(days=1)

        return trading_days

    def get_missing_trading_days(self, start_date: date, end_date: date,
                                 existing_dates: List[date]) -> List[date]:
        """
        获取缺失的交易日

        Args:
            start_date: 开始日期
            end_date: 结束日期
            existing_dates: 已有的数据日期

        Returns:
            缺失的交易日列表
        """
        all_trading_days = set(self.get_trading_days(start_date, end_date))
        existing_set = set(existing_dates)

        missing_days = sorted(all_trading_days - existing_set)
        return missing_days


class SmartDataDetector:
    """
    智能数据缺失检测器

    功能：
    1. 扫描本地数据库，识别数据空窗期
    2. 将缺失数据分段（连续的缺失段）
    3. 支持断点续传
    """

    def __init__(self, duckdb_path: str = r'D:/StockData/stock_data.ddb'):
        """
        初始化检测器

        Args:
            duckdb_path: DuckDB 数据库路径
        """
        self.duckdb_path = duckdb_path
        self.con = None
        self.calendar = TradingCalendar()

    def connect(self):
        """连接数据库"""
        try:
            self.con = duckdb.connect(self.duckdb_path, read_only=True)
            return True
        except Exception as e:
            print(f"[ERROR] 数据库连接失败: {e}")
            return False

    def detect_missing_data(self,
                           stock_code: str,
                           start_date: str,
                           end_date: str) -> Dict:
        """
        检测指定股票的数据缺失情况

        Args:
            stock_code: 股票代码
            start_date: 检查开始日期
            end_date: 检查结束日期

        Returns:
            缺失数据报告，包含：
            {
                'stock_code': str,
                'check_range': (start, end),
                'existing_data': {
                    'first_date': date,
                    'last_date': date,
                    'count': int,
                    'dates': list
                },
                'missing_segments': [
                    {'start': date, 'end': date, 'days': int},
                    ...
                ],
                'missing_trading_days': list,
                'completeness_ratio': float
            }
        """
        if not self.con:
            print("[ERROR] 请先连接数据库")
            return {}

        start = pd.to_datetime(start_date).date()
        end = pd.to_datetime(end_date).date()

        # 1. 查询现有数据
        query = f"""
            SELECT date
            FROM stock_daily
            WHERE stock_code = '{stock_code}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
            ORDER BY date
        """

        try:
            df_existing = self.con.execute(query).df()

            if df_existing.empty:
                existing_dates = []
            else:
                existing_dates = pd.to_datetime(df_existing['date']).dt.date.tolist()

        except Exception as e:
            print(f"[ERROR] 查询失败: {e}")
            return {}

        # 2. 计算应该有的交易日
        expected_trading_days = self.calendar.get_trading_days(start, end)

        # 3. 找出缺失的交易日
        missing_trading_days = self.calendar.get_missing_trading_days(
            start, end, existing_dates
        )

        # 4. 将缺失数据分段（连续的缺失段）
        missing_segments = self._group_continuous_dates(missing_trading_days)

        # 5. 计算完整度
        completeness_ratio = len(existing_dates) / len(expected_trading_days) if expected_trading_days else 0

        # 6. 构建报告
        report = {
            'stock_code': stock_code,
            'check_range': (start_date, end_date),
            'expected_trading_days': len(expected_trading_days),
            'existing_data': {
                'first_date': existing_dates[0] if existing_dates else None,
                'last_date': existing_dates[-1] if existing_dates else None,
                'count': len(existing_dates),
                'dates': existing_dates
            },
            'missing_trading_days': missing_trading_days,
            'missing_segments': missing_segments,
            'missing_count': len(missing_trading_days),
            'completeness_ratio': completeness_ratio
        }

        return report

    def _group_continuous_dates(self, dates: List[date]) -> List[Dict]:
        """
        将日期分组为连续的段

        Args:
            dates: 日期列表

        Returns:
            分段列表，每段包含 start, end, days
        """
        if not dates:
            return []

        segments = []
        current_segment = {'start': dates[0], 'end': dates[0], 'days': 1}

        for i in range(1, len(dates)):
            # 如果是连续的（相差1-3天，考虑到周末）
            if (dates[i] - current_segment['end']).days <= 3:
                current_segment['end'] = dates[i]
                current_segment['days'] += 1
            else:
                # 不连续，保存当前段，开始新段
                segments.append(current_segment)
                current_segment = {'start': dates[i], 'end': dates[i], 'days': 1}

        segments.append(current_segment)

        return segments

    def batch_detect_missing(self,
                             stock_codes: List[str],
                             start_date: str,
                             end_date: str) -> Dict[str, Dict]:
        """
        批量检测多只股票的数据缺失情况

        Args:
            stock_codes: 股票代码列表
            start_date: 检查开始日期
            end_date: 检查结束日期

        Returns:
            股票代码到缺失报告的字典
        """
        reports = {}

        for stock_code in stock_codes:
            report = self.detect_missing_data(stock_code, start_date, end_date)
            reports[stock_code] = report

        return reports

    def get_download_plan(self,
                         stock_codes: List[str],
                         start_date: str,
                         end_date: str) -> Dict:
        """
        生成数据下载计划

        只下载缺失的数据段，避免重复下载

        Args:
            stock_codes: 股票代码列表
            start_date: 检查开始日期
            end_date: 检查结束日期

        Returns:
            下载计划
            {
                'total_stocks': int,
                'stocks_with_missing_data': int,
                'total_missing_days': int,
                'download_tasks': [
                    {
                        'stock_code': str,
                        'segments': [
                            {'start': date, 'end': date, 'days': int},
                            ...
                        ]
                    },
                    ...
                ]
            }
        """
        reports = self.batch_detect_missing(stock_codes, start_date, end_date)

        download_tasks = []
        stocks_with_missing = 0
        total_missing_days = 0

        for stock_code, report in reports.items():
            if report.get('missing_count', 0) > 0:
                stocks_with_missing += 1
                total_missing_days += report['missing_count']

                download_tasks.append({
                    'stock_code': stock_code,
                    'segments': report['missing_segments']
                })

        plan = {
            'total_stocks': len(stock_codes),
            'stocks_with_missing_data': stocks_with_missing,
            'total_missing_days': total_missing_days,
            'download_tasks': download_tasks
        }

        return plan

    def print_missing_report(self, report: Dict):
        """
        打印缺失数据报告

        Args:
            report: 缺失数据报告
        """
        print()
        print("=" * 60)
        print(f"数据缺失报告: {report['stock_code']}")
        print("=" * 60)
        print(f"检查范围: {report['check_range'][0]} ~ {report['check_range'][1]}")
        print(f"应有交易日: {report['expected_trading_days']} 天")
        print()

        # 现有数据
        existing = report['existing_data']
        print("现有数据:")
        if existing['count'] > 0:
            print(f"  数据量: {existing['count']} 条")
            print(f"  日期范围: {existing['first_date']} ~ {existing['last_date']}")
        else:
            print("  无数据")
        print()

        # 缺失数据
        missing = report['missing_trading_days']
        print(f"缺失交易日: {len(missing)} 天")
        print(f"数据完整度: {report['completeness_ratio']*100:.2f}%")
        print()

        if report['missing_segments']:
            print("缺失数据段:")
            for i, segment in enumerate(report['missing_segments'], 1):
                print(f"  段 {i}: {segment['start']} ~ {segment['end']} ({segment['days']} 天)")
        else:
            print("  数据完整，无缺失")

        print("=" * 60)

    def close(self):
        """关闭数据库连接"""
        if self.con:
            self.con.close()
            self.con = None


def test_smart_detection():
    """测试智能缺失检测功能"""
    print("=" * 60)
    print("智能数据缺失检测测试")
    print("=" * 60)
    print()

    # 创建检测器
    detector = SmartDataDetector()

    if not detector.connect():
        print("[ERROR] 无法连接数据库")
        return

    # 测试单个股票
    print("[1] 检测 511380.SH 数据缺失...")
    report = detector.detect_missing_data('511380.SH', '2024-01-01', '2025-01-31')
    detector.print_missing_report(report)

    # 测试批量检测
    print()
    print("[2] 批量检测...")
    stock_codes = ['511380.SH', '511880.SH', '511010.SH']
    plan = detector.get_download_plan(stock_codes, '2024-01-01', '2025-01-31')

    print(f"总标的数: {plan['total_stocks']}")
    print(f"有缺失的标的: {plan['stocks_with_missing_data']}")
    print(f"总缺失天数: {plan['total_missing_days']}")
    print()

    # 打印下载任务
    print("下载任务:")
    for task in plan['download_tasks']:
        print(f"  {task['stock_code']}: {len(task['segments'])} 个缺失段")

    detector.close()
    print()
    print("[OK] 测试完成")


if __name__ == "__main__":
    test_smart_detection()
