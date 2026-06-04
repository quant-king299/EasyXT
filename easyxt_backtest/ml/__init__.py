# -*- coding: utf-8 -*-
"""
miniQMT 轻量 ML 模块 — 直接对接 DuckDB

无需 Qlib、无需数据转换。直接用现有因子系统生成特征，
训练 LightGBM 模型，产出预测信号供 EnhancedBacktestEngine 回测。

架构:
  DuckDB stock_daily → 现有因子库(alpha101/191+技术+基本面)
    → LightGBM 训练 → 预测信号 → EnhancedBacktestEngine 回测

使用:
  from easyxt_backtest.ml import DuckDBModelTrainer
  trainer = DuckDBModelTrainer()
  trainer.train(stock_pool, start, end)
  predictions = trainer.predict(target_date)
"""

from .trainer import DuckDBModelTrainer
from .predictor import ModelPredictor

__all__ = ["DuckDBModelTrainer", "ModelPredictor"]
