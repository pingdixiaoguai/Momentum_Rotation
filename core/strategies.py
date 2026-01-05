import pandas as pd
from .base import Strategy, Factor
from typing import Dict, Callable


class CustomStrategy(Strategy):
    """
    [新增] 通用自定义逻辑策略 (CustomStrategy)

    1. 传入任意数量的因子 (通过字典命名)。
    2. 传入一个 python 函数 (logic_func) 来编写你的选股/择时逻辑。
    3. [New] 支持 holding_period 参数，实现定期调仓 (如每5天)。

    这样你就不需要每次为了改逻辑而去修改 core/strategies.py 源码了。
    """

    def __init__(self,
                 factors: Dict[str, Factor],
                 logic_func: Callable[[Dict[str, pd.DataFrame], pd.DataFrame], pd.DataFrame],
                 name: str = "Custom",
                 holding_period: int = 1):
        """
        :param factors: 因子字典, e.g. {'mom': Momentum(20), 'bias': Bias(20)}
        :param logic_func: 自定义逻辑函数。
                           签名必须是: def my_logic(factor_values, closes) -> weights
        :param name: 策略名称
        :param holding_period: 调仓周期 (天)。默认为 1 (每日调仓)。
                               设为 5 表示每 5 个交易日才计算一次信号，中间保持持仓。
        """
        super().__init__(name)
        self.factors = factors
        self.logic_func = logic_func
        self.holding_period = holding_period

    def generate_target_weights(self, **kwargs) -> pd.DataFrame:
        if 'close' not in kwargs:
            raise ValueError("Strategy requires 'close' price data.")
        closes = kwargs['close']

        # 1. 计算所有因子值
        factor_values = {}
        for name, factor in self.factors.items():
            factor_values[name] = factor.calculate(**kwargs)

        # 2. 调用用户传入的逻辑函数
        # 计算每一天的理论信号 (Daily Signal)
        raw_weights = self.logic_func(factor_values, closes)

        # 3. 处理调仓周期 (Holding Period)
        if self.holding_period > 1:
            # 逻辑说明：
            # 1. iloc[::N]: 从第0天开始，每隔N天取出一行数据。这代表我们在这些日子做决定。
            # 2. reindex: 将索引恢复为完整的交易日序列，中间缺失的日子会被填为 NaN。
            # 3. ffill: 用上一次的有效持仓填充中间的空缺，代表"锁仓"。

            sampled_weights = raw_weights.iloc[::self.holding_period]
            target_weights = sampled_weights.reindex(raw_weights.index).ffill()

            # 注意：ffill 后，如果最开始几天是 NaN，它们依然会是 NaN，这符合逻辑（还没到第一个调仓日或数据不足）
            return target_weights
        else:
            return raw_weights