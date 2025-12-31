import numpy as np
import pandas as pd
from core.base import Factor


class MainLineBias(Factor):
    """
    广发策略刘晨明-主线乖离率因子

    来源: 广发证券刘晨明《如何区分主线是调整还是终结》
    https://finance.sina.com.cn/stock/stockzmt/2025-10-19/doc-infumfqq4939735.shtml
    计算公式: ln(close) - EMA20(ln(close))

    阈值参考:
    - 0% ~ 15%: 主线行情健康区间
    - > 15%: 过热风险区 (建议规避或减仓)
    - < -5%: 破位风险区

    使用建议:
    在轮动策略中，如果给予该因子"负权重"，可以起到"避免过热"的风控效果；
    如果给予"正权重"，则是追逐强势股（但在>15%时风险极大）。
    """

    def __init__(self, window: int = 20):
        super().__init__(f"LiuBias_{window}d")
        self.window = window

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        # 1. 取对数价格 (Log Price)
        # 使用对数是为了消除高价股和低价股的波动率差异，使指标更具横向可比性
        ln_close = np.log(close)

        # 2. 计算指数移动平均 (EMA)
        # 广发原文使用的是 EMA20 (span=20)
        ema = ln_close.ewm(span=self.window, adjust=False).mean()

        # 3. 计算乖离率
        # ln(A) - ln(B) = ln(A/B) ≈ A/B - 1 (当差异较小时)
        # 这个值直接对应百分比，例如 0.15 代表 15%
        bias = ln_close - ema

        return bias