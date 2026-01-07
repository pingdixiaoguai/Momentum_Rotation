import pandas as pd
import numpy as np
from core.base import Factor

class Momentum(Factor):
    """
    经典动量因子 (Momentum)
    计算公式: (Close_t / Close_{t-N}) - 1
    """
    def __init__(self, window: int = 20, mode: str = "tradition"):
        # 这里的 name 会在回测报告中显示
        super().__init__(f"Mom_{window}d")
        self.window = window
        self.mode = mode

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        :param close: 收盘价宽表 (Index=Date, Columns=Assets)
        """
        # 逻辑：过去 N 天的收益率
        if self.mode == "tradition":
            res = close.pct_change(self.window)
        elif self.mode == "castle":
            res = close.rolling(window=self.window).apply(self.calculate_c1, raw=False) #.fillna(0.0),min_periods=20

        return res
    
    def calculate_c1(self, series):
        """计算滚动窗口内最大值与第一个值的斜率"""
        if len(series) < 20:  # 不足20个数据返回NaN
            return np.nan

        min_value = series.iloc[:3].min()
        last_value = series.iloc[-1]

        return (last_value/min_value if min_value != 0 else 0.0) - 1