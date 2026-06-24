import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

DuckDB 原生 LightGBM 训练器



直接从 DuckDB 读取数据 + 现有因子系统生成特征 → LightGBM 训练。

无需 Qlib，零数据转换。



使用方法:

  from easyxt_backtest.ml import DuckDBModelTrainer



  trainer = DuckDBModelTrainer()

  # 训练

  model, metrics = trainer.train(stock_pool='all', train_start='2020-01-01',

                                  train_end='2023-12-31')

  # 保存

  trainer.save('models/mymodel.pkl')

"""



import sys

import pickle

import warnings

from pathlib import Path

from datetime import datetime, timedelta

from typing import List, Optional, Dict, Tuple



import pandas as pd

import numpy as np



warnings.filterwarnings("ignore")



_project_root = Path(__file__).parent.parent.parent

sys.path.insert(0, str(_project_root))





class DuckDBModelTrainer:

    """基于 DuckDB 的 LightGBM 训练器



    核心流程:

      1. 从 DuckDB 批量加载 OHLCV 数据

      2. 计算技术因子作为特征 (alpha101/191 因子 + 技术指标)

      3. 构造标签: 未来 T+1~T+5 日收益率

      4. LightGBM 训练 (回归)

      5. 保存模型 + 评估指标



    参数:

      db_path:    DuckDB 数据库路径 (默认从 .env 读取)

      n_estimators: LightGBM 树的数量

      learning_rate: 学习率

      label_horizon: 预测未来 N 日的收益率 (默认 5)

    """



    def __init__(

        self,

        db_path: str = None,

        n_estimators: int = 300,

        learning_rate: float = 0.05,

        num_leaves: int = 63,

        label_horizon: int = 5,

        min_data_per_stock: int = 100,

    ):

        if db_path is None:

            from config.env_config import get_default_db_path

            db_path = get_default_db_path()



        self.db_path = db_path

        self.n_estimators = n_estimators

        self.learning_rate = learning_rate

        self.num_leaves = num_leaves

        self.label_horizon = label_horizon

        self.min_data_per_stock = min_data_per_stock



        self._model = None

        self._metrics = {}

        self._feature_names = []



    def _connect_duckdb(self):

        """连接 DuckDB (只读)"""

        import duckdb

        return duckdb.connect(self.db_path, read_only=True)



    # ─── 数据加载 ──────────────────────────────────────



    def load_data(

        self,

        stock_pool: List[str] = None,

        start_date: str = "2020-01-01",

        end_date: str = "2023-12-31",

    ) -> pd.DataFrame:

        """从 DuckDB 批量加载日线数据



        Args:

            stock_pool: 股票列表 (None=全市场)

            start_date: 起始日期

            end_date:   结束日期



        Returns:

            DataFrame with columns: stock_code, date, open, high, low, close, volume

        """

        con = self._connect_duckdb()

        try:

            where = [f"date >= '{start_date}'", f"date <= '{end_date}'",

                      "period = '1d'"]

            if stock_pool:

                codes = "', '".join(stock_pool)

                where.append(f"stock_code IN ('{codes}')")



            query = f"""

                SELECT stock_code, CAST(date AS VARCHAR) as date,

                       open, high, low, close, volume

                FROM stock_daily

                WHERE {' AND '.join(where)}

                ORDER BY stock_code, date

            """

            df = con.execute(query).df()

            print(f"[LOAD] {len(df):,} rows, {df['stock_code'].nunique()} stocks, "

                  f"{df['date'].nunique()} days")

            return df

        finally:

            con.close()



    # ─── 特征计算 ──────────────────────────────────────



    def compute_features(self, df: pd.DataFrame, fast_mode: bool = False) -> pd.DataFrame:

        """从 OHLCV 批量计算因子特征



        与项目 alpha101/191 因子库互补，使用纯 pandas 批量计算。

        fast_mode=True 时只算基础 17 因子（快速验证用），

        fast_mode=False 时算 ~80 因子（包含 alpha 类因子）。



        Args:

            df: load_data() 返回的 OHLCV DataFrame

            fast_mode: 是否快速模式



        Returns:

            特征 DataFrame

        """

        mode = "快速" if fast_mode else "完整"

        logger.info(f"[FEAT] 计算特征 ({mode}模式)...")
        df = df.sort_values(["stock_code", "date"]).copy()



        g = df.groupby("stock_code")

        o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]



        # ═══ 收益率类 ═══

        df["ret_1d"] = g["close"].pct_change(1)

        df["ret_5d"] = g["close"].pct_change(5)

        df["ret_20d"] = g["close"].pct_change(20)



        # ═══ 均线偏离 ═══

        for w in [5, 10, 20, 60]:

            ma = g["close"].transform(lambda x: x.rolling(w, min_periods=1).mean())

            df[f"ma{w}_bias"] = (c - ma) / (ma + 1e-9)



        # ═══ 波动率 ═══

        for w in [5, 10, 20]:

            df[f"vol_{w}d"] = df["ret_1d"].rolling(w, min_periods=5).std()



        # ═══ 量价关系 ═══

        for w in [5, 10, 20]:

            df[f"vol_ratio_{w}"] = v / (g["volume"].transform(

                lambda x: x.rolling(w, min_periods=1).mean()) + 1e-9)



        df["amount"] = v * c

        for w in [5, 10]:

            df[f"amount_ratio_{w}"] = df["amount"] / (

                g["amount"].transform(lambda x: x.rolling(w, min_periods=1).mean()) + 1e-9)



        # ═══ 价格位置 ═══

        df["high_low_ratio"] = (h - l) / (c + 1e-9)

        for w in [10, 20, 60]:

            rh = g["high"].transform(lambda x: x.rolling(w, min_periods=1).max())

            rl = g["low"].transform(lambda x: x.rolling(w, min_periods=1).min())

            df[f"close_pos_{w}"] = (c - rl) / (rh - rl + 1e-9)



        # ═══ RSI ═══

        for w in [6, 14, 24]:

            delta = g["close"].diff()

            gain = delta.clip(lower=0).rolling(w, min_periods=1).mean()

            loss = (-delta).clip(lower=0).rolling(w, min_periods=1).mean()

            df[f"rsi_{w}"] = 100 - 100 / (1 + gain / (loss + 1e-9))



        if not fast_mode:

            # ═══ 扩展因子 (alpha101/191 类) ═══



            # --- alpha001: 反转信号 ---

            ret_std20 = df["ret_1d"].rolling(20, min_periods=5).std()

            df["alpha001"] = (c.where(df["ret_1d"] < 0, ret_std20) ** 2).rolling(5).apply(

                lambda x: x.argmax(), raw=True

            ) / 5 - 0.5



            # --- alpha002: 量价相关性 ---

            dlogvol = np.log1p(v).diff(2)

            ret_open = (c - o) / (o + 1e-9)

            df["alpha002"] = -dlogvol.rolling(6).corr(ret_open)



            # --- alpha006: 开盘价突破 ---

            df["alpha006"] = -g["open"].transform(

                lambda x: (x - x.rolling(10, min_periods=1).min()).corr(

                    c.loc[x.index].rolling(10, min_periods=1).mean()))



            # --- alpha008: 量价动量和 ---

            df["alpha008"] = -((v * c).rolling(5).sum() / v.rolling(20).sum())



            # --- alpha009: 极端收益 ---

            df["alpha009"] = (c.where(df["ret_1d"] < 0, df["ret_5d"]).rolling(5).max() -

                               c.where(df["ret_1d"] > 0, df["ret_5d"]).rolling(5).min())



            # --- alpha012: 成交量信号 ---

            df["alpha012"] = (v.rolling(10).mean() - v) / (v.rolling(10).std() + 1e-9)



            # --- alpha014: 开盘价动量 ---

            df["alpha014"] = -g["open"].transform(

                lambda x: x.diff(3).rolling(10, min_periods=1).mean())



            # --- alpha017: 最高/收盘比 ---

            df["alpha017"] = (h / (c.shift(1) + 1e-9)).rolling(20).mean()



            # --- alpha020: 延迟信号 ---

            df["alpha020"] = -g["open"].transform(

                lambda x: x.diff(5).rolling(5, min_periods=1).mean())



            # --- alpha023: 高低价差 ---

            df["alpha023"] = (h - l).rolling(20).mean() / c



            # --- alpha028: 量价背离 ---

            df["alpha028"] = (c.rolling(10).mean() / c).rolling(20).corr(

                v.rolling(10).mean() / v)



            # --- alpha033: 反转 ---

            df["alpha033"] = -g["close"].pct_change(5).rolling(5).mean()



            # --- alpha038: 均价 ---

            df["alpha038"] = (o + h + l + c) / 4

            df["alpha038"] = df["alpha038"].diff(10)



            # --- alpha041: VWAP ---

            vwap = (v * c).rolling(20).sum() / (v.rolling(20).sum() + 1e-9)

            df["alpha041"] = (c - vwap) / (vwap + 1e-9)



            # --- alpha046: 窄幅突破 ---

            df["alpha046"] = -((c - c.shift(20)) / (c.shift(20) + 1e-9)).rolling(20).mean()



            # --- alpha049: 日内波动 ---

            df["alpha049"] = ((h + l) / 2 - c.shift(1)).rolling(20).std()



            # --- alpha053: 尾部风险 ---

            df["alpha053"] = ((c - l) - (h - c)) / ((h - l) + 1e-9)



            # --- alpha054: 开盘反转 ---

            df["alpha054"] = -(o - c.shift(1)).rolling(10).mean()



            # --- alpha064: 量能减弱 ---

            df["alpha064"] = df["ret_1d"].rolling(20).corr(v.rolling(20).mean())



            # --- alpha067: 加权动量 ---

            df["alpha067"] = df["ret_1d"].rolling(20).mean() * (1 + v / (v.rolling(20).mean() + 1e-9))



            # --- alpha071: 加速 ---

            df["alpha071"] = df["close"].diff(1).diff(5)



            # --- alpha083: 振幅 ---

            df["alpha083"] = (h - l) / (c.shift(1) + 1e-9)

            df["alpha083"] = df["alpha083"].rolling(5).mean()



        # ═══ 换手率 & 规模 ═══

        amt = v * c

        df["turnover_proxy"] = amt / (g["close"].transform(

            lambda x: x.rolling(60, min_periods=1).mean()) * v + 1e-9)

        df["size_proxy"] = np.log1p(amt)



        # ═══ 动量因子 (alpha191 类) ═══

        if not fast_mode:

            for w in [5, 10, 20, 60]:

                # 指数加权动量

                df[f"mom_ewm_{w}"] = g["close"].transform(

                    lambda x: x.pct_change(w).ewm(span=w).mean())

                # 偏度（min_periods 至少为 min(w, 3)）

                mp = min(w, max(5, 3))

                df[f"skew_{w}"] = df["ret_1d"].rolling(w, min_periods=mp).skew()

                # 峰度

                df[f"kurt_{w}"] = df["ret_1d"].rolling(w, min_periods=mp).kurt()

                # 涨跌比

                up = (df["ret_1d"] > 0).astype(float).rolling(w).sum()

                down = (df["ret_1d"] < 0).astype(float).rolling(w).sum()

                df[f"ud_ratio_{w}"] = up / (down + 1e-9)



        # 删除中间列

        drop_cols = ["open", "high", "low", "close", "volume", "amount"]

        df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")



        self._feature_names = [c for c in df.columns

                               if c not in ("stock_code", "date", "label")]

        logger.info(f"  [OK] {len(self._feature_names)} 个特征")
        return df



    # ─── 标签构造 ──────────────────────────────────────



    def compute_labels(self, df: pd.DataFrame) -> pd.DataFrame:

        """构造预测标签: 未来 T+N 日收益率



        必须在 compute_features() 之后调用 (需要 close 列存在)。

        调用前确保 close 列未被删除。



        Args:

            df: 含 close 列的 DataFrame



        Returns:

            含 label 列的 DataFrame

        """

        logger.info(f"[LABEL] 构造标签 (T+{self.label_horizon})...")
        df = df.sort_values(["stock_code", "date"]).copy()



        g = df.groupby("stock_code")

        # 未来 N 日累计收益率

        df["label"] = g["close"].transform(

            lambda x: x.shift(-self.label_horizon) / x - 1

        )

        return df



    # ─── 训练 ──────────────────────────────────────────



    def train(

        self,

        stock_pool: List[str] = None,

        train_start: str = "2020-01-01",

        train_end: str = "2022-12-31",

        valid_start: str = "2023-01-01",

        valid_end: str = "2023-12-31",

    ) -> Tuple[object, Dict]:

        """训练 LightGBM 模型



        Args:

            stock_pool:  股票列表 (None=全市场)

            train_start, train_end: 训练集区间

            valid_start, valid_end: 验证集区间



        Returns:

            (model, metrics_dict)

        """

        logger.info("=" * 60)
        logger.info("DuckDB LightGBM 训练")
        logger.info("=" * 60)
        logger.info(f"训练集: {train_start} ~ {train_end}")
        logger.info(f"验证集: {valid_start} ~ {valid_end}")
        logger.info(f"标签:   未来 {self.label_horizon} 日收益")
        logger.info(f"模型:   LightGBM (n_est={self.n_estimators}, lr={self.learning_rate})")


        # 1. 加载训练数据

        logger.info("\n[1/5] 加载训练数据...")
        train_df = self.load_data(stock_pool, train_start, train_end)



        # 2. 标签计算 (必须在特征之前，因为需要 close 列)

        logger.info("[2/5] 特征工程...")
        train_df = self.compute_labels(train_df)

        train_df = self.compute_features(train_df)



        # 3. 加载验证数据

        logger.info("[3/5] 加载验证数据...")
        valid_df = self.load_data(stock_pool, valid_start, valid_end)

        valid_df = self.compute_labels(valid_df)

        valid_df = self.compute_features(valid_df)



        # 4. 准备训练

        logger.info("[4/5] 训练 LightGBM...")
        # 去掉 NaN

        feature_cols = self._feature_names

        train_df = train_df.dropna(subset=feature_cols + ["label"])

        valid_df = valid_df.dropna(subset=feature_cols + ["label"])



        X_train = train_df[feature_cols].values.astype(np.float32)

        y_train = train_df["label"].values.astype(np.float32)

        X_valid = valid_df[feature_cols].values.astype(np.float32)

        y_valid = valid_df["label"].values.astype(np.float32)



        logger.info(f"  训练样本: {len(X_train):,}")
        logger.info(f"  验证样本: {len(X_valid):,}")
        logger.info(f"  特征维度: {len(feature_cols)}")


        # 去掉极端标签 (>100% 或 <-80%)

        mask_train = (y_train > -0.8) & (y_train < 1.0)

        mask_valid = (y_valid > -0.8) & (y_valid < 1.0)

        X_train, y_train = X_train[mask_train], y_train[mask_train]

        X_valid, y_valid = X_valid[mask_valid], y_valid[mask_valid]

        logger.info(f"  过滤极端值后: train={len(X_train):,}, valid={len(X_valid):,}")


        if len(X_valid) == 0:

            logger.warning("  [WARN] 验证集为空，使用训练集的一部分作为验证集")
            split = int(len(X_train) * 0.8)

            X_valid, y_valid = X_train[split:], y_train[split:]

            X_train, y_train = X_train[:split], y_train[:split]

            logger.info(f"  重新划分: train={len(X_train):,}, valid={len(X_valid):,}")


        # LightGBM 训练

        t0 = datetime.now()

        import lightgbm as lgb



        model = lgb.LGBMRegressor(

            n_estimators=self.n_estimators,

            learning_rate=self.learning_rate,

            num_leaves=self.num_leaves,

            subsample=0.8,

            colsample_bytree=0.8,

            reg_alpha=0.1,

            reg_lambda=0.1,

            min_child_samples=20,

            random_state=42,

            verbose=-1,

        )

        model.fit(

            X_train, y_train,

            eval_set=[(X_valid, y_valid)],

            eval_metric="rmse",

        )



        elapsed = (datetime.now() - t0).total_seconds()

        self._model = model



        # 5. 评估

        logger.info(f"[5/5] 评估 (训练耗时 {elapsed:.0f}s)")
        y_pred = model.predict(X_valid)



        from scipy.stats import pearsonr, spearmanr

        ic = pearsonr(y_valid, y_pred)[0]

        rank_ic = spearmanr(y_valid, y_pred)[0]



        # Top/Bottom 分组收益

        n = len(y_pred)

        top_n = max(int(n * 0.2), 1)

        sorted_idx = np.argsort(y_pred)

        top_pred = sorted_idx[-top_n:]

        bottom_pred = sorted_idx[:top_n]



        self._metrics = {

            "IC": round(ic, 4),

            "Rank_IC": round(rank_ic, 4),

            "train_samples": len(X_train),

            "valid_samples": len(X_valid),

            "features": len(feature_cols),

            "top20_mean_ret": round(float(y_valid[top_pred].mean() * 100), 3),

            "bottom20_mean_ret": round(float(y_valid[bottom_pred].mean() * 100), 3),

            "training_time_s": round(elapsed, 1),

        }



        logger.info("\n" + "=" * 60)
        logger.info("训练结果")
        logger.info("=" * 60)
        for k, v in self._metrics.items():

            logger.info(f"  {k}: {v}")
        logger.info("=" * 60)


        return model, self._metrics



    # ─── 保存 / 加载 ───────────────────────────────────



    def save(self, path: str = None):

        """保存模型到文件"""

        if self._model is None:

            raise RuntimeError("请先调用 train() 训练模型")

        if path is None:

            path = _project_root / "easyxt_backtest" / "ml" / "models" / "lightgbm_model.pkl"

        path = Path(path)

        path.parent.mkdir(parents=True, exist_ok=True)



        package = {

            "model": self._model,

            "feature_names": self._feature_names,

            "metrics": self._metrics,

            "label_horizon": self.label_horizon,

            "n_estimators": self.n_estimators,

            "learning_rate": self.learning_rate,

            "num_leaves": self.num_leaves,

            "created_at": datetime.now().isoformat(),

        }

        with open(path, "wb") as f:

            pickle.dump(package, f)

        logger.info(f"[SAVE] 模型已保存: {path}")


    def load(self, path: str):

        """加载已保存的模型"""

        path = Path(path)

        if not path.exists():

            raise FileNotFoundError(f"模型不存在: {path}")

        with open(path, "rb") as f:

            package = pickle.load(f)

        self._model = package["model"]

        self._feature_names = package["feature_names"]

        self._metrics = package.get("metrics", {})

        self.label_horizon = package.get("label_horizon", 5)

        logger.info(f"[LOAD] 模型已加载: {path}")
        logger.info(f"  特征: {len(self._feature_names)} 维")
        if self._metrics:

            logger.info(f"  IC: {self._metrics.get('IC', 'N/A')}")


    def get_model(self):

        return self._model



    def get_metrics(self) -> Dict:

        return self._metrics



    def get_feature_names(self) -> List[str]:

        return self._feature_names





# ─── CLI ───────────────────────────────────────────────



def main():

    import argparse

    parser = argparse.ArgumentParser(description="DuckDB LightGBM 训练器")

    parser.add_argument("--stock-pool", type=str, default=None,

                        help="股票池文件 (每行一个代码, 默认全市场)")

    parser.add_argument("--train-start", type=str, default="2020-01-01")

    parser.add_argument("--train-end", type=str, default="2022-12-31")

    parser.add_argument("--valid-start", type=str, default="2023-01-01")

    parser.add_argument("--valid-end", type=str, default="2023-12-31")

    parser.add_argument("--n-estimators", type=int, default=300)

    parser.add_argument("--lr", type=float, default=0.05)

    parser.add_argument("--label-horizon", type=int, default=5,

                        help="预测未来 N 日收益")

    parser.add_argument("--output", type=str, default=None)

    args = parser.parse_args()



    stock_pool = None

    if args.stock_pool:

        with open(args.stock_pool) as f:

            stock_pool = [line.strip() for line in f if line.strip()]



    trainer = DuckDBModelTrainer(

        n_estimators=args.n_estimators,

        learning_rate=args.lr,

        label_horizon=args.label_horizon,

    )

    trainer.train(stock_pool, args.train_start, args.train_end,

                   args.valid_start, args.valid_end)

    trainer.save(args.output)





if __name__ == "__main__":

    main()

