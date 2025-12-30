import pandas as pd
from datetime import datetime
from typing import List, Dict
from infra.repo import sync_latest_etf_data, read_data_range
from utils import DataType, Klt
from utils.const import DATETIME, CODE


class DataLoader:
    def __init__(self, start_date: str, end_date: str, auto_sync: bool = False):
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.auto_sync = auto_sync

    def load(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """
        加载数据并返回一个字典，包含所有可用的字段。

        Returns:
            Dict[str, pd.DataFrame]:
            {
                'close': df_close,
                'open': df_open,
                'volume': df_volume,
                'high': df_high,   # 如果数据源有，自动包含
                'low': df_low,     # 如果数据源有，自动包含
                ...
            }
        """
        # 1. 自动同步
        if self.auto_sync:
            try:
                print(f"[Data] Syncing latest data for {len(symbols)} symbols...")
                sync_latest_etf_data(codes=symbols, include_tick=False)
            except Exception as e:
                print(f"[Warn] Auto-sync failed: {e}")

        # 2. 读取数据 (Long Format)
        print(f"[Data] Loading local parquet files...")
        dfs = []
        for sym in symbols:
            try:
                df = read_data_range(str(sym), self.start_date, self.end_date, DataType.ETF, Klt.DAY)
                if not df.empty:
                    dfs.append(df)
            except Exception as e:
                print(f"[Warn] Failed to load {sym}: {e}")

        if not dfs:
            raise ValueError("No data found! Please check your data directory or run sync.")

        all_data = pd.concat(dfs, ignore_index=True)

        # 3. 动态转换为宽表 (Pivot)
        # 自动发现除了 datetime 和 code 之外的所有列
        feature_cols = [c for c in all_data.columns if c not in [DATETIME, CODE, 'name', 'preclose']]

        data_dict = {}
        for col in feature_cols:
            # Pivot: Index=Date, Columns=Code, Values=Col
            # 使用 float 类型以节省内存并统一格式
            try:
                wide_df = all_data.pivot(index=DATETIME, columns=CODE, values=col)
                wide_df = wide_df.sort_index().fillna(method='ffill')

                # 将列名统一转为小写，方便后续通过 kwargs 调用 (例如 'CLOSE' -> 'close')
                data_dict[col.lower()] = wide_df
                print(f"[Data] Processed field: {col.lower()} ({wide_df.shape})")
            except Exception as e:
                print(f"[Warn] Failed to pivot column {col}: {e}")

        # 兼容旧代码，确保至少有 close
        if 'close' not in data_dict and 'latest' in data_dict:  # 处理 akshare 可能的列名差异
            pass

        return data_dict