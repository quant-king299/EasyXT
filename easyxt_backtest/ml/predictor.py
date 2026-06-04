#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型预测器 — 加载训练好的模型，对指定日期生成预测信号

预测信号可直接传入 EnhancedBacktestEngine 的选股逻辑中使用。

使用方法:
  from easyxt_backtest.ml import ModelPredictor

  predictor = ModelPredictor('ml/models/lightgbm_model.pkl')
  scores = predictor.predict('2024-06-03', stock_pool=['000001.SZ', '600519.SH'])
  # -> {'000001.SZ': 0.023, '600519.SH': 0.015, ...}
"""

import sys
import pickle
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))


class ModelPredictor:
    """模型预测器

    加载 trainer 保存的模型，对指定日期的股票池生成预测分数。
    分数越高 = 预期未来收益越高。
    """

    def __init__(self, model_path: str = None):
        if model_path is None:
            model_path = _project_root / "easyxt_backtest" / "ml" / "models" / "lightgbm_model.pkl"
        self.model_path = Path(model_path)

        self._model = None
        self._feature_names = []
        self._metrics = {}
        self._label_horizon = 5
        self._loaded = False

    def load(self):
        """加载模型"""
        if self._loaded:
            return
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"模型不存在: {self.model_path}\n"
                f"请先运行: python -m easyxt_backtest.ml.trainer"
            )
        with open(self.model_path, "rb") as f:
            package = pickle.load(f)

        self._model = package["model"]
        self._feature_names = package["feature_names"]
        self._metrics = package.get("metrics", {})
        self._label_horizon = package.get("label_horizon", 5)
        self._loaded = True

    def _connect_duckdb(self):
        import duckdb
        from config.env_config import get_default_db_path
        return duckdb.connect(get_default_db_path(), read_only=True)

    def _compute_single_stock_features(
        self, stock_code: str, target_date: str, lookback: int = 120
    ) -> pd.Series:
        """计算单只股票在目标日期的特征向量

        Args:
            stock_code: 股票代码
            target_date: 目标日期 (YYYY-MM-DD)
            lookback: 回顾天数

        Returns:
            Series with feature names as index
        """
        con = self._connect_duckdb()
        try:
            # 获取该日期及之前的数据
            query = f"""
                SELECT CAST(date AS VARCHAR) as date, open, high, low, close, volume
                FROM stock_daily
                WHERE stock_code = '{stock_code}'
                  AND date <= '{target_date}'
                ORDER BY date DESC
                LIMIT {lookback}
            """
            df = con.execute(query).df()
            if len(df) < 20:
                return None  # 数据不足
            df = df.sort_values("date")
            return self._calc_features(df.iloc[-1], df)
        finally:
            con.close()

    def _calc_features(self, latest: pd.Series, hist: pd.DataFrame) -> pd.Series:
        """从历史数据计算特征值 (与 trainer.compute_features 对应)"""
        close = hist["close"].values.astype(float)
        volume = hist["volume"].values.astype(float)
        high = hist["high"].values.astype(float)
        low = hist["low"].values.astype(float)
        n = len(close)

        feats = {}

        # 收益率
        feats["ret_1d"] = close[-1] / close[-2] - 1 if n >= 2 else 0
        feats["ret_5d"] = close[-1] / close[-6] - 1 if n >= 6 else 0
        feats["ret_20d"] = close[-1] / close[-21] - 1 if n >= 21 else 0

        # 均线偏离
        for w in [5, 10, 20, 60]:
            if n >= w:
                ma = close[-w:].mean()
                feats[f"ma{w}_bias"] = (close[-1] - ma) / (ma + 1e-9)
            else:
                feats[f"ma{w}_bias"] = 0

        # 波动率
        rets = np.diff(close) / (close[:-1] + 1e-9)
        for w in [5, 20]:
            if len(rets) >= w:
                feats[f"vol_{w}d"] = rets[-w:].std()
            else:
                feats[f"vol_{w}d"] = 0

        # 量比
        if n >= 5:
            feats["vol_ratio_5"] = volume[-1] / (volume[-5:].mean() + 1e-9)
        else:
            feats["vol_ratio_5"] = 1
        if n >= 20:
            feats["vol_ratio_20"] = volume[-1] / (volume[-20:].mean() + 1e-9)
        else:
            feats["vol_ratio_20"] = 1

        # amount_ratio
        amt = volume * close
        amt5 = amt[-5:].mean() if n >= 5 else amt[-1]
        feats["amount_ratio_5"] = amt[-1] / (amt5 + 1e-9)

        # 价格位置
        feats["high_low_ratio"] = (high[-1] - low[-1]) / (close[-1] + 1e-9)
        if n >= 20:
            roll_h = high[-20:].max()
            roll_l = low[-20:].min()
            feats["close_position"] = (close[-1] - roll_l) / (roll_h - roll_l + 1e-9)
        else:
            feats["close_position"] = 0.5

        # RSI 14
        if n >= 15:
            delta = np.diff(close[-15:])
            gain = delta[delta > 0].sum()
            loss = -delta[delta < 0].sum()
            rs = gain / (loss + 1e-9)
            feats["rsi_14"] = 100 - 100 / (1 + rs)
        else:
            feats["rsi_14"] = 50

        # turnover proxy
        if n >= 60:
            feats["turnover_proxy"] = amt[-1] / (close[-60:].mean() + 1e-9)
        else:
            feats["turnover_proxy"] = amt[-1] / (close.mean() + 1e-9)

        # size proxy
        feats["size_proxy"] = np.log1p(amt[-1])

        # 对齐到训练时的特征名
        result = pd.Series(feats)
        return result[self._feature_names]

    def predict(
        self,
        target_date: str,
        stock_pool: List[str] = None,
    ) -> Dict[str, float]:
        """对指定日期的股票池生成预测分数

        Args:
            target_date: 预测日期 (YYYY-MM-DD)
            stock_pool:  股票列表 (None=需要外部提供)

        Returns:
            {stock_code: score} — score 越高越好
        """
        self.load()

        if stock_pool is None:
            # 从 DuckDB 获取当天有数据的所有股票
            con = self._connect_duckdb()
            try:
                stock_pool = con.execute(f"""
                    SELECT DISTINCT stock_code FROM stock_daily
                    WHERE date = '{target_date}'
                """).fetchdf()["stock_code"].tolist()
            finally:
                con.close()

        print(f"[PREDICT] 日期={target_date}, 股票池={len(stock_pool)} 只")

        scores = {}
        failed = 0
        for i, code in enumerate(stock_pool):
            try:
                feats = self._compute_single_stock_features(code, target_date)
                if feats is not None and not feats.isna().any():
                    X = feats.values.astype(np.float32).reshape(1, -1)
                    scores[code] = float(self._model.predict(X)[0])
            except Exception:
                failed += 1

            if (i + 1) % 500 == 0:
                print(f"  [{i+1}/{len(stock_pool)}] 已完成...")

        if failed:
            print(f"  [WARN] {failed} 只股票预测失败")
        print(f"  [OK] 预测完成: {len(scores)} 只, "
              f"范围=[{min(scores.values()):.4f}, {max(scores.values()):.4f}]")

        return scores

    def predict_batch(
        self,
        dates: List[str],
        stock_pool: List[str] = None,
    ) -> pd.DataFrame:
        """批量预测多日

        Returns:
            DataFrame with columns: date, stock_code, score
        """
        all_rows = []
        for d in dates:
            scores = self.predict(d, stock_pool)
            for code, score in scores.items():
                all_rows.append({"date": d, "stock_code": code, "score": score})
        return pd.DataFrame(all_rows)

    def get_metrics(self) -> Dict:
        """返回训练时的评估指标"""
        self.load()
        return self._metrics
