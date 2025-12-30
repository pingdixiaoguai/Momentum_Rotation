import pandas as pd
import numpy as np
from core.base import Factor


class Momentum(Factor):
    def __init__(self, window: int = 20):
        super().__init__(f"Mom_{window}")
        self.window = window

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        # 只取 close，忽略其他
        return close.pct_change(self.window)


class Volatility(Factor):
    def __init__(self, window: int = 20):
        super().__init__(f"Vol_{window}")
        self.window = window

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        log_ret = np.log(close / close.shift(1))
        return log_ret.rolling(self.window).std()


class MeanReversion(Factor):
    def __init__(self, window: int = 5):
        super().__init__(f"Rev_{window}")
        self.window = window

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        ma = close.rolling(self.window).mean()
        return (close - ma) / ma


class IntradayVolatility(Factor):
    """
    示例：这是一个需要 High 和 Low 数据的因子
    """

    def __init__(self, window: int = 14):
        super().__init__(f"IntradayVol_{window}")
        self.window = window

    def calculate(self, high: pd.DataFrame, low: pd.DataFrame, **kwargs) -> pd.DataFrame:
        # 如果数据里没有 high/low，这里会报错，或者可以在这里处理 fallback
        range_pct = (high - low) / low
        return range_pct.rolling(self.window).mean()