import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
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

        """从历史数据批量计算特征值 (与 trainer.compute_features 对齐)"""

        close = hist["close"].values.astype(float)

        volume = hist["volume"].values.astype(float)

        high = hist["high"].values.astype(float)

        low = hist["low"].values.astype(float)

        open_ = hist["open"].values.astype(float)

        n = len(close)



        feats = {}



        def _safe_rolling(arr, w, func):

            return func(arr[-w:]) if n >= w else func(arr)



        # ═══ 收益率 ═══

        rets = np.diff(close) / (close[:-1] + 1e-9)

        feats["ret_1d"] = rets[-1] if len(rets) >= 1 else 0

        feats["ret_5d"] = close[-1] / close[-6] - 1 if n >= 6 else 0

        feats["ret_20d"] = close[-1] / close[-21] - 1 if n >= 21 else 0



        # ═══ 均线偏离 ═══

        for w in [5, 10, 20, 60]:

            ma = close[-w:].mean() if n >= w else close.mean()

            feats[f"ma{w}_bias"] = (close[-1] - ma) / (ma + 1e-9)



        # ═══ 波动率 ═══

        for w in [5, 10, 20]:

            feats[f"vol_{w}d"] = rets[-w:].std() if len(rets) >= w else 0



        # ═══ 量比 ═══

        for w in [5, 10, 20]:

            feats[f"vol_ratio_{w}"] = volume[-1] / (volume[-w:].mean() + 1e-9)



        # ═══ amount ratio ═══

        amt = volume * close

        for w in [5, 10]:

            feats[f"amount_ratio_{w}"] = amt[-1] / (amt[-w:].mean() + 1e-9)



        # ═══ 价格位置 ═══

        feats["high_low_ratio"] = (high[-1] - low[-1]) / (close[-1] + 1e-9)

        for w in [10, 20, 60]:

            rh = high[-w:].max() if n >= w else high.max()

            rl = low[-w:].min() if n >= w else low.min()

            feats[f"close_pos_{w}"] = (close[-1] - rl) / (rh - rl + 1e-9)



        # ═══ RSI ═══

        for w in [6, 14, 24]:

            if n >= w + 1:

                delta = np.diff(close[-(w+1):])

                gain = delta[delta > 0].sum()

                loss = -delta[delta < 0].sum()

                rs = gain / (loss + 1e-9)

                feats[f"rsi_{w}"] = 100 - 100 / (1 + rs)

            else:

                feats[f"rsi_{w}"] = 50



        # 判断是否需要完整模式 (根据训练特征名)

        needs_extended = any(f.startswith("alpha") or f.startswith("mom_")

                             or f.startswith("skew_") or f.startswith("kurt_")

                             or f.startswith("ud_ratio_") for f in self._feature_names)



        if needs_extended:

            # ═══ alpha001 ═══

            ret_std20 = pd.Series(rets).rolling(20, min_periods=5).std().values

            a1_arr = np.where(rets < 0, ret_std20[-len(rets):], close[-len(rets):]) ** 2

            feats["alpha001"] = np.argmax(a1_arr[-5:]) / 5 - 0.5 if len(a1_arr) >= 5 else 0



            # ═══ alpha002 ═══

            if n >= 7:

                dlogvol = np.diff(np.log1p(volume[-(7+2):]))

                ret_open = (close[-(7):] - open_[-(7):]) / (open_[-(7):] + 1e-9)

                min_len = min(len(dlogvol[-6:]), len(ret_open[-6:]))

                if min_len >= 2:

                    feats["alpha002"] = -np.corrcoef(dlogvol[-min_len:], ret_open[-min_len:])[0, 1]

                else:

                    feats["alpha002"] = 0

            else:

                feats["alpha002"] = 0



            # ═══ alpha006 ═══

            if n >= 10:

                feats["alpha006"] = -(open_[-1] - open_[-10:].min()) + close[-10:].mean()

            else:

                feats["alpha006"] = 0



            # ═══ alpha008 ═══

            feats["alpha008"] = -(amt[-5:].sum() / (amt[-20:].sum() + 1e-9)) if n >= 20 else 0



            # ═══ alpha009 ═══

            ret5 = np.array([close[-1] / close[-6] - 1]) if n >= 6 else np.array([0])

            feats["alpha009"] = (abs(rets[-5:]).max() - abs(rets[-5:]).min()) if len(rets) >= 5 else 0



            # ═══ alpha012 ═══

            feats["alpha012"] = (volume[-10:].mean() - volume[-1]) / (volume[-10:].std() + 1e-9) if n >= 10 else 0



            # ═══ alpha014 ═══

            if n >= 13:

                feats["alpha014"] = -np.diff(open_[-(13):], n=3)[-10:].mean()

            else:

                feats["alpha014"] = 0



            # ═══ alpha017 ═══

            feats["alpha017"] = (high[-20:] / (np.roll(close, 1)[-20:] + 1e-9)).mean() if n >= 21 else 0



            # ═══ alpha020 ═══

            if n >= 10:

                feats["alpha020"] = -np.diff(open_[-(10):], n=5)[-5:].mean()

            else:

                feats["alpha020"] = 0



            # ═══ alpha023 ═══

            feats["alpha023"] = (high[-20:] - low[-20:]).mean() / (close[-1] + 1e-9) if n >= 20 else 0



            # ═══ alpha028 ═══

            feats["alpha028"] = 0  # complex, simplified



            # ═══ alpha033 ═══

            feats["alpha033"] = -rets[-5:].mean() if len(rets) >= 5 else 0



            # ═══ alpha038 ═══

            avg_price = (open_ + high + low + close) / 4

            feats["alpha038"] = avg_price[-1] - avg_price[-11] if n >= 11 else 0



            # ═══ alpha041 ═══

            if n >= 20:

                vwap = (amt[-20:]).sum() / (volume[-20:].sum() + 1e-9)

                feats["alpha041"] = (close[-1] - vwap) / (vwap + 1e-9)

            else:

                feats["alpha041"] = 0



            # ═══ alpha046 ═══

            if n >= 40:

                chg = (close[-1] - close[-21]) / (close[-21] + 1e-9)

                chgs = [(close[i] - close[i-20]) / (close[i-20] + 1e-9) for i in range(-20, 0)]

                feats["alpha046"] = -np.mean(chgs)

            else:

                feats["alpha046"] = 0



            # ═══ alpha049 ═══

            feats["alpha049"] = 0



            # ═══ alpha053 ═══

            feats["alpha053"] = ((close[-1] - low[-1]) - (high[-1] - close[-1])) / (high[-1] - low[-1] + 1e-9)



            # ═══ alpha054 ═══

            feats["alpha054"] = -(open_[-1] - close[-2]) / 10 if n >= 2 else 0



            # ═══ alpha064 ═══

            feats["alpha064"] = 0



            # ═══ alpha067 ═══

            if n >= 20:

                feats["alpha067"] = rets[-20:].mean() * (1 + volume[-1] / (volume[-20:].mean() + 1e-9))

            else:

                feats["alpha067"] = 0



            # ═══ alpha071 ═══

            feats["alpha071"] = close[-1] - 2 * close[-2] + close[-6] if n >= 6 else 0



            # ═══ alpha083 ═══

            if n >= 6:

                ratios = (high[-5:] - low[-5:]) / (np.roll(close, 1)[-5:] + 1e-9)

                feats["alpha083"] = ratios.mean()

            else:

                feats["alpha083"] = 0



            # ═══ 动量 & 分布 ═══

            for w in [5, 10, 20, 60]:

                arr = rets[-w:] if len(rets) >= w else rets

                if len(arr) >= 3:

                    feats[f"mom_ewm_{w}"] = pd.Series(arr).ewm(span=min(w, len(arr))).mean().iloc[-1]

                    feats[f"skew_{w}"] = pd.Series(arr).skew()

                    feats[f"kurt_{w}"] = pd.Series(arr).kurt()

                    up = (arr > 0).sum()

                    down = (arr < 0).sum()

                    feats[f"ud_ratio_{w}"] = up / (down + 1e-9)

                else:

                    feats[f"mom_ewm_{w}"] = 0

                    feats[f"skew_{w}"] = 0

                    feats[f"kurt_{w}"] = 0

                    feats[f"ud_ratio_{w}"] = 1



        # ═══ 换手率 & 规模 ═══

        feats["turnover_proxy"] = amt[-1] / (close[-60:].mean() * volume[-1] + 1e-9) if n >= 60 else amt[-1] / (close.mean() * volume[-1] + 1e-9)

        feats["size_proxy"] = np.log1p(amt[-1])



        # 取交集: 只返回模型训练时用的特征 (容忍缺失)

        result = pd.Series(feats)

        available = [f for f in self._feature_names if f in result.index]

        return result[available]



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



        logger.info(f"[PREDICT] 日期={target_date}, 股票池={len(stock_pool)} 只")


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

                logger.info(f"  [{i+1}/{len(stock_pool)}] 已完成...")


        if failed:

            logger.warning(f"  [WARN] {failed} 只股票预测失败")
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

