import pandas as pd
from datetime import datetime, date
from typing import List, Optional
from core import DataProvider
import config

# 引入现有的 infra 架构组件
from infra.repo import read_data_range, sync_latest_etf_data
from utils import DataType, Klt
from utils.const import DATETIME, CODE, OPEN, CLOSE, VOLUME


class ParquetDataProvider(DataProvider):
    """
    基于 infra/ 目录 Parquet 系统的专业数据加载器。
    实现了 DataProvider 接口，负责将存储层(Parquet)的数据转换为策略层(DataFrame)所需的格式。
    """

    def __init__(self,
                 start_date: str = config.START_DATE,
                 end_date: str = config.END_DATE,
                 auto_sync: bool = False):
        """
        :param start_date: 加载数据的开始日期 (YYYY-MM-DD)
        :param end_date: 加载数据的结束日期 (YYYY-MM-DD)
        :param auto_sync: 初始化时是否自动尝试联网同步最新数据
        """
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.auto_sync = auto_sync

    def load_data(self, symbols: List[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        加载指定标的的数据，并转换为宽表格式 (Index=Date, Columns=Symbols)。
        """
        print(
            f"[Data] Loading Parquet data for {len(symbols)} symbols from {self.start_date.date()} to {self.end_date.date()}...")

        # 1. 如果配置了自动同步，先尝试更新数据
        if self.auto_sync:
            print("[Data] Auto-syncing latest ETF data...")
            try:
                # 调用 infra.repo 中的同步逻辑
                sync_latest_etf_data(codes=symbols, include_tick=False)
            except Exception as e:
                print(f"[Data] Warning: Auto-sync failed: {e}. Using existing local data.")

        # 2. 逐个读取 Parquet 数据
        dfs = []
        for symbol in symbols:
            try:
                # 调用 infra.repo 中的读取逻辑
                df = read_data_range(
                    code=str(symbol),
                    trade_beg=self.start_date,
                    trade_end=self.end_date,
                    data_type=DataType.ETF,
                    klt=Klt.DAY
                )

                if not df.empty:
                    dfs.append(df)
                else:
                    print(f"[Data] Warning: No data found for {symbol}")
            except Exception as e:
                print(f"[Data] Error reading {symbol}: {e}")

        if not dfs:
            raise ValueError("No data loaded. Please check if 'infra/data' exists or run sync first.")

        # 3. 合并所有单一资产的长表数据
        all_data = pd.concat(dfs, ignore_index=True)

        # 4. 数据透视 (Pivot) - 将长表转换为宽表
        # infra 系统中的列名常量定义在 utils.const 中
        closes = all_data.pivot(index=DATETIME, columns=CODE, values=CLOSE)
        opens = all_data.pivot(index=DATETIME, columns=CODE, values=OPEN)
        volumes = all_data.pivot(index=DATETIME, columns=CODE, values=VOLUME)

        # 5. 数据清洗
        # 转换索引为 DatetimeIndex 并排序
        for df in [closes, opens, volumes]:
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            # 处理缺失值：向前填充 (ffill)
            df.fillna(method='ffill', inplace=True)
            # 去除全空的行 (可能是非交易日)
            df.dropna(how='all', inplace=True)

        print(f"[Data] Loaded successfully. Shape: {closes.shape}")
        return closes, opens, volumes