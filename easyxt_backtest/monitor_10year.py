# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)
"""
10年回测进度监控
"""
import time
import sys
from pathlib import Path

log_file = Path(__file__).parent.parent / "output" / "10year_backtest.log"

logger.info("\n" + "="*70)
logger.info("10年回测进度监控")
logger.info("="*70)

logger.info("\n正在运行...")
logger.info(f"日志文件: {log_file}")
logger.info("\n按 Ctrl+C 停止监控\n")

try:
    last_size = 0
    last_lines = []

    while True:
        if log_file.exists():
            current_size = log_file.stat().st_size

            # 如果文件大小有变化，读取新增的行
            if current_size > last_size:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_size)
                    new_lines = f.readlines()

                    for line in new_lines:
                        # 只打印关键信息
                        if any(keyword in line for keyword in [
                            '调仓日期', '回测结果', '收益率', '回撤',
                            '[步骤', '======', '总交易次数',
                            '最终资金', '✓'
                        ]):
                            logger.info(line.strip())

                        # 保存最近20行用于查找错误
                        last_lines.append(line)
                        if len(last_lines) > 20:
                            last_lines.pop(0)

                last_size = current_size

        time.sleep(2)  # 每2秒检查一次

except KeyboardInterrupt:
    logger.info("\n\n监控已停止")
    logger.info("\n最后20行日志:")
    logger.info("-"*70)
    for line in last_lines[-20:]:
        logger.info(line.rstrip())
    logger.info("="*70)
