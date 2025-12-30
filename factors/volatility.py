import pandas as pd
import numpy as np
from core.base import Factor


class Volatility(Factor):
    """
    历史波动率因子 (Volatility)
    计算公式: Log收益率的N日标准差
    """

    def __init__(self, window: int = 20):
        super().__init__(f"Vol_{window}d")
        self.window = window

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        # 1. 计算对数收益率
        log_ret = np.log(close / close.shift(1))
        # 2. 计算滚动标准差
        return log_ret.rolling(self.window).std()


class IntradayVolatility(Factor):
    """
    日内波动率因子 (Intraday Volatility)
    计算公式: (High - Low) / Low 的 N 日均值
    """

    def __init__(self, window: int = 14):
        super().__init__(f"IntradayVol_{window}d")
        self.window = window

    def calculate(self, high: pd.DataFrame, low: pd.DataFrame, **kwargs) -> pd.DataFrame:
        # 利用 kwargs 自动接收 high 和 low 数据
        daily_range = (high - low) / low
        return daily_range.rolling(self.window).mean()