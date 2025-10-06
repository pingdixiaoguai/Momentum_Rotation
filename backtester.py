# backtester.py

import pandas as pd
import quantstats as qs
from config import MOMENTUM_WINDOW_ORIGINAL, OUTPUT_HTML_FILE
from strategy import calculate_scores


def backtest_single_momentum(prices, signals):
    """单动量策略计算函数"""
    daily_returns = prices.pct_change()
    common_index = signals.index.intersection(daily_returns.index)
    aligned_signals = signals.loc[common_index]
    aligned_returns = daily_returns.loc[common_index]
    strategy_returns_list = []
    for date, etf_to_hold in aligned_signals.items():
        if etf_to_hold in aligned_returns.columns:
            daily_return = aligned_returns.at[date, etf_to_hold]
            strategy_returns_list.append(daily_return)
        else:
            strategy_returns_list.append(0)
    return pd.Series(strategy_returns_list, index=aligned_signals.index)


def backtest_dual_momentum_portfolio(prices, combined_scores, reversal_scores):
    """执行加权双动量策略的回测"""
    print("开始计算加权双动量策略每日收益...")
    daily_returns = prices.pct_change()
    portfolio_returns = {}
    for i in range(1, len(combined_scores.index)):
        prev_date = combined_scores.index[i - 1]
        date = combined_scores.index[i]
        if date not in daily_returns.index or prev_date not in reversal_scores.index: continue

        prev_date_scores = combined_scores.loc[prev_date]
        top_2_etfs = prev_date_scores.nlargest(2)
        etf1, etf2 = top_2_etfs.index[0], top_2_etfs.index[1]

        reversal_score1 = reversal_scores.at[prev_date, etf1]
        reversal_score2 = reversal_scores.at[prev_date, etf2]

        strength1, strength2 = max(0, -reversal_score1), max(0, -reversal_score2)
        total_strength = strength1 + strength2

        weight1, weight2 = (strength1 / total_strength, strength2 / total_strength) if total_strength > 0 else (0.5,
                                                                                                                0.5)

        return1, return2 = daily_returns.at[date, etf1], daily_returns.at[date, etf2]
        portfolio_returns[date] = weight1 * return1 + weight2 * return2

    return pd.Series(portfolio_returns)


def run_strategy_comparison(etf_symbols, benchmark_symbol, closes, opens):
    """执行两种策略的回测并生成对比报告。"""
    daily_returns_for_signal = closes.pct_change().dropna()

    print("\n正在计算原始策略 (21日动量)...")
    momentum_original = closes[etf_symbols].pct_change(periods=MOMENTUM_WINDOW_ORIGINAL).dropna()
    signals_original = momentum_original.idxmax(axis=1).shift(1).dropna()
    returns_original = backtest_single_momentum(opens, signals_original)
    returns_original.name = "Original_Single_Momentum"

    print("\n正在计算加权双动量策略...")
    combined_scores, reversal_scores = calculate_scores(daily_returns_for_signal, etf_symbols)
    returns_dual_momentum = backtest_dual_momentum_portfolio(opens, combined_scores, reversal_scores)
    returns_dual_momentum.name = "New_Dual_Momentum_Weighted"

    print("\n所有策略计算完成，正在生成对比报告...")
    benchmark_returns = closes[benchmark_symbol].pct_change().dropna()
    benchmark_returns.name = f"Benchmark_{benchmark_symbol}"

    report_df = pd.concat([returns_dual_momentum, returns_original, benchmark_returns], axis=1, join='inner')

    if report_df.empty or len(report_df) < 20:
        print("有效数据点太少，无法生成报告。")
        return

    qs.reports.html(
        returns=report_df["New_Dual_Momentum_Weighted"],
        benchmark=report_df[["Original_Single_Momentum", f"Benchmark_{benchmark_symbol}"]],
        output=OUTPUT_HTML_FILE,
        title='(次日开盘交易)加权双动量策略 vs 原始策略'
    )
    print(f"\n回测对比报告已生成！请在浏览器中打开文件: {OUTPUT_HTML_FILE}")