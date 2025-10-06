import os
import time
import random
import pandas as pd
import akshare as ak


def get_etf_data(symbols, cache_file, force_refresh=False):
    """
    获取ETF数据，同时包含开盘价和收盘价。
    返回两个DataFrame: closes, opens
    """
    cache_file_closes = cache_file.replace('.csv', '_closes.csv')
    cache_file_opens = cache_file.replace('.csv', '_opens.csv')

    if os.path.exists(cache_file_closes) and not force_refresh:
        print(f"从缓存文件加载数据...")
        closes = pd.read_csv(cache_file_closes, parse_dates=['date'], index_col='date')
        opens = pd.read_csv(cache_file_opens, parse_dates=['date'], index_col='date')
        closes.columns = closes.columns.astype(str)
        opens.columns = opens.columns.astype(str)
        return closes, opens

    print("开始从网络下载ETF历史数据...")
    all_data = {}
    max_retries = 3
    for symbol in symbols:
        for attempt in range(max_retries):
            try:
                delay = random.uniform(1, 3)
                print(f"正在获取 {symbol}... (等待 {delay:.2f} 秒)")
                time.sleep(delay)
                str_symbol = str(symbol)
                etf_df = ak.fund_etf_hist_em(symbol=str_symbol, period="daily", adjust="hfq")[["日期", "开盘", "收盘"]]
                etf_df.rename(columns={"日期": "date", "开盘": "open", "收盘": "close"}, inplace=True)
                etf_df.set_index("date", inplace=True)
                all_data[str_symbol] = etf_df
                print(f"成功获取 {symbol} 的数据。")
                break
            except Exception as e:
                print(f"获取 {symbol} 数据失败 (第 {attempt + 1}/{max_retries} 次尝试): {e}")
                if attempt + 1 == max_retries:
                    print(f"已达到最大重试次数，放弃获取 {symbol}。")
                else:
                    time.sleep(5)

    if not all_data: return None, None

    closes = pd.DataFrame({symbol: df['close'] for symbol, df in all_data.items()})
    opens = pd.DataFrame({symbol: df['open'] for symbol, df in all_data.items()})

    for df in [closes, opens]:
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        df.fillna(method='ffill', inplace=True)
        df.dropna(inplace=True)

    print(f"\n数据下载完成，保存到缓存文件...")
    closes.to_csv(cache_file_closes)
    opens.to_csv(cache_file_opens)
    return closes, opens