import os
import time
import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime
from utils.const import (
    DATETIME, CODE, NAME, OPEN, HIGH, LOW, CLOSE,
    VOLUME, AMOUNT, PRECLOSE, PRICE_CHG, PE_TTM, PB_TTM, TURN,
    COLUMNS, COLUMNS_TYPE, TICK_COLUMNS, TICK_COLUMNS_TYPE,
)
from .base import AbstractETFFetcher

_TICK_INTERVAL = float(os.getenv("TICK_INTERVAL", "0.2"))


def _retry(func, kwargs: dict, retry_times: int = 3):
    for attempt in range(retry_times + 1):
        try:
            return func(**kwargs)
        except Exception:
            if attempt == retry_times:
                return None
            time.sleep(_TICK_INTERVAL)
    return None


class AkShareFetcher(AbstractETFFetcher):
    supports_tick = True
    supports_full_list = True

    def fetch_daily(self, code: str, name: str,
                    start_date: datetime, end_date: datetime) -> pd.DataFrame:
        context = {
            'symbol': code,
            'period': 'daily',
            'start_date': start_date.strftime('%Y%m%d'),
            'end_date': end_date.strftime('%Y%m%d'),
            'adjust': 'hfq',
        }
        df = _retry(ak.fund_etf_hist_em, context, retry_times=3)
        if df is None or df.empty:
            return pd.DataFrame()
        df.rename(columns={
            '日期': DATETIME, '开盘': OPEN, '收盘': CLOSE, '最高': HIGH,
            '最低': LOW, '成交量': VOLUME, '成交额': AMOUNT,
            '涨跌幅': PRICE_CHG, '换手率': TURN,
        }, inplace=True)
        df[DATETIME] = pd.to_datetime(df[DATETIME])
        df[CODE] = code
        df[NAME] = name
        df[VOLUME] = df[VOLUME] * 100
        df[PE_TTM] = np.nan
        df[PB_TTM] = np.nan
        df[PRECLOSE] = np.nan
        return df[COLUMNS].astype(COLUMNS_TYPE)

    def fetch_tick(self, code: str, name: str, date: datetime) -> pd.DataFrame:
        # 注意：东方财富 ETF 分时接口要求传 name（ETF 名称），而非 code
        context = {'symbol': name, 'period': '1'}
        df = _retry(ak.fund_etf_hist_min_em, context, retry_times=3)
        if df is None or df.empty:
            return pd.DataFrame()
        df.rename(columns={
            '日期时间': DATETIME, '开盘': OPEN, '收盘': CLOSE, '最高': HIGH,
            '最低': LOW, '成交量': VOLUME, '成交额': AMOUNT,
        }, inplace=True)
        df[DATETIME] = pd.to_datetime(df[DATETIME])
        df[CODE] = code
        df[NAME] = name
        df[VOLUME] = df[VOLUME] * 100
        return df[TICK_COLUMNS].astype(TICK_COLUMNS_TYPE)
