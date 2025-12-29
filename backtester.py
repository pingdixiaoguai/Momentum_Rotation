import pandas as pd
import quantstats as qs
from config import START_DATE, END_DATE, TRANSACTION_COST, ETF_SYMBOLS, OUTPUT_HTML_FILE, BENCHMARK_SYMBOL


class Backtester:
    def __init__(self, start_date=START_DATE, end_date=END_DATE, cost=TRANSACTION_COST):
        self.start_date = start_date
        self.end_date = end_date
        self.cost = cost
        print(f"回测引擎初始化 (周期: {start_date} to {end_date}, 成本: {cost * 100:.2f}%)")

    def run(self, closes: pd.DataFrame, opens: pd.DataFrame, volumes: pd.DataFrame, strategy_func):
        """
        运行回测。
        :param closes: 收盘价数据
        :param opens: 开盘价数据
        :param strategy_func: 一个接收closes并返回信号的策略函数
        """
        # 数据预处理
        closes = closes.loc[self.start_date:self.end_date]
        opens = opens.loc[self.start_date:self.end_date]
        volumes = volumes.loc[self.start_date:self.end_date]

        # 1. 调用策略函数生成信号
        holdings = strategy_func(closes)
        signals = holdings.shift(1).dropna()
        # print("opens:", opens)
        # print("holdings:", holdings)
        # print("signals:",len(set(signals)),"/",len(ETF_SYMBOLS), signals)

        # # 2. 计算投资组合价值
        portfolio_value = pd.Series(index=signals.index, dtype=float)
        # print("portfolio_value:", portfolio_value)

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
        benchmark_returns = closes[BENCHMARK_SYMBOL].pct_change().loc[strategy_returns.index]

        # print("[backtester] portfolio_value:", portfolio_value)
        tmp = portfolio_value / portfolio_value.shift(1)
        tmp = tmp.dropna()
        # print("[backtester] tmp info:",type(tmp),tmp,max(tmp),tmp.idxmax())
        # print("[backtester] portfolio_value find:",portfolio_value.loc['2024-09-20':'2024-10-10'])
        # print("[backtester] holdings find:",holdings.loc['2024-09-20':'2024-10-10'])


        # print("[backtester] strategy_returns:",strategy_returns)
        # print("[backtester] benchmark_returns:",benchmark_returns)

        qs.reports.html(
            returns=strategy_returns,
            benchmark=benchmark_returns,
            output=strategy_func.__name__ + "_" + OUTPUT_HTML_FILE,
            title=f'策略回测报告 ({strategy_func.__name__})'
        )
        # print(f"报告已生成: {strategy_func.__name__ + "_" + OUTPUT_HTML_FILE}")
        print(f'报告已生成: {strategy_func.__name__ + "_" + OUTPUT_HTML_FILE}')


# import config
# from data_loader import get_etf_data
# from strategies.risk_managed_momentum_strategy import risk_managed_momentum_strategy
# from strategies.pure_momentum_strategy import pure_momentum_strategy

# closes, opens = get_etf_data(config.ETF_SYMBOLS, config.CACHE_FILE, force_refresh=False)
# if closes is not None:
#     bt = Backtester()
#     bt.run(closes, opens, strategy_func=risk_managed_momentum_strategy)