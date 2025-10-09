import pandas as pd
from config import MOMENTUM_WINDOW

def pure_momentum_strategy(closes: pd.DataFrame) -> pd.Series:
    """
    策略二：纯粹动量轮动策略 (我们最开始复现的版本)。

    规则：
    1. 计算20日动量。
    2. 永远满仓持有动量冠军。

    :param closes: 包含收盘价的DataFrame
    :return: 包含每日持仓信号的Series
    """
    print("应用策略: 纯粹动量轮动")
    momentum = closes.pct_change(periods=MOMENTUM_WINDOW).dropna()
    holdings = momentum.idxmax(axis=1)
    return holdings