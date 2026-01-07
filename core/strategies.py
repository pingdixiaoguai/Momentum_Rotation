import pandas as pd
from .base import Strategy, Factor
from typing import Dict, Callable, Any


class CustomStrategy(Strategy):
    """
    [增强版] 通用自定义逻辑策略 (CustomStrategy)

    1. 传入任意数量的因子 (通过字典命名)。
    2. 传入一个 python 函数 (logic_func) 来编写你的选股/择时逻辑。
    3. 支持 holding_period 参数，实现定期调仓。
    4. [New] 支持 **logic_kwargs，可以将策略参数（如 top_k, weights 等）透传给 logic_func。
    """

    def __init__(self,
                 factors: Dict[str, Factor],
                 logic_func: Callable[..., pd.DataFrame],
                 name: str = "Custom",
                 holding_period: int = 1,
                 **logic_kwargs):
        """
        :param factors: 因子字典, e.g. {'mom': Momentum(20), 'bias': Bias(20)}
        :param logic_func: 自定义逻辑函数。
                           签名建议: def my_logic(factor_values, closes, **kwargs) -> weights
        :param name: 策略名称
        :param holding_period: 调仓周期 (天)。默认为 1 (每日调仓)。
        :param logic_kwargs: 额外的参数，会直接传递给 logic_func。
                             例如: top_k=2, weights={'mom': 1.0, 'bias': 0.5}
        """
        super().__init__(name)
        self.factors = factors
        self.logic_func = logic_func
        self.holding_period = holding_period
        self.logic_kwargs = logic_kwargs  # 存储额外的策略参数

    def generate_target_weights(self, **kwargs) -> pd.DataFrame:
        if 'close' not in kwargs:
            raise ValueError("Strategy requires 'close' price data.")
        closes = kwargs['close']

        # 1. 计算所有因子值
        factor_values = {}
        for name, factor in self.factors.items():
            # calculate 可能会用到 open, high, low 等，直接传 kwargs
            factor_values[name] = factor.calculate(**kwargs)

        # 2. 调用用户传入的逻辑函数
        # 将 factor_values, closes 以及初始化时传入的 logic_kwargs 一并传给逻辑函数
        raw_weights = self.logic_func(factor_values, closes, **self.logic_kwargs)

        # 3. 处理调仓周期 (Holding Period)
        if self.holding_period > 1:
            sampled_weights = raw_weights.iloc[::self.holding_period]
            target_weights = sampled_weights.reindex(raw_weights.index).ffill()
            return target_weights
        else:
            return raw_weights