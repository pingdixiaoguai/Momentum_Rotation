import pandas as pd
import numpy as np
from core.base import Factor

class Peak(Factor):
    def __init__(self, window: int = 20):
        # 这里的 name 会在回测报告中显示
        super().__init__(f"Peak_{window}d")
        self.window = window

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        print("close:", "\n", close['2024-09-20':'2024-10-15'])
        res = close.rolling(window=20,min_periods=2).apply(self.calculate_k, raw=False).fillna(0.0)

        # print(res.head(50))
        print(res.describe())
        return res
    
    def calculate_k(self, series):
        """计算滚动窗口内最大值与第一个值的斜率"""
        # if len(series) < 20:  # 不足20个数据返回NaN
        #     return np.nan
        
        max_value = series.max()
        max_pos = series.argmax()

        if max_pos == 0:
            return 0.0
        elif max_pos == len(series) - 1:
            return 0.0
        
        min_value = series.iloc[:max_pos].min()
        min_pos = series.iloc[:max_pos].argmin()

        # first_value = series.iloc[0]
        last_value = series.iloc[-1]
        
        # k1 = (max_value - first_value) / max_pos
        # k2 = (last_value - max_value) / (len(series) - 1 - max_pos)
        k1 = (max_value - min_value) / (max_pos - min_pos)
        k2 = (last_value - min_value) / (len(series) - 1 - min_pos)

        return (k2 - k1) * k1 * 500

import config
from core.data import DataLoader
if __name__ == "__main__":
    loader = DataLoader("2013-08-01", "2025-12-31", auto_sync=False)
    data_dict = loader.load(config.ETF_SYMBOLS)
    closes = data_dict['close']
    Peak(20).calculate(closes)