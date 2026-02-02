#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据完整性检查模块
提供全面的数据质量检查和验证功能

参考文档：duckdb.docx
数据完整性检查功能：系统内置了完整的 A 股交易日历，能够自动比对本地数据。
你只需指定时间段，系统就能精确揪出缺失的每一个交易日，并在界面上高亮提示。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date, timedelta
import duckdb
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from smart_data_detector import SmartDataDetector, TradingCalendar


class DataQualityReport:
    """数据质量报告"""

    def __init__(self):
        self.issues = []
        self.warnings = []
        self.info = []

    def add_issue(self, level: str, message: str):
        """添加问题"""
        if level == 'ERROR':
            self.issues.append(message)
        elif level == 'WARNING':
            self.warnings.append(message)
        else:
            self.info.append(message)

    def has_errors(self) -> bool:
        return len(self.issues) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def get_summary(self) -> Dict:
        return {
            'errors': len(self.issues),
            'warnings': len(self.warnings),
            'info': len(self.info),
            'issues': self.issues,
            'warnings': self.warnings
        }


class DataIntegrityChecker:
    """
    数据完整性检查器

    功能：
    1. 缺失交易日检查
    2. 数据质量检查（异常值、价格关系等）
    3. 数据连续性检查
    4. 生成完整性报告
    """

    def __init__(self, duckdb_path: str = r'D:/StockData/stock_data.ddb'):
        """
        初始化检查器

        Args:
            duckdb_path: DuckDB 数据库路径
        """
        self.duckdb_path = duckdb_path
        self.con = None
        self.detector = SmartDataDetector(duckdb_path)
        self.calendar = TradingCalendar()

    def connect(self):
        """连接数据库"""
        return self.detector.connect()

    def check_integrity(self,
                       stock_code: str,
                       start_date: str,
                       end_date: str,
                       detailed: bool = True) -> Dict:
        """
        执行完整的数据完整性检查

        Args:
            stock_code: 股票代码
            start_date: 检查开始日期
            end_date: 检查结束日期
            detailed: 是否执行详细检查

        Returns:
            完整性报告
        """
        report = DataQualityReport()

        # 1. 检查缺失交易日
        print(f"[1/5] 检查缺失交易日...")
        missing_report = self.detector.detect_missing_data(stock_code, start_date, end_date)

        if missing_report['missing_count'] > 0:
            report.add_issue('WARNING',
                           f"缺失 {missing_report['missing_count']} 个交易日: "
                           f"{[str(d) for d in missing_report['missing_trading_days'][:10]]}"
                           )
        else:
            report.add_issue('INFO', "交易日数据完整")

        # 2. 检查数据质量
        print(f"[2/5] 检查数据质量...")
        quality_issues = self._check_data_quality(stock_code, start_date, end_date)

        for issue in quality_issues:
            report.add_issue(issue['level'], issue['message'])

        # 3. 检查价格关系
        print(f"[3/5] 检查价格关系...")
        price_issues = self._check_price_relations(stock_code, start_date, end_date)

        for issue in price_issues:
            report.add_issue(issue['level'], issue['message'])

        # 4. 检查异常值
        print(f"[4/5] 检查异常值...")
        outlier_issues = self._check_outliers(stock_code, start_date, end_date)

        for issue in outlier_issues:
            report.add_issue(issue['level'], issue['message'])

        # 5. 检查成交量异常
        if detailed:
            print(f"[5/5] 检查成交量...")
            volume_issues = self._check_volume_anomalies(stock_code, start_date, end_date)

            for issue in volume_issues:
                report.add_issue(issue['level'], issue['message'])

        # 汇总报告
        summary = {
            'stock_code': stock_code,
            'check_range': (start_date, end_date),
            'missing_trading_days': missing_report['missing_count'],
            'completeness_ratio': missing_report['completeness_ratio'],
            'quality_report': report.get_summary(),
            'status': 'PASS' if not report.has_errors() else 'FAIL'
        }

        return summary

    def _check_data_quality(self, stock_code: str, start_date: str, end_date: str) -> List[Dict]:
        """检查数据质量"""
        issues = []

        query = f"""
            SELECT date, open, high, low, close, volume
            FROM stock_daily
            WHERE stock_code = '{stock_code}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
            ORDER BY date
        """

        try:
            df = self.detector.con.execute(query).df()

            if df.empty:
                return [{'level': 'ERROR', 'message': '数据库中无数据'}]

            # 检查空值
            null_counts = df.isnull().sum()
            for col, count in null_counts.items():
                if count > 0:
                    issues.append({
                        'level': 'ERROR',
                        'message': f'{col} 列有 {count} 个空值'
                    })

            # 检查零值或负值价格
            for col in ['open', 'high', 'low', 'close']:
                if col in df.columns:
                    invalid_count = (df[col] <= 0).sum()
                    if invalid_count > 0:
                        issues.append({
                            'level': 'ERROR',
                            'message': f'{col} 列有 {invalid_count} 个非正值'
                        })

        except Exception as e:
            issues.append({
                'level': 'ERROR',
                'message': f'数据质量检查失败: {e}'
            })

        return issues

    def _check_price_relations(self, stock_code: str, start_date: str, end_date: str) -> List[Dict]:
        """检查价格关系合理性"""
        issues = []

        query = f"""
            SELECT date, open, high, low, close
            FROM stock_daily
            WHERE stock_code = '{stock_code}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
            ORDER BY date
        """

        try:
            df = self.detector.con.execute(query).df()

            if df.empty or len(df) == 0:
                return []

            # 检查: high >= max(open, close) and low <= min(open, close)
            invalid_high = df[df['high'] < df[['open', 'close']].max(axis=1)]
            invalid_low = df[df['low'] > df[['open', 'close']].min(axis=1)]

            if len(invalid_high) > 0:
                issues.append({
                    'level': 'WARNING',
                    'message': f'有 {len(invalid_high)} 条数据的最高价小于开盘价或收盘价'
                })

            if len(invalid_low) > 0:
                issues.append({
                    'level': 'WARNING',
                    'message': f'有 {len(invalid_low)} 条数据的最低价大于开盘价或收盘价'
                })

        except Exception as e:
            issues.append({
                'level': 'ERROR',
                'message': f'价格关系检查失败: {e}'
            })

        return issues

    def _check_outliers(self, stock_code: str, start_date: str, end_date: str) -> List[Dict]:
        """检查异常值"""
        issues = []

        query = f"""
            SELECT date, close, volume
            FROM stock_daily
            WHERE stock_code = '{stock_code}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
            ORDER BY date
        """

        try:
            df = self.detector.con.execute(query).df()

            if df.empty or len(df) < 2:
                return []

            # 检查异常波动（单日涨跌幅超过 20%）
            returns = df['close'].pct_change()
            extreme_returns = returns[returns.abs() > 0.20]

            if len(extreme_returns) > 0:
                dates_str = [str(d) for d in df.loc[extreme_returns.index, 'date'].tolist()[:5]]
                issues.append({
                    'level': 'WARNING',
                    'message': f'有 {len(extreme_returns)} 天的涨跌幅超过 20%: {dates_str}...'
                })

        except Exception as e:
            issues.append({
                'level': 'ERROR',
                'message': f'异常值检查失败: {e}'
            })

        return issues

    def _check_volume_anomalies(self, stock_code: str, start_date: str, end_date: str) -> List[Dict]:
        """检查成交量异常"""
        issues = []

        query = f"""
            SELECT date, volume
            FROM stock_daily
            WHERE stock_code = '{stock_code}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
              AND volume > 0
            ORDER BY date
        """

        try:
            df = self.detector.con.execute(query).df()

            if df.empty or len(df) < 10:
                return []

            # 检查成交量异常（超过均值的 5 倍）
            volume_mean = df['volume'].mean()
            volume_std = df['volume'].std()
            outliers = df[df['volume'] > volume_mean + 5 * volume_std]

            if len(outliers) > 0:
                dates_str = [str(d) for d in outliers['date'].tolist()[:5]]
                issues.append({
                    'level': 'INFO',
                    'message': f'有 {len(outliers)} 天的成交量异常偏高: {dates_str}...'
                })

        except Exception as e:
            issues.append({
                'level': 'WARNING',
                'message': f'成交量检查失败: {e}'
            })

        return issues

    def batch_check_integrity(self,
                              stock_codes: List[str],
                              start_date: str,
                              end_date: str) -> Dict[str, Dict]:
        """
        批量检查多只股票的数据完整性

        Args:
            stock_codes: 股票代码列表
            start_date: 检查开始日期
            end_date: 检查结束日期

        Returns:
            股票代码到完整性报告的字典
        """
        reports = {}

        total = len(stock_codes)
        for i, stock_code in enumerate(stock_codes, 1):
            print(f"\n检查进度: {i}/{total} - {stock_code}")
            report = self.check_integrity(stock_code, start_date, end_date)
            reports[stock_code] = report

        return reports

    def generate_integrity_report(self, reports: Dict[str, Dict]) -> str:
        """
        生成完整性检查报告

        Args:
            reports: 完整性报告字典

        Returns:
            格式化的报告文本
        """
        lines = []
        lines.append("=" * 80)
        lines.append("数据完整性检查报告")
        lines.append("=" * 80)
        lines.append("")

        # 汇总统计
        total_stocks = len(reports)
        passed = sum(1 for r in reports.values() if r['status'] == 'PASS')
        failed = total_stocks - passed

        lines.append(f"检查标的数: {total_stocks}")
        lines.append(f"通过: {passed}")
        lines.append(f"失败: {failed}")
        lines.append("")

        # 详细报告
        lines.append("-" * 80)
        lines.append("详细报告:")
        lines.append("-" * 80)
        lines.append("")

        for stock_code, report in reports.items():
            lines.append(f"标的: {stock_code}")
            lines.append(f"检查范围: {report['check_range'][0]} ~ {report['check_range'][1]}")
            lines.append(f"缺失交易日: {report['missing_trading_days']}")
            lines.append(f"完整度: {report['completeness_ratio']*100:.2f}%")
            lines.append(f"状态: {report['status']}")

            quality = report['quality_report']
            lines.append(f"  错误: {quality['errors']}")
            lines.append(f"  警告: {quality['warnings']}")

            if quality['issues']:
                lines.append("  问题详情:")
                for issue in quality['issues'][:5]:
                    lines.append(f"    - {issue}")
                if len(quality['issues']) > 5:
                    lines.append(f"    ... 还有 {len(quality['issues']) - 5} 个问题")

            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def close(self):
        """关闭数据库连接"""
        self.detector.close()


def test_integrity_checker():
    """测试数据完整性检查功能"""
    print("=" * 60)
    print("数据完整性检查测试")
    print("=" * 60)
    print()

    # 创建检查器
    checker = DataIntegrityChecker()

    if not checker.connect():
        print("[ERROR] 无法连接数据库")
        return

    # 测试单个股票
    print("[1] 检查 511380.SH 完整性...")
    report = checker.check_integrity('511380.SH', '2024-01-01', '2025-01-31')

    print(f"\n检查结果: {report['status']}")
    print(f"缺失交易日: {report['missing_trading_days']}")
    print(f"完整度: {report['completeness_ratio']*100:.2f}%")
    print(f"错误: {report['quality_report']['errors']}")
    print(f"警告: {report['quality_report']['warnings']}")

    # 测试批量检查
    print()
    print("[2] 批量检查...")
    stock_codes = ['511380.SH', '511880.SH', '511010.SH']
    reports = checker.batch_check_integrity(stock_codes, '2024-01-01', '2025-01-31')

    # 生成报告
    report_text = checker.generate_integrity_report(reports)
    print()
    print(report_text)

    checker.close()
    print("[OK] 测试完成")


if __name__ == "__main__":
    test_integrity_checker()
