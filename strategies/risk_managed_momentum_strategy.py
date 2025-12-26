import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MOMENTUM_WINDOW  # 从配置文件导入参数

# def calculate_reversal_factor(opens: pd.DataFrame) -> pd.Series:
#     return -opens.pct_change(periods=MOMENTUM_WINDOW).dropna()

def risk_managed_momentum_strategy(closes: pd.DataFrame, volumes: pd.DataFrame) -> pd.Series:
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
        print("[strategy] " + col + " momentum_threshold:", row_num, momentum_threshold)
    
    print("[strategy] volumes:", volumes)








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
    row_num = len(reversal) 
    for col in reversal.columns:
        reversal_sort = reversal.sort_values(by=col, ascending=True)
        # print("[strategy] " + col + " reversal(head):", reversal_sort.head(150))
        reversal_threshold = reversal_sort.iloc[int(0.05*row_num),reversal.columns.get_loc(col)]
        reversal.loc[reversal[col] > reversal_threshold, col] = 0
        print("[strategy] " + col + " reversal_threshold:", row_num, reversal_threshold)


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

    w_momentum, w_reversal = 1.0, 5.0
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




cache_file = "etf_data.csv"
force_refresh=False
cache_file_volumes = cache_file.replace('.csv', '_volumes.csv')

if os.path.exists(cache_file_volumes) and not force_refresh:
    volumes = pd.read_csv(cache_file_volumes, parse_dates=['date'], index_col='date')
    volumes.columns = volumes.columns.astype(str)
print(cache_file_volumes,'\n',volumes.head())

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

# 定义计算斜率的函数
def cal_volume_momentum(volume_list):
    if len(volume_list) != 20:
        return 0, 0
    
    volumes = np.array(volume_list).reshape(-1, 1)

    X1 = np.arange(1, 19).reshape(-1, 1)  # 1到18
    y1 = volumes[:18].flatten()
    
    X2 = np.arange(18, 21).reshape(-1, 1)  # 18到20
    y2 = volumes[17:20].flatten()  # 注意：这里取第18-20个数据
    # print(y1, y2)
    
    model1 = LinearRegression()
    model1.fit(X1, y1)
    k1 = model1.coef_[0]
    
    model2 = LinearRegression()
    model2.fit(X2, y2)
    k2 = model2.coef_[0]
    
    return k1, k2
# a = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 16, 14] #list(range(20))
# print(a,cal_volume_momentum(a))

def calculate_volume_momentum_efficient(volumes):
    # 确保数据是按日期排序的
    volumes = volumes.sort_index()
    
    # 创建一个空的DataFrame来存储结果
    k1_results = pd.DataFrame(index=volumes.index, columns=volumes.columns)
    k2_results = pd.DataFrame(index=volumes.index, columns=volumes.columns)
    
    # 对每列（每支股票）应用rolling计算
    for stock in volumes.columns:
        for i in range(19, len(volumes)):
            window_data = volumes[stock].iloc[i-19:i+1].values
            
            if len(window_data) == 20:
                k1, k2 = cal_volume_momentum(window_data.tolist())
                k1_results.iloc[i, volumes.columns.get_loc(stock)] = k1
                k2_results.iloc[i, volumes.columns.get_loc(stock)] = k2
    
    k1_results = k1_results.dropna()
    k2_results = k2_results.dropna()
    
    return k1_results, k2_results


if __name__ == "__main__":
    k1_df, k2_df = calculate_volume_momentum_efficient(volumes)
    
    print("k1结果 (前18天斜率):")
    print(k1_df.head())
    
    print("\nk2结果 (最后3天斜率):")
    print(k2_df.head())
    
    # 可以计算k1和k2的差值作为信号
    momentum_signal = k2_df - k1_df
    print("\n动量信号 (k2 - k1):")
    print(momentum_signal.head())

    k1_df_renamed = k1_df.copy()
    # k1_df_renamed.columns = [f"{col}_k1" for col in k1_df.columns]
    
    k2_df_renamed = k2_df.copy()
    # k2_df_renamed.columns = [f"{col}_k2" for col in k2_df.columns]
    
    # 拼接DataFrame
    combined_df = pd.concat([k1_df_renamed, k2_df_renamed], axis=0)
    
    print("拼接后的DataFrame形状:", combined_df.shape)
    print("拼接后的列名:", combined_df.columns.tolist())
    print(combined_df.head())
    
    # 2. 对每列进行归一化
    # 使用StandardScaler进行标准化（均值为0，标准差为1）
    scaler = StandardScaler()
    combined_normalized = scaler.fit_transform(combined_df)
    
    # 转换为DataFrame
    combined_normalized_df = pd.DataFrame(
        combined_normalized,
        index=combined_df.index,
        columns=combined_df.columns
    )
    print(combined_normalized_df)
    print(combined_normalized_df["513100"].mean())
    print(combined_normalized_df["510300"].mean())
    print(combined_normalized_df["518880"].mean())
    print(combined_normalized_df["159915"].mean())
    
    # # 3. 重新拆分为k1和k2的DataFrame
    # # 提取k1列
    # k1_columns = [col for col in combined_normalized_df.columns if col.endswith('_k1')]
    # k1_df_normalized = combined_normalized_df[k1_columns].copy()
    
    # # 提取k2列
    # k2_columns = [col for col in combined_normalized_df.columns if col.endswith('_k2')]
    # k2_df_normalized = combined_normalized_df[k2_columns].copy()
    
    # # 4. 恢复原始列名
    # k1_df_normalized.columns = [col.replace('_k1', '') for col in k1_df_normalized.columns]
    # k2_df_normalized.columns = [col.replace('_k2', '') for col in k2_df_normalized.columns]
    
    # 5. 验证归一化效果
    # print("\n归一化统计信息:")
    # print("K1均值:", k1_df_normalized.mean().mean())
    # print("K1标准差:", k1_df_normalized.std().mean())
    # print("K2均值:", k2_df_normalized.mean().mean())
    # print("K2标准差:", k2_df_normalized.std().mean())