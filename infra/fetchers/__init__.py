import os
from .base import AbstractETFFetcher


def get_fetcher() -> AbstractETFFetcher:
    """根据环境变量 DATA_FETCHER 返回对应的 ETF 数据获取器实例。"""
    name = os.getenv("DATA_FETCHER", "akshare").lower()
    if name == "baostock":
        from .baostock import BaoStockFetcher
        return BaoStockFetcher()
    elif name == "akshare":
        from .akshare import AkShareFetcher
        return AkShareFetcher()
    else:
        raise ValueError(
            f"Unknown DATA_FETCHER='{name}'. Supported values: akshare, baostock"
        )
