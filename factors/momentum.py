import pandas as pd
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
        # 逻辑：过去 N 天的收益率
        return close.pct_change(self.window)