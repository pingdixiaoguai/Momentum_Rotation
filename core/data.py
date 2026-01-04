import sys
import os

# 获取项目根目录（Quant目录）
project_root = "/Users/hujiaoyuan/Desktop/Quant"
sys.path.insert(0, project_root)

# 或者自动获取（推荐）
current_dir = os.path.dirname(os.path.abspath(__file__))  # core目录
project_root = os.path.dirname(os.path.dirname(current_dir))  # Quant目录
sys.path.insert(0, project_root)

# 现在导入
from infra.repo import sync_latest_etf_data, read_data_range



import pandas as pd
from datetime import datetime
from typing import List, Dict
# from infra.repo import sync_latest_etf_data, read_data_range
from utils import DataType, Klt, logger
from utils.const import DATETIME, CODE


class DataLoader:
    def __init__(self, start_date: str, end_date: str, auto_sync: bool = False):
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.auto_sync = auto_sync

    def load(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """
        加载数据并返回一个字典，包含所有可用的字段。
        """
        # 1. 自动同步
        if self.auto_sync:
            try:
                logger.info(
                    f"[Data] Syncing data from {self.start_date.date()} to {self.end_date.date()} for {len(symbols)} symbols...")

                # --- 修复：显式传递时间范围，确保同步该段历史数据 ---
                sync_latest_etf_data(
                    codes=symbols,
                    include_tick=False,
                    beg_date=self.start_date,
                    end_date=self.end_date
                )
                # -----------------------------------------------

            except Exception as e:
                logger.warning(f"[Data] Auto-sync failed: {e}")

        # 2. 读取数据 (Long Format)
        logger.info(f"[Data] Loading local parquet files...")
        dfs = []
        for sym in symbols:
            try:
                df = read_data_range(str(sym), self.start_date, self.end_date, DataType.ETF, Klt.DAY)
                if not df.empty:
                    dfs.append(df)
            except Exception as e:
                logger.warning(f"[Data] Failed to load {sym}: {e}")

        if not dfs:
            error_msg = "No data found! Please check your data directory or run sync."
            logger.error(error_msg)
            raise ValueError(error_msg)

        all_data = pd.concat(dfs, ignore_index=True)

        # 3. 动态转换为宽表 (Pivot)
        # 自动发现除了 datetime 和 code 之外的所有列
        feature_cols = [c for c in all_data.columns if c not in [DATETIME, CODE, 'name', 'preclose']]

        data_dict = {}
        for col in feature_cols:
            try:
                # Pivot: Index=Date, Columns=Code, Values=Col
                wide_df = all_data.pivot(index=DATETIME, columns=CODE, values=col)
                wide_df = wide_df.sort_index().ffill()

                # 将列名统一转为小写 (e.g. 'CLOSE' -> 'close')
                data_dict[col.lower()] = wide_df
                logger.info(f"[Data] Processed field: {col.lower()} (Shape: {wide_df.shape})")
            except Exception as e:
                logger.warning(f"[Data] Failed to pivot column {col}: {e}")

        return data_dict