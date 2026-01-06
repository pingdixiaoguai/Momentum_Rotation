import pandas as pd
import numpy as np
from core.base import Factor

class Momentum(Factor):
    """
    经典动量因子 (Momentum)
    计算公式: (Close_t / Close_{t-N}) - 1
    """
    def __init__(self, window: int = 20):
        # 这里的 name 会在回测报告中显示
        super().__init__(f"Mom_{window}d")
        self.window = window

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        :param close: 收盘价宽表 (Index=Date, Columns=Assets)
        """
        print(close.head(50))
        # res = close.pct_change(self.window)

        # print("close:", "\n", close['2024-09-20':'2024-10-15'])
        res = close.rolling(window=24).apply(self.calculate_k, raw=False) #.fillna(0.0),min_periods=20

        print(res.head(50))
        print(res.describe())
        return res


    def calculate_k(self, series):
        """计算滚动窗口内最大值与第一个值的斜率"""
        if len(series) < 20:  # 不足20个数据返回NaN
            return np.nan

        min_value = series.iloc[:3].min()
        last_value = series.iloc[-1]

        return (last_value/min_value if min_value != 0 else 0.0) - 1



import config
from core.data import DataLoader
if __name__ == "__main__":
    loader = DataLoader("2013-08-01", "2025-12-31", auto_sync=False)
    data_dict = loader.load(config.ETF_SYMBOLS)
    closes = data_dict['close']
    Momentum(20).calculate(closes)