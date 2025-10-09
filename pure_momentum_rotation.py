import warnings
import pandas as pd
import quantstats as qs
from data_loader import get_etf_data

warnings.filterwarnings('ignore')

# --- 1. 参数配置 ---
# ======================================================================
ETF_SYMBOLS = ["510300", "518880", "513100", "159915"]
MOMENTUM_WINDOW = 20  # 动量计算窗口
TRANSACTION_COST = 1 / 1000  # 单边交易成本万分之零点五
CACHE_FILE = "etf_data_cache_expanded.csv"
OUTPUT_HTML_FILE = "pure_momentum_report.html"


def run_risk_managed_momentum_backtest(force_refresh=False):
    """执行带现金过滤器的动量轮动回测"""

    closes, opens = get_etf_data(ETF_SYMBOLS, CACHE_FILE, force_refresh)
    if closes is None: return


    # --- 信号计算 ---
    # FIX: Add .dropna() to remove initial rows where momentum can't be calculated
    momentum = closes.pct_change(periods=MOMENTUM_WINDOW).dropna()

    # 每日决策
    holdings = pd.Series(index=momentum.index, dtype=str)
    for date in momentum.index:
        best_etf = momentum.loc[date].idxmax()
        # **风控逻辑核心**：检查冠军的动量是否为正
        if momentum.at[date, best_etf] > 0:
            holdings.loc[date] = best_etf
        else:
            holdings.loc[date] = 'cash'  # 如果为负，则空仓

    # T-1日的信号决定T日的持仓
    signals = holdings.shift(1).dropna()

    # --- 交易和收益计算 ---
    portfolio_value = pd.Series(index=signals.index, dtype=float)
    last_holding = 'cash'
    current_value = 1.0

    for date in signals.index:
        # Find the previous valid trading day in the 'opens' index
        try:
            prev_date_loc = opens.index.get_loc(date) - 1
            if prev_date_loc < 0: continue
            prev_date = opens.index[prev_date_loc]
        except KeyError:
            continue  # Skip if the current date isn't in the opens index

        # 收益计算
        if last_holding != 'cash':
            open_return = opens.at[date, last_holding] / opens.at[prev_date, last_holding] - 1
            current_value *= (1 + open_return)

        current_signal = signals.loc[date]

        # 换仓时才计算交易成本
        if current_signal != last_holding:
            costs = 0
            if last_holding != 'cash': costs += TRANSACTION_COST
            if current_signal != 'cash': costs += TRANSACTION_COST
            current_value *= (1 - costs)

        portfolio_value.loc[date] = current_value
        last_holding = current_signal

    strategy_returns = portfolio_value.pct_change().fillna(0)
    strategy_returns.name = "Strategy"

    # --- 生成报告 ---
    print("\n--- 风险管理策略回测结果 ---")
    qs.reports.html(
        returns=strategy_returns,
        benchmark=closes[ETF_SYMBOLS[0]].pct_change().loc[strategy_returns.index],
        output=OUTPUT_HTML_FILE,
        title=f'动量轮动策略 (带现金过滤器)'
    )
    print(f"\n回测报告已生成！请在浏览器中打开文件: {OUTPUT_HTML_FILE}")


# --- 4. 主程序入口 ---
if __name__ == '__main__':
    run_risk_managed_momentum_backtest(force_refresh=False)