import pandas as pd
from .base import Strategy, Factor
from typing import Dict, Callable


class CustomStrategy(Strategy):
    """
    [新增] 通用自定义逻辑策略 (CustomStrategy)

    1. 传入任意数量的因子 (通过字典命名)。
    2. 传入一个 python 函数 (logic_func) 来编写你的选股/择时逻辑。

    这样你就不需要每次为了改逻辑而去修改 core/strategies.py 源码了。
    """

    def __init__(self,
                 factors: Dict[str, Factor],
                 logic_func: Callable[[Dict[str, pd.DataFrame], pd.DataFrame], pd.DataFrame],
                 name: str = "Custom"):
        """
        :param factors: 因子字典, e.g. {'mom': Momentum(20), 'bias': Bias(20)}
        :param logic_func: 自定义逻辑函数。
                           签名必须是: def my_logic(factor_values, closes) -> weights
        """
        super().__init__(name)
        self.factors = factors
        self.logic_func = logic_func

    def generate_target_weights(self, **kwargs) -> pd.DataFrame:
        if 'close' not in kwargs:
            raise ValueError("Strategy requires 'close' price data.")
        closes = kwargs['close']

        # 1. 计算所有因子值
        factor_values = {}
        for name, factor in self.factors.items():
            factor_values[name] = factor.calculate(**kwargs)

        # 2. 调用用户传入的逻辑函数
        # 我们把计算好的因子值字典和收盘价传给它
        target_weights = self.logic_func(factor_values, closes)

        return target_weights