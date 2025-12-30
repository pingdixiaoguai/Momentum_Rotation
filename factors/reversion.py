import pandas as pd
from core.base import Factor

class MeanReversion(Factor):
    """
    均值回归/乖离率因子 (Mean Reversion / Bias)
    计算公式: (Price - MA) / MA
    通常作为负向因子使用（即值越大，越应该卖出）
    """
    def __init__(self, window: int = 5):
        super().__init__(f"Rev_{window}d")
        self.window = window

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        ma = close.rolling(self.window).mean()
        # 计算当前价格偏离均线的幅度
        bias = (close - ma) / ma
        return bias