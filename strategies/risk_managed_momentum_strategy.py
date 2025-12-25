import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MOMENTUM_WINDOW  # 从配置文件导入参数

# def calculate_reversal_factor(opens: pd.DataFrame) -> pd.Series:
#     return -opens.pct_change(periods=MOMENTUM_WINDOW).dropna()

def risk_managed_momentum_strategy(closes: pd.DataFrame) -> pd.Series:
    """
    策略一：带现金过滤器的动量轮动策略。

    规则：
    1. 计算20日动量。
    2. 选出动量冠军。
    3. 如果冠军动量为正，则持有；否则持有现金。

    :param closes: 包含收盘价的DataFrame
    :return: 包含每日持仓信号的Series (ETF代码或'cash')
    """
    print("应用策略: 带现金过滤器的动量轮动")
    momentum = closes.pct_change(periods=MOMENTUM_WINDOW).dropna()
    row_num = len(momentum) 
    for col in momentum.columns:
        momentum_sort = momentum.sort_values(by=col, ascending=False)
        # print("[strategy] " + col + " momentum(head):", momentum_sort.head(150))
        momentum_threshold = momentum_sort.iloc[int(0.05*row_num),momentum.columns.get_loc(col)]
        momentum.loc[momentum[col] > momentum_threshold, col] = 0
        print(row_num, col, momentum_threshold)

    print("[strategy] momentum:", momentum) #.head(30)

    def calculate_reversal_factor(closes_df: pd.DataFrame) -> pd.Series:
        returns_log = np.log(closes_df / closes_df.shift(1))
        # print("returns_log:", returns_log.head(30))
        reversal = returns_log.copy()
        reversal_factors = reversal.rolling(window=MOMENTUM_WINDOW).mean().shift(1).fillna(0)
        # reversal_factors.columns = [f"{col}_rev_factor_{window}d" for col in reversal_factors.columns]
        return reversal_factors
    reversal = calculate_reversal_factor(closes)
    # print("reversal:", reversal.head(30))

    momentum_aligned, reversal_aligned = momentum.align(reversal, join='inner')
    # for col in momentum.columns:
    #     momentum_sort = momentum.sort_values(by=col, ascending=False)
    #     # print("[strategy] " + col + " momentum(head):", momentum_sort.head(150))
    #     momentum_threshold = momentum_sort.iloc[int(0.05*row_num),momentum.columns.get_loc(col)]
    #     momentum.loc[momentum[col] > momentum_threshold, col] = 0
    #     print(row_num, col, momentum_threshold)
    # reversal_aligned[abs(reversal_aligned) <= 0.002] = 0
    # reversal_aligned[reversal_aligned >= -0.0008] = 0
    # momentum_aligned[momentum_aligned >= 0.01] = 0
    
    # 计算0的数量和占比
    zero_count = (reversal_aligned == 0).sum()  # 转换为整数
    total_count = len(reversal_aligned)
    print("zero_count:", zero_count, total_count)

    print("[strategy] momentum_aligned, :", type(momentum_aligned), momentum_aligned)
    print("[strategy] reversal_aligned:", reversal_aligned)
    # 市场波动率越高，动量权重应该越小
    # 在价格低位时反转因子更加有效
    # market_vol = self._get_market_volatility()
    # w_momentum = 0.7 if market_vol < 0.15 else 0.3
    # w_reversal = 1 - w_momentum

    w_momentum, w_reversal = 1.0, 0.0
    momentum = w_momentum * momentum_aligned - w_reversal * reversal_aligned

    print("[strategy] momentum:", momentum)

    holdings = pd.Series(index=momentum.index, dtype=str)
    # print(holdings)
    for date in momentum.index:
        best_etf = momentum.loc[date].idxmax()
        # print(momentum.loc[date])
        # print(date, best_etf)
        if momentum.at[date, best_etf] > 0:
            holdings.loc[date] = best_etf
        else:
            holdings.loc[date] = 'cash'

    return holdings

# import config
# from data_loader import get_etf_data
# closes, opens = get_etf_data(config.ETF_SYMBOLS, config.CACHE_FILE, force_refresh=False)
# # reversal = calculate_reversal_factor(opens)
# # print("reversal:",reversal)
# holdings = risk_managed_momentum_strategy(closes)
# print(holdings)
# print(holdings[holdings == 'cash'].index)