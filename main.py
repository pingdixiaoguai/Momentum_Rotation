import warnings

warnings.filterwarnings('ignore')
import akshare as ak
import pandas as pd
import quantstats as qs
import os
import time  # 引入 time 库
import random  # 引入 random 库

# --- 1. 参数配置 ---
# ======================================================================
ETF_SYMBOLS = ["518880", "513100", "159915", "510300"]
BENCHMARK_SYMBOL = "510300"
MOMENTUM_WINDOW = 21
OUTPUT_HTML_FILE = "momentum_strategy_report.html"
CACHE_FILE = "etf_data_cache.csv"


# ======================================================================

def get_etf_data(symbols, cache_file, force_refresh=False):
    """
    获取ETF数据，并实现本地缓存与健壮的下载逻辑（重试与随机延迟）。
    """
    if os.path.exists(cache_file) and not force_refresh:
        print(f"从缓存文件 {cache_file} 中加载数据...")
        prices = pd.read_csv(cache_file, parse_dates=['date'], index_col='date')
        return prices

    print("开始从网络下载ETF历史数据...")
    etf_data_list = []

    # 新增：健壮的下载逻辑
    max_retries = 3  # 每个symbol最多重试3次

    for symbol in symbols:
        for attempt in range(max_retries):
            try:
                # 随机延迟1到3秒，模拟人类行为
                delay = random.uniform(1, 3)
                print(f"正在获取 {symbol}... (等待 {delay:.2f} 秒)")
                time.sleep(delay)

                etf_df = ak.fund_etf_hist_em(symbol=symbol, period="daily", adjust="hfq")[["日期", "收盘"]]
                etf_df.rename(columns={"日期": "date", "收盘": symbol}, inplace=True)
                etf_df.set_index("date", inplace=True)
                etf_data_list.append(etf_df)

                print(f"成功获取 {symbol} 的数据。")
                # 成功后就跳出重试循环
                break

            except Exception as e:
                print(f"获取 {symbol} 数据失败 (第 {attempt + 1}/{max_retries} 次尝试): {e}")
                if attempt + 1 == max_retries:
                    print(f"已达到最大重试次数，放弃获取 {symbol}。")
                else:
                    # 等待更长的时间再重试
                    time.sleep(5)

    if len(etf_data_list) < len(symbols):
        print("\n警告：未能获取所有ETF的数据，回测结果可能不完整或失败。")
        if not etf_data_list:
            return None

    prices = pd.concat(etf_data_list, axis=1)
    # 合并后，某些ETF的数据可能缺失，需要处理
    prices.index = pd.to_datetime(prices.index)
    prices.sort_index(inplace=True)  # 确保索引是排序的
    prices.fillna(method='ffill', inplace=True)
    prices.dropna(inplace=True)

    print(f"\n数据下载完成，保存到缓存文件 {cache_file} 中...")
    prices.to_csv(cache_file)

    return prices


def run_momentum_backtest(etf_symbols, benchmark_symbol, window, output_file, force_refresh=False):
    """
    执行ETF动量轮动策略回测，并生成专业的HTML报告。
    """
    all_symbols_to_fetch = list(set(etf_symbols + [benchmark_symbol]))
    prices = get_etf_data(all_symbols_to_fetch, CACHE_FILE, force_refresh)

    if prices is None or prices.empty:
        print("未能获取任何数据，程序终止。")
        return

    # 检查是否所有需要的ETF都已下载
    missing_symbols = [s for s in etf_symbols if s not in prices.columns]
    if missing_symbols:
        print(f"错误：数据中缺少以下ETF，无法继续回测: {missing_symbols}")
        return

    print("\n数据准备完成，开始计算指标和信号...")

    daily_returns = prices.pct_change().dropna()
    momentum_scores = prices[etf_symbols].pct_change(periods=window).dropna()
    aligned_returns = daily_returns.loc[momentum_scores.index]
    signals = momentum_scores.idxmax(axis=1).shift(1).dropna()
    aligned_returns = aligned_returns.loc[signals.index]

    print("根据信号计算策略每日收益率...")
    strategy_daily_returns_list = []
    for date, etf_to_hold in signals.items():
        daily_return = aligned_returns.at[date, etf_to_hold]
        strategy_daily_returns_list.append(daily_return)

    strategy_daily_returns = pd.Series(strategy_daily_returns_list, index=signals.index, name="Strategy")

    if strategy_daily_returns.empty:
        print("策略未能产生任何交易信号，无法生成报告。")
        return

    print("\n回测计算完成，正在生成报告...")

    benchmark_returns = daily_returns[benchmark_symbol].loc[strategy_daily_returns.index]
    benchmark_returns.name = f"Benchmark ({benchmark_symbol})"

    qs.reports.html(
        returns=strategy_daily_returns,
        benchmark=benchmark_returns,
        output=output_file,
        title=f'ETF动量轮动策略 (窗口期: {window}天)'
    )

    print(f"\n回测报告已生成！请在浏览器中打开文件: {output_file}")


# --- 主程序入口 ---
if __name__ == '__main__':
    # 重要：在运行前，请先手动删除旧的、可能不完整的 etf_data_cache.csv 文件
    run_momentum_backtest(
        etf_symbols=ETF_SYMBOLS,
        benchmark_symbol=BENCHMARK_SYMBOL,
        window=MOMENTUM_WINDOW,
        output_file=OUTPUT_HTML_FILE,
        force_refresh=True  # 建议设为True来强制执行一次新的、健壮的下载
    )