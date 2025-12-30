from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Tuple


class Factor(ABC):
    """
    因子基类：用户专注于实现 calculate
    """

    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__

    @abstractmethod
    def calculate(self, **kwargs) -> pd.DataFrame:
        """
        计算因子值。

        设计模式：使用 **kwargs 接收任意数据。
        在子类实现时，推荐直接在参数列表中列出你需要的数据字段，并加上 **kwargs 忽略其他字段。

        示例子类实现:
            def calculate(self, closes, volumes, **kwargs):
                # 自动获取了 closes 和 volumes，忽略了其他可能传入的 opens, highs 等
                return closes / volumes

        :param kwargs: 包含数据的字典 (e.g., closes=df, volumes=df, opens=df)
        :return: 因子值宽表 (Index=Date, Columns=Assets)
        """
        pass


class Strategy(ABC):
    """策略基类：负责将因子值转化为持仓信号"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_target_weights(self, **kwargs) -> pd.DataFrame:
        """
        生成目标持仓权重。
        同样使用 **kwargs 接收任意数据 (closes, volumes, factors_data 等)。

        :return: 目标持仓权重宽表 (Sum of row <= 1.0)
        """
        pass