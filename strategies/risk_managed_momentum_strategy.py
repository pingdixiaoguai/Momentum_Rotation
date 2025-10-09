import pandas as pd
from config import MOMENTUM_WINDOW  # 从配置文件导入参数


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

    holdings = pd.Series(index=momentum.index, dtype=str)
    for date in momentum.index:
        best_etf = momentum.loc[date].idxmax()
        if momentum.at[date, best_etf] > 0:
            holdings.loc[date] = best_etf
        else:
            holdings.loc[date] = 'cash'

    return holdings