"""
因子相关性分析模块
用于分析多个因子之间的相关性，识别重复因子

功能：
1. 计算因子间的相关系数矩阵
2. 识别高相关性因子对
3. 聚类分析相似因子
4. 因子降维建议

集成自：EasyXT的alpha_analysis模块
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from scipy.spatial.distance import squareform
import warnings
warnings.filterwarnings('ignore')


class FactorCorrelationAnalyzer:
    """
    因子相关性分析器

    功能：
    1. 计算因子间的相关性（Pearson/Spearman）
    2. 识别高相关性因子对
    3. 层次聚类分析
    4. 生成去重建议
    """

    def __init__(self, factor_dict: Dict[str, pd.DataFrame]):
        """
        初始化因子相关性分析器

        参数：
        ----------
        factor_dict : Dict[str, pd.DataFrame]
            因子字典，key为因子名称，value为因子数据DataFrame
            格式：{factor_name: DataFrame(index=date, columns=stock_code)}
            或：{factor_name: Series(index=[date, symbol])} - MultiIndex格式
        """
        self.factor_dict = factor_dict
        self.factor_names = list(factor_dict.keys())

        # 对齐数据
        self._align_data()

        # 分析结果存储
        self.correlation_matrix = None
        self.high_corr_pairs = None
        self.cluster_result = None
        self.removal_suggestions = None

    def _align_data(self):
        """对齐所有因子的日期和股票"""
        # 获取共同的日期和股票
        common_dates = None
        common_stocks = None

        for factor_name, factor_data in self.factor_dict.items():
            # 处理MultiIndex格式（日期+股票代码）
            if isinstance(factor_data.index, pd.MultiIndex):
                factor_data = factor_data.unstack()
                if isinstance(factor_data, pd.DataFrame):
                    factor_data = factor_data.iloc[:, 0]  # 取第一列
                self.factor_dict[factor_name] = factor_data

            if common_dates is None:
                common_dates = set(factor_data.index)
                common_stocks = set(factor_data.columns)
            else:
                common_dates &= set(factor_data.index)
                common_stocks &= set(factor_data.columns)

        if not common_dates or not common_stocks:
            raise ValueError("因子之间没有共同的日期或股票")

        common_dates = sorted(common_dates)
        common_stocks = sorted(common_stocks)

        # 对齐所有因子数据
        self.aligned_factors = {}
        for factor_name, factor_data in self.factor_dict.items():
            aligned_data = factor_data.loc[common_dates, common_stocks]
            self.aligned_factors[factor_name] = aligned_data

        self.common_dates = common_dates
        self.common_stocks = common_stocks

    def calculate_correlation(
        self,
        method: str = 'spearman',
        time_window: Optional[int] = None
    ) -> pd.DataFrame:
        """
        计算因子间的相关系数矩阵

        参数：
        ----------
        method : str
            相关系数计算方法，'pearson'或'spearman'
        time_window : int, optional
            时间窗口，如果指定则计算滚动相关性
            如果为None，则使用全样本计算

        返回：
        ----------
        corr_matrix : pd.DataFrame
            因子相关系数矩阵
        """
        # 将因子数据展平
        factor_series = {}

        for factor_name, factor_data in self.aligned_factors.items():
            if time_window is None:
                # 全样本：展平所有数据
                factor_series[factor_name] = factor_data.stack().dropna()
            else:
                # 滚动窗口：只使用最近time_window期的数据
                recent_data = factor_data.iloc[-time_window:]
                factor_series[factor_name] = recent_data.stack().dropna()

        # 创建DataFrame计算相关性
        factor_df = pd.DataFrame(factor_series)

        # 计算相关系数
        self.correlation_matrix = factor_df.corr(method=method)

        return self.correlation_matrix

    def find_high_correlation_pairs(
        self,
        threshold: float = 0.7,
        method: str = 'spearman'
    ) -> List[Tuple[str, str, float]]:
        """
        识别高相关性因子对

        参数：
        ----------
        threshold : float
            相关系数阈值，默认0.7
        method : str
            相关系数计算方法

        返回：
        ----------
        high_corr_pairs : List[Tuple[str, str, float]]
            高相关性因子对列表，每个元素为(因子1, 因子2, 相关系数)
        """
        # 计算相关性矩阵
        if self.correlation_matrix is None:
            self.calculate_correlation(method=method)

        corr_matrix = self.correlation_matrix

        # 找出高相关性因子对（只取上三角，避免重复）
        high_corr_pairs = []

        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                factor1 = corr_matrix.columns[i]
                factor2 = corr_matrix.columns[j]
                corr_value = corr_matrix.iloc[i, j]

                if abs(corr_value) >= threshold:
                    high_corr_pairs.append((factor1, factor2, corr_value))

        # 按相关系数绝对值降序排序
        high_corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        self.high_corr_pairs = high_corr_pairs

        return high_corr_pairs

    def hierarchical_clustering(
        self,
        method: str = 'average',
        metric: str = 'euclidean',
        n_clusters: Optional[int] = None
    ) -> pd.Series:
        """
        层次聚类分析因子相似性

        参数：
        ----------
        method : str
            链接方法，'single', 'complete', 'average', 'weighted'
        metric : str
            距离度量，'euclidean', 'correlation'等
        n_clusters : int, optional
            聚类数量，如果为None则自动确定

        返回：
        ----------
        cluster_labels : pd.Series
            聚类标签，索引为因子名称
        """
        # 计算相关性矩阵
        if self.correlation_matrix is None:
            self.calculate_correlation()

        # 转换为距离矩阵（距离 = 1 - |相关系数|）
        distance_matrix = 1 - abs(self.correlation_matrix)

        # 层次聚类
        linkage_matrix = linkage(
            squareform(distance_matrix),
            method=method
        )

        # 确定聚类数量
        if n_clusters is None:
            # 使用最大距离法确定聚类数量
            n_clusters = max(1, len(self.factor_names) // 3)

        # 分配聚类标签
        cluster_labels = fcluster(
            linkage_matrix,
            t=n_clusters,
            criterion='maxclust'
        )

        self.cluster_result = pd.Series(
            cluster_labels,
            index=self.factor_names,
            name='cluster'
        )

        return self.cluster_result

    def generate_removal_suggestions(
        self,
        threshold: float = 0.7,
        method: str = 'spearman',
        keep_criteria: str = 'name'
    ) -> Dict[str, List[str]]:
        """
        生成因子去重建议

        参数：
        ----------
        threshold : float
            相关系数阈值
        method : str
            相关系数计算方法
        keep_criteria : str
            保留因子标准：
            - 'name': 按名称顺序保留第一个
            - 'ic_mean': 按IC均值保留（需要额外传入IC数据）

        返回：
        ----------
        suggestions : Dict[str, List[str]]
            去重建议字典，key为保留因子，value为建议删除的因子列表
        """
        # 找出高相关性因子对
        high_corr_pairs = self.find_high_correlation_pairs(
            threshold=threshold,
            method=method
        )

        if not high_corr_pairs:
            print(f"没有发现相关性超过{threshold}的因子对")
            self.removal_suggestions = {}
            return self.removal_suggestions

        # 构建因子分组
        factor_groups = []
        factor_set = set(self.factor_names)

        for factor1, factor2, corr in high_corr_pairs:
            # 查找这两个因子是否已经在某个组中
            found_group = None
            for group in factor_groups:
                if factor1 in group or factor2 in group:
                    found_group = group
                    break

            if found_group is not None:
                found_group.add(factor1)
                found_group.add(factor2)
            else:
                factor_groups.append({factor1, factor2})

        # 生成去重建议
        suggestions = {}
        removed_factors = set()

        for group in factor_groups:
            # 移除已经处理过的因子
            group = group - removed_factors

            if len(group) <= 1:
                continue

            # 确定保留哪个因子
            if keep_criteria == 'name':
                # 按名称字母顺序保留第一个
                keep_factor = sorted(group)[0]
            else:
                # 默认按名称顺序
                keep_factor = sorted(group)[0]

            # 建议删除的因子
            remove_factors = group - {keep_factor}
            suggestions[keep_factor] = sorted(remove_factors)
            removed_factors.update(remove_factors)

        self.removal_suggestions = suggestions

        return suggestions

    def generate_report(self) -> pd.DataFrame:
        """
        生成相关性分析报告

        返回：
        ----------
        report : pd.DataFrame
            相关性分析报告
        """
        if self.high_corr_pairs is None:
            self.find_high_correlation_pairs()

        # 创建报告数据
        report_data = []

        for factor1, factor2, corr in self.high_corr_pairs:
            report_data.append({
                '因子1': factor1,
                '因子2': factor2,
                '相关系数': f"{corr:.4f}",
                '相关强度': self._get_correlation_strength(corr),
                '建议': '考虑去除其中一个' if abs(corr) > 0.8 else '可保留'
            })

        if not report_data:
            print("没有发现高相关性因子对")
            return pd.DataFrame()

        report = pd.DataFrame(report_data)

        return report

    def print_report(self, threshold: float = 0.7):
        """
        打印相关性分析报告

        参数：
        ----------
        threshold : float
            相关系数阈值
        """
        print("=" * 100)
        print("因子相关性分析报告")
        print("=" * 100)

        # 计算相关性矩阵
        if self.correlation_matrix is None:
            self.calculate_correlation()

        print(f"\n因子数量: {len(self.factor_names)}")
        print(f"共同日期范围: {self.common_dates[0]} 至 {self.common_dates[-1]}")
        print(f"共同股票数量: {len(self.common_stocks)}")

        # 找出高相关性因子对
        high_corr_pairs = self.find_high_correlation_pairs(threshold=threshold)

        if not high_corr_pairs:
            print(f"\n[OK] 没有发现相关性超过{threshold}的因子对，所有因子都是独立的！")
        else:
            print(f"\n发现 {len(high_corr_pairs)} 对高相关性因子：\n")
            print(f"{'因子1':<25} {'因子2':<25} {'相关系数':<15} {'相关强度':<15}")
            print("-" * 100)

            for factor1, factor2, corr in high_corr_pairs:
                strength = self._get_correlation_strength(corr)
                print(f"{factor1:<25} {factor2:<25} {corr:>14.4f}     {strength:<15}")

        # 生成去重建议
        suggestions = self.generate_removal_suggestions(threshold=threshold)

        if suggestions:
            print("\n" + "=" * 100)
            print("去重建议：")
            print("=" * 100)

            for keep_factor, remove_factors in suggestions.items():
                print(f"\n保留因子: {keep_factor}")
                print(f"  建议删除: {', '.join(remove_factors)}")
        else:
            print("\n[OK] 无需去重")

        # 聚类分析
        print("\n" + "=" * 100)
        print("层次聚类分析：")
        print("=" * 100)

        cluster_result = self.hierarchical_clustering()

        print("\n因子分组：")
        for cluster_id in sorted(cluster_result.unique()):
            factors_in_cluster = cluster_result[cluster_result == cluster_id].index.tolist()
            print(f"  簇 {cluster_id}: {', '.join(factors_in_cluster)}")

        print("=" * 100)

    def _get_correlation_strength(self, corr: float) -> str:
        """获取相关性强度描述"""
        abs_corr = abs(corr)
        if abs_corr >= 0.9:
            return "极强"
        elif abs_corr >= 0.7:
            return "强"
        elif abs_corr >= 0.5:
            return "中等"
        elif abs_corr >= 0.3:
            return "弱"
        else:
            return "极弱"

    def save_correlation_matrix(self, filepath: str):
        """保存相关系数矩阵到文件"""
        if self.correlation_matrix is None:
            self.calculate_correlation()

        self.correlation_matrix.to_csv(filepath)
        print(f"相关系数矩阵已保存到: {filepath}")

    def save_report(self, filepath: str, threshold: float = 0.7):
        """保存分析报告到文件"""
        report = self.generate_report()
        report.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"相关性分析报告已保存到: {filepath}")
