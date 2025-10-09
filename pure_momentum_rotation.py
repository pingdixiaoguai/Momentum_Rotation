import warnings
import pandas as pd
import numpy as np
import quantstats as qs
from data_loader import get_etf_data

warnings.filterwarnings('ignore')

# --- 1. 参数配置 ---
# ======================================================================
ETF_SYMBOLS = ["510300", "518880", "513100", "159915"]
MOMENTUM_WINDOW = 20  # 动量计算窗口
TRANSACTION_COST = 0.5 / 10000  # 单边交易成本万分之零点五
CACHE_FILE = "etf_data_cache_expanded.csv"
OUTPUT_HTML_FILE = "pure_momentum_report.html"


def run_pure_momentum_backtest(force_refresh=False):
    """执行纯粹动量轮动回测"""

    # --- 数据准备 ---
    closes, opens = get_etf_data(ETF_SYMBOLS, CACHE_FILE, force_refresh)
    if closes is None:
        print("获取数据失败，回测终止。")
        return


    # --- 信号计算 (基于收盘价) ---
    momentum = closes.pct_change(periods=MOMENTUM_WINDOW)
    # T-1日的信号决定T日的交易
    signals = momentum.idxmax(axis=1).shift(1).dropna()

    # --- 交易和收益计算 (基于开盘价) ---
    portfolio_value = pd.Series(index=signals.index, dtype=float)

    last_holding = None
    current_value = 1.0  # 初始资金为1.0

    # 用于计算平均持仓天数
    trade_dates = []
    holding_days_list = []
    last_trade_date = signals.index[0]

    for date in signals.index:
        # 检查是否有对应的开盘价数据
        prev_date = date - pd.Timedelta(days=1)
        if date not in opens.index or prev_date not in opens.index:
            portfolio_value.loc[date] = current_value
            continue

        current_signal = signals.loc[date]

        # 收益计算: 基于上一个开盘价到今天开盘价的变化
        if last_holding is not None:
            # 找到上一个有效的开盘价日期
            last_open_date = opens.index[opens.index.get_loc(date) - 1]
            open_return = opens.at[date, last_holding] / opens.at[last_open_date, last_holding] - 1
            current_value *= (1 + open_return)

        # 检查是否换仓
        if current_signal != last_holding:
            # 换仓，扣除交易成本 (一卖一买)
            current_value *= (1 - TRANSACTION_COST * 2)

            # 记录交易信息用于计算持仓天数
            if last_holding is not None:
                holding_days = len(pd.bdate_range(start=last_trade_date, end=date)) - 1
                if holding_days > 0:
                    holding_days_list.append(holding_days)

            last_trade_date = date
            trade_dates.append(date)

        portfolio_value.loc[date] = current_value
        last_holding = current_signal

    strategy_returns = portfolio_value.pct_change().fillna(0)
    strategy_returns.name = "Strategy"

    # --- 指标计算与对比 ---
    print("\n--- 回测结果分析 ---")
    avg_holding_days = np.mean(holding_days_list) if holding_days_list else 0
    total_trades = len(trade_dates)

    print(f"回测时间段: {strategy_returns.index[0].date()} to {strategy_returns.index[-1].date()}")
    print(f"平均持有天数: {avg_holding_days:.2f} 天")
    print(f"总交易次数: {total_trades} 次 (换仓次数)")

    # --- 生成报告 ---
    qs.reports.html(
        returns=strategy_returns,
        benchmark=closes[ETF_SYMBOLS[0]].pct_change().loc[strategy_returns.index],  # 用沪深300作基准
        output=OUTPUT_HTML_FILE,
        title=f'纯粹动量轮动策略 (Momentum{MOMENTUM_WINDOW})'
    )
    print(f"\n回测报告已生成！请在浏览器中打开文件: {OUTPUT_HTML_FILE}")


# --- 4. 主程序入口 ---
if __name__ == '__main__':
    run_pure_momentum_backtest(force_refresh=False)