import pandas as pd
import quantstats as qs
from config import START_DATE, END_DATE, TRANSACTION_COST, ETF_SYMBOLS, OUTPUT_HTML_FILE


class Backtester:
    def __init__(self, start_date=START_DATE, end_date=END_DATE, cost=TRANSACTION_COST):
        self.start_date = start_date
        self.end_date = end_date
        self.cost = cost
        print(f"回测引擎初始化 (周期: {start_date} to {end_date}, 成本: {cost * 100:.2f}%)")

    def run(self, closes: pd.DataFrame, opens: pd.DataFrame, strategy_func):
        """
        运行回测。
        :param closes: 收盘价数据
        :param opens: 开盘价数据
        :param strategy_func: 一个接收closes并返回信号的策略函数
        """
        # 数据预处理
        closes = closes.loc[self.start_date:self.end_date]
        opens = opens.loc[self.start_date:self.end_date]

        # 1. 调用策略函数生成信号
        holdings = strategy_func(closes)
        signals = holdings.shift(1).dropna()

        # 2. 计算投资组合价值
        portfolio_value = pd.Series(index=signals.index, dtype=float)
        last_holding = 'cash'
        current_value = 1.0

        for date in signals.index:
            try:
                prev_date_loc = opens.index.get_loc(date) - 1
                if prev_date_loc < 0: continue
                prev_date = opens.index[prev_date_loc]
            except KeyError:
                continue

            if last_holding != 'cash':
                open_return = opens.at[date, last_holding] / opens.at[prev_date, last_holding] - 1
                current_value *= (1 + open_return)

            current_signal = signals.loc[date]

            if current_signal != last_holding:
                costs = 0
                if last_holding != 'cash': costs += self.cost
                if current_signal != 'cash': costs += self.cost
                current_value *= (1 - costs)

            portfolio_value.loc[date] = current_value
            last_holding = current_signal

        strategy_returns = portfolio_value.pct_change().fillna(0)
        strategy_returns.name = "Strategy"

        # 3. 生成报告
        print("\n回测完成，正在生成报告...")
        benchmark_returns = closes[ETF_SYMBOLS[0]].pct_change().loc[strategy_returns.index]

        qs.reports.html(
            returns=strategy_returns,
            benchmark=benchmark_returns,
            output=strategy_func.__name__ + OUTPUT_HTML_FILE,
            title=f'策略回测报告 ({strategy_func.__name__})'
        )
        print(f"报告已生成: {OUTPUT_HTML_FILE}")