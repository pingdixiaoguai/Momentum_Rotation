from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime


class AbstractETFFetcher(ABC):
    supports_tick: bool = False
    supports_full_list: bool = True  # 是否支持自动拉取全量 ETF 列表（codes=[] 路径）
    needs_price_normalization: bool = False  # 是否需要归一化价格（BaoStock ETF 不支持复权）

    @abstractmethod
    def fetch_daily(self, code: str, name: str,
                    start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        返回符合 COLUMNS / COLUMNS_TYPE 格式的 DataFrame。
        - volume 单位：股（shares）
        - 不支持的字段（如 pe_ttm、pb_ttm）填 np.nan
        - 若无数据，返回空 DataFrame
        """
        pass

    def fetch_tick(self, code: str, name: str, date: datetime) -> pd.DataFrame:
        """可选：返回当天分时数据（TICK_COLUMNS 格式）。默认返回空 DataFrame。"""
        return pd.DataFrame()
