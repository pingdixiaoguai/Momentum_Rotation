import pandas as pd
import numpy as np
from core.base import Factor


class Peak(Factor):
    def __init__(self, window: int = 20):
        # 这里的 name 会在回测报告中显示
        super().__init__(f"Peak_{window}d")
        self.window = window

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        res = close.rolling(window=self.window, min_periods=2).apply(self.calculate_k).fillna(0.0)
        return res

    def calculate_k(self, series):
        """计算滚动窗口内最大值与第一个值的斜率"""
        max_value = series.max()
        max_pos = series.argmax()

        if max_pos == 0:
            return 0.0
        elif max_pos == len(series) - 1:
            return 0.0

        min_value = series.iloc[:max_pos].min()
        min_pos = series.iloc[:max_pos].argmin()

        last_value = series.iloc[-1]

        k1 = (max_value - min_value) / (max_pos - min_pos)
        k2 = (last_value - min_value) / (len(series) - 1 - min_pos)

        return (k2 - k1) * k1 * 280

