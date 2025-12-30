from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any


class DataProvider(ABC):
    """数据提供者抽象基类"""

    @abstractmethod
    def load_data(self, symbols: list) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        返回: (closes, opens, volumes)
        """
        pass


class Strategy(ABC):
    """策略抽象基类"""

    def __init__(self, params: Dict[str, Any] = None):
        self.params = params or {}

    @abstractmethod
    def generate_signals(self, closes: pd.DataFrame, volumes: pd.DataFrame = None) -> pd.Series:
        """
        输入收盘价，返回每日持仓信号序列 (Series index=date, value=symbol or 'cash')
        """
        pass

    @property
    def name(self):
        return self.__class__.__name__


class BacktestResult:
    """回测结果封装"""

    def __init__(self, strategy_name: str, returns: pd.Series, benchmark_returns: pd.Series,
                 transactions: pd.DataFrame):
        self.strategy_name = strategy_name
        self.returns = returns
        self.benchmark_returns = benchmark_returns
        self.transactions = transactions