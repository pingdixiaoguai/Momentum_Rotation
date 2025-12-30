import pandas as pd
import quantstats as qs
from core import BacktestResult, Strategy


class BacktestEngine:
    """回测执行引擎"""

    def __init__(self, start_date: str, end_date: str, cost: float = 0.0005, benchmark: str = '510300'):
        self.start_date = start_date
        self.end_date = end_date
        self.cost = cost
        self.benchmark = benchmark

    def run(self, strategy: Strategy, closes: pd.DataFrame, opens: pd.DataFrame) -> BacktestResult:
        print(f"--- Running Backtest: {strategy.name} ---")

        # 截取时间段
        data_closes = closes.loc[self.start_date:self.end_date]
        data_opens = opens.loc[self.start_date:self.end_date]

        # 生成信号 (信号是“收盘后”生成的，实际上影响“次日”的持仓)
        raw_signals = strategy.generate_signals(data_closes)

        # Shift 1: 今天的信号决定明天的持仓
        # 填充NaN为 'cash'
        holdings = raw_signals.shift(1).fillna('cash')
        # 对齐索引
        holdings = holdings.reindex(data_closes.index, fill_value='cash')

        # 向量化计算净值 (简化版，比逐日循环快且易读)
        # 1. 计算所有资产的日收益率
        asset_rets = data_opens.pct_change().fillna(0)  # 这里用Open-to-Open收益率近似，或者根据实际逻辑调整
        # *注: 原代码用的是 Open[t]/Open[t-1]，这里保持一致逻辑

        # 2. 构建组合收益序列
        portfolio_rets = pd.Series(0.0, index=holdings.index)

        # 记录交易明细
        transactions = []
        last_h = 'cash'

        current_equity = 1.0
        equity_curve = [1.0]

        # 还是需要一次遍历来准确处理 交易成本 和 动态持有
        # 向量化处理换仓成本比较麻烦，混合方法最稳妥
        dates = holdings.index
        for i in range(1, len(dates)):
            date = dates[i]
            prev_date = dates[i - 1]

            current_h = holdings.loc[date]  # 今天应该持有的

            # 计算当日涨跌幅 (基于Open)
            # 假设我们是在 Open 时刻根据昨晚信号调仓
            day_ret = 0.0
            if last_h != 'cash' and last_h in data_opens.columns:
                # 昨天的持有在今天的收益
                # 严谨逻辑：(Open_t - Open_t-1) / Open_t-1
                p_open = data_opens.at[prev_date, last_h]
                c_open = data_opens.at[date, last_h]
                if p_open > 0:
                    day_ret = (c_open / p_open) - 1

            # 计算成本
            cost_deduction = 0.0
            if current_h != last_h:
                # 发生调仓
                cost_deduction += self.cost  # 卖出旧的 (if not cash)
                cost_deduction += self.cost  # 买入新的 (if not cash)
                # 简化：只要变动就扣双倍，或者根据 cash 细分

                transactions.append({
                    'date': date,
                    'action': 'rebalance',
                    'from': last_h,
                    'to': current_h
                })

            # 更新净值: 先算涨跌，再扣成本
            current_equity *= (1 + day_ret)
            current_equity *= (1 - cost_deduction)
            equity_curve.append(current_equity)

            last_h = current_h

        equity_series = pd.Series(equity_curve, index=dates)
        returns_series = equity_series.pct_change().fillna(0)
        returns_series.name = strategy.name

        # 基准收益
        bench_ret = data_closes[self.benchmark].pct_change().loc[returns_series.index].fillna(0)

        return BacktestResult(
            strategy_name=strategy.name,
            returns=returns_series,
            benchmark_returns=bench_ret,
            transactions=pd.DataFrame(transactions)
        )


class ReportGenerator:
    """报告生成器"""

    @staticmethod
    def show_html(result: BacktestResult, filename: str = None):
        if not filename:
            filename = f"report_{result.strategy_name}.html"

        print(f"Generating report: {filename}")
        qs.reports.html(
            result.returns,
            benchmark=result.benchmark_returns,
            output=filename,
            title=f"Backtest: {result.strategy_name}"
        )