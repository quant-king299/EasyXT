# -*- coding: utf-8 -*-
"""
性能分析器 - 计算回测性能指标
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


class PerformanceAnalyzer:
    """
    性能分析器

    计算各种回测性能指标：
    - 收益率指标（总收益、年化收益）
    - 风险指标（最大回撤、波动率）
    - 风险调整收益（夏普比率、卡尔玛比率）
    """

    def __init__(self, risk_free_rate: float = 0.03):
        """
        初始化性能分析器

        Args:
            risk_free_rate: 无风险利率（默认3%）
        """
        self.risk_free_rate = risk_free_rate

    def analyze(self,
                returns: pd.Series,
                initial_cash: float = 1000000) -> Dict[str, float]:
        """
        分析性能

        Args:
            returns: 每日收益率序列
            initial_cash: 初始资金

        Returns:
            性能指标字典
        """
        if returns.empty:
            return self._empty_metrics()

        # 收益率指标
        total_return = self._calculate_total_return(returns)
        annual_return = self._calculate_annual_return(returns, len(returns))

        # 风险指标
        max_drawdown = self._calculate_max_drawdown(returns)
        volatility = self._calculate_volatility(returns)

        # 风险调整收益
        sharpe_ratio = self._calculate_sharpe_ratio(returns, volatility)
        calmar_ratio = self._calculate_calmar_ratio(annual_return, max_drawdown)

        # 最终资产
        final_value = initial_cash * (1 + total_return)

        # 汇总
        metrics = {
            # 收益指标
            'total_return': total_return,
            'annual_return': annual_return,
            'initial_cash': initial_cash,
            'final_value': final_value,

            # 风险指标
            'max_drawdown': max_drawdown,
            'volatility': volatility,

            # 风险调整收益
            'sharpe_ratio': sharpe_ratio,
            'calmar_ratio': calmar_ratio,

            # 其他
            'total_days': len(returns),
            'positive_days': (returns > 0).sum(),
            'negative_days': (returns < 0).sum(),
        }

        return metrics

    def _empty_metrics(self) -> Dict[str, float]:
        """返回空指标"""
        return {
            'total_return': 0.0,
            'annual_return': 0.0,
            'max_drawdown': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'calmar_ratio': 0.0,
            'initial_cash': 0.0,
            'final_value': 0.0,
            'total_days': 0,
            'positive_days': 0,
            'negative_days': 0,
        }

    # ==================== 收益率计算 ====================

    def _calculate_total_return(self, returns: pd.Series) -> float:
        """
        计算总收益率

        公式：(1 + r1) * (1 + r2) * ... * (1 + rn) - 1
        """
        if returns.empty:
            return 0.0

        return (1 + returns).prod() - 1

    def _calculate_annual_return(self,
                                  returns: pd.Series,
                                  n_days: int) -> float:
        """
        计算年化收益率

        公式：(1 + total_return) ^ (252 / n_days) - 1

        Args:
            returns: 收益率序列
            n_days: 交易日数量
        """
        if returns.empty or n_days == 0:
            return 0.0

        total_return = self._calculate_total_return(returns)

        # 假设一年有252个交易日
        trading_days_per_year = 252
        years = n_days / trading_days_per_year

        if years == 0:
            return 0.0

        return (1 + total_return) ** (1 / years) - 1

    # ==================== 风险指标计算 ====================

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """
        计算最大回撤

        回撤 = (峰值 - 当前值) / 峰值

        最大回撤 = max(所有回撤)
        """
        if returns.empty:
            return 0.0

        # 计算累计净值
        cumulative = (1 + returns).cumprod()

        # 计算历史最高点
        running_max = cumulative.expanding().max()

        # 计算回撤
        drawdown = (cumulative - running_max) / running_max

        # 最大回撤（取最小值，因为回撤是负数）
        return drawdown.min()

    def _calculate_volatility(self,
                               returns: pd.Series,
                               annualize: bool = True) -> float:
        """
        计算波动率（标准差）

        Args:
            returns: 收益率序列
            annualize: 是否年化

        Returns:
            波动率
        """
        if returns.empty:
            return 0.0

        vol = returns.std()

        if annualize:
            # 年化：乘以sqrt(252)
            vol = vol * np.sqrt(252)

        return vol

    # ==================== 风险调整收益计算 ====================

    def _calculate_sharpe_ratio(self,
                                returns: pd.Series,
                                volatility: float) -> float:
        """
        计算夏普比率

        公式：(年化收益率 - 无风险利率) / 年化波动率

        Args:
            returns: 收益率序列
            volatility: 年化波动率

        Returns:
            夏普比率
        """
        if returns.empty or volatility == 0:
            return 0.0

        # 计算年化收益率
        annual_return = self._calculate_annual_return(returns, len(returns))

        # 夏普比率
        sharpe = (annual_return - self.risk_free_rate) / volatility

        return sharpe

    def _calculate_calmar_ratio(self,
                                 annual_return: float,
                                 max_drawdown: float) -> float:
        """
        计算卡尔玛比率

        公式：年化收益率 / |最大回撤|

        Args:
            annual_return: 年化收益率
            max_drawdown: 最大回撤（负数）

        Returns:
            卡尔玛比率
        """
        if max_drawdown == 0:
            return 0.0

        return annual_return / abs(max_drawdown)

    # ==================== 其他指标 ====================

    def calculate_win_rate(self, returns: pd.Series) -> float:
        """
        计算胜率

        公式：盈利天数 / 总天数

        Args:
            returns: 收益率序列

        Returns:
            胜率（0-1之间）
        """
        if returns.empty:
            return 0.0

        positive_days = (returns > 0).sum()
        total_days = len(returns)

        return positive_days / total_days if total_days > 0 else 0.0

    def calculate_profit_loss_ratio(self, returns: pd.Series) -> float:
        """
        计算盈亏比

        公式：平均盈利 / 平均亏损

        Args:
            returns: 收益率序列

        Returns:
            盈亏比
        """
        if returns.empty:
            return 0.0

        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]

        if positive_returns.empty or negative_returns.empty:
            return 0.0

        avg_profit = positive_returns.mean()
        avg_loss = abs(negative_returns.mean())

        return avg_profit / avg_loss if avg_loss != 0 else 0.0

    # ==================== 详细报告 ====================

    def generate_detailed_report(self,
                                  returns: pd.Series,
                                  initial_cash: float = 1000000) -> str:
        """
        生成详细的性能报告

        Args:
            returns: 收益率序列
            initial_cash: 初始资金

        Returns:
            报告字符串
        """
        metrics = self.analyze(returns, initial_cash)

        report = []
        report.append("="*70)
        report.append("回测性能报告")
        report.append("="*70)

        # 收益指标
        report.append("\n【收益指标】")
        report.append(f"总收益率:     {metrics['total_return']:>10.2%}")
        report.append(f"年化收益率:   {metrics['annual_return']:>10.2%}")
        report.append(f"初始资金:     {metrics['initial_cash']:>10,.2f} 元")
        report.append(f"最终资金:     {metrics['final_value']:>10,.2f} 元")

        # 风险指标
        report.append("\n【风险指标】")
        report.append(f"最大回撤:     {metrics['max_drawdown']:>10.2%}")
        report.append(f"波动率:       {metrics['volatility']:>10.2%}")

        # 风险调整收益
        report.append("\n【风险调整收益】")
        report.append(f"夏普比率:     {metrics['sharpe_ratio']:>10.2f}")
        report.append(f"卡尔玛比率:   {metrics['calmar_ratio']:>10.2f}")

        # 交易统计
        report.append("\n【交易统计】")
        report.append(f"总交易日:     {metrics['total_days']:>10} 天")
        report.append(f"盈利天数:     {metrics['positive_days']:>10} 天")
        report.append(f"亏损天数:     {metrics['negative_days']:>10} 天")

        # 胜率和盈亏比
        win_rate = self.calculate_win_rate(returns)
        profit_loss_ratio = self.calculate_profit_loss_ratio(returns)
        report.append(f"胜率:         {win_rate:>10.2%}")
        report.append(f"盈亏比:       {profit_loss_ratio:>10.2f}")

        report.append("\n" + "="*70)

        return "\n".join(report)

    # ==================== HTML 报告 ====================

    def generate_html_report(self,
                              daily_df: pd.DataFrame,
                              trades_df: pd.DataFrame,
                              strategy_name: str = "策略回测",
                              symbol: str = "",
                              date_range: str = "",
                              initial_cash: float = 1_000_000,
                              output_path: str = "") -> str:
        """
        生成独立 HTML 回测报告（含 SVG 净值曲线和回撤图）

        Args:
            daily_df: 日净值 DataFrame，需含 date 和 total 列
            trades_df: 交易记录 DataFrame，需含 date, action, price, shares 列
            strategy_name: 策略名称
            symbol: 标的代码
            date_range: 回测区间描述（如 "2024-07-01 → 2025-07-01"）
            initial_cash: 初始资金
            output_path: 输出路径。为空则自动存到 easyxt_backtest/output/

        Returns:
            HTML 文件路径
        """
        import numpy as np
        from pathlib import Path as _Path

        daily = daily_df.copy()
        trades = trades_df.copy()
        daily["date"] = pd.to_datetime(daily["date"])
        trades["date"] = pd.to_datetime(trades["date"])

        # --- 计算指标 ---
        nav = (daily["total"] / initial_cash).values
        dates = daily["date"].dt.strftime("%Y-%m-%d").values
        cummax = np.maximum.accumulate(nav)
        dd = (nav - cummax) / cummax

        total_return = nav[-1] - 1
        ar = (nav[-1]) ** (252 / max(len(nav), 1)) - 1
        max_dd = dd.min()
        daily_ret = np.diff(nav) / nav[:-1]
        std_ret = np.std(daily_ret) if len(daily_ret) > 0 else 1e-9
        sharpe = np.mean(daily_ret) / std_ret * np.sqrt(252) if std_ret > 0 else 0
        calmar = ar / abs(max_dd) if max_dd != 0 else 0
        annual_vol = std_ret * np.sqrt(252)
        final_value = nav[-1] * initial_cash
        buy_count = len(trades[trades["action"] == "BUY"])
        sell_count = len(trades[trades["action"] == "SELL"])

        # --- SVG 净值曲线 ---
        w, h = 800, 350
        pad = 60
        step = max(1, len(nav) // 200)
        x_scale = (w - 2 * pad) / max(len(nav) - 1, 1)
        y_min, y_max = min(nav) * 0.98, max(nav) * 1.02
        y_range = max(y_max - y_min, 1e-9)

        def yp(v):
            return h - pad - (v - y_min) / y_range * (h - 2 * pad)

        nav_pts = " ".join(
            f"{pad + i * x_scale:.1f},{yp(nav[i]):.1f}"
            for i in range(0, len(nav), step)
        )

        buys = sells = ""
        for _, t in trades.iterrows():
            idx = daily[daily["date"] == t["date"]].index
            if len(idx) > 0:
                x = pad + idx[0] * x_scale
                c = "red" if t["action"] == "BUY" else "green"
                s = (f'<circle cx="{x:.1f}" cy="{yp(nav[idx[0]]):.1f}" '
                     f'r="4" fill="{c}"/>\n            ')
                if t["action"] == "BUY":
                    buys += s
                else:
                    sells += s

        # --- SVG 回撤 ---
        dd_bars = ""
        for i in range(0, len(nav), max(1, len(nav) // 300)):
            if dd[i] < 0:
                x = pad + i * x_scale
                bh = abs(dd[i]) / abs(max_dd) * (h - 2 * pad) * 0.8 if max_dd != 0 else 0
                dd_bars += (f'<rect x="{x - 1:.1f}" y="{h - pad - bh:.1f}" '
                            f'width="2" height="{bh:.1f}" fill="#e74c3c" opacity="0.3"/>')

        # --- 交易明细 ---
        trows = ""
        for _, t in trades.iterrows():
            c = "#e74c3c" if t["action"] == "BUY" else "#27ae60"
            trows += (f"<tr><td>{t['date'].strftime('%Y-%m-%d')}</td>"
                      f"<td style='color:{c};font-weight:600'>{t['action']}</td>"
                      f"<td>{t['price']:.2f}</td><td>{t['shares']:,.0f}</td></tr>")

        pos_cls = "positive" if total_return > 0 else "negative"
        sym_str = f"&nbsp;|&nbsp; {symbol}" if symbol else ""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{strategy_name} — {symbol or '回测报告'}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; background: #f5f6fa; color: #2d3436; line-height: 1.6; }}
.container {{ max-width: 960px; margin: 0 auto; padding: 24px; }}
.header {{ background: linear-gradient(135deg, #2d3436, #636e72); color: white; padding: 40px 32px; border-radius: 12px; margin-bottom: 24px; }}
.header h1 {{ font-size: 24px; margin-bottom: 8px; }}
.header .sub {{ opacity: 0.8; font-size: 14px; }}
.card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
.card h2 {{ font-size: 16px; color: #636e72; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #dfe6e9; }}
.metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }}
.metric {{ text-align: center; padding: 16px; background: #f8f9fa; border-radius: 8px; }}
.metric .label {{ font-size: 12px; color: #636e72; margin-bottom: 4px; }}
.metric .value {{ font-size: 22px; font-weight: 700; color: #2d3436; }}
.metric .value.positive {{ color: #27ae60; }}
.metric .value.negative {{ color: #e74c3c; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; padding: 10px 12px; background: #f8f9fa; border-bottom: 2px solid #dfe6e9; color: #636e72; font-weight: 600; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #f1f2f6; }}
tr:hover td {{ background: #f8f9fa; }}
.legend {{ display: flex; gap: 20px; font-size: 12px; color: #636e72; margin-bottom: 8px; }}
.legend span {{ display: flex; align-items: center; gap: 4px; }}
.dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
.footer {{ text-align: center; color: #b2bec3; font-size: 12px; padding: 20px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>{strategy_name}</h1>
    <div class="sub">{symbol}{sym_str if not sym_str else ''} &nbsp;|&nbsp; {date_range} &nbsp;|&nbsp; 初始资金 ¥{initial_cash:,.0f}</div>
  </div>
  <div class="card">
    <h2>绩效指标</h2>
    <div class="metrics">
      <div class="metric"><div class="label">总收益率</div><div class="value {pos_cls}">{total_return:+.2%}</div></div>
      <div class="metric"><div class="label">年化收益</div><div class="value {pos_cls}">{ar:+.2%}</div></div>
      <div class="metric"><div class="label">最终资金</div><div class="value positive">¥{final_value:,.0f}</div></div>
      <div class="metric"><div class="label">最大回撤</div><div class="value negative">{max_dd:.2%}</div></div>
      <div class="metric"><div class="label">夏普比率</div><div class="value">{sharpe:.2f}</div></div>
      <div class="metric"><div class="label">卡玛比率</div><div class="value">{calmar:.2f}</div></div>
      <div class="metric"><div class="label">年化波动</div><div class="value">{annual_vol:.2%}</div></div>
      <div class="metric"><div class="label">交易天数</div><div class="value">{len(daily)}</div></div>
      <div class="metric"><div class="label">买/卖次数</div><div class="value">{buy_count} / {sell_count}</div></div>
    </div>
  </div>
  <div class="card">
    <h2>净值曲线</h2>
    <div class="legend"><span><span class="dot" style="background:#3498db"></span>策略净值</span><span><span class="dot" style="background:red"></span>买入</span><span><span class="dot" style="background:green"></span>卖出</span></div>
    <svg viewBox="0 0 {w} {h}" width="100%" height="350">
      <line x1="{pad}" y1="{yp(1):.1f}" x2="{w-pad}" y2="{yp(1):.1f}" stroke="#b2bec3" stroke-width="1" stroke-dasharray="4,4"/>
      <polyline points="{nav_pts}" fill="none" stroke="#3498db" stroke-width="2"/>
      {buys}{sells}
      <text x="{pad}" y="20" font-size="11" fill="#636e72">起始净值: 1.00</text>
      <text x="{w-pad}" y="20" font-size="11" fill="#636e72" text-anchor="end">终值: {nav[-1]:.2f}</text>
    </svg>
  </div>
  <div class="card">
    <h2>回撤曲线</h2>
    <svg viewBox="0 0 {w} 160" width="100%" height="160">
      <line x1="{pad}" y1="130" x2="{w-pad}" y2="130" stroke="#dfe6e9" stroke-width="1"/>
      {dd_bars}
      <text x="{pad}" y="14" font-size="11" fill="#636e72">最大回撤: {max_dd:.2%}</text>
    </svg>
  </div>
  <div class="card">
    <h2>交易明细</h2>
    <table><thead><tr><th>日期</th><th>方向</th><th>价格</th><th>股数</th></tr></thead><tbody>{trows}</tbody></table>
  </div>
  <div class="footer">EasyXT {strategy_name} · 生成于 {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
</body>
</html>"""

        # --- 保存 ---
        if not output_path:
            import os as _os
            out_dir = _Path(__file__).parent / "output"
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_name = strategy_name.replace(" ", "_").replace("/", "_")
            output_path = str(out_dir / f"{safe_name}_report.html")
        else:
            _Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path
