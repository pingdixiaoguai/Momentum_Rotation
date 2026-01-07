# 统一管理对外暴露的因子
# 这样外部引用时只需: from factors import Momentum, Volatility

from .momentum import Momentum
from .volatility import Volatility, IntradayVolatility
from .reversion import MeanReversion
from .bias import MainLineBias
from .peak import Peak  # 新增 Peak 因子导出

# 方便使用 import *
__all__ = [
    'Momentum',
    'Volatility',
    'IntradayVolatility',
    'MeanReversion',
    'MainLineBias',
    'Peak'
]