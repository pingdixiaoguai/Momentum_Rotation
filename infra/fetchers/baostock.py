import pandas as pd
import numpy as np
from datetime import datetime
from utils.const import (
    DATETIME, CODE, NAME, OPEN, HIGH, LOW, CLOSE,
    VOLUME, AMOUNT, PRECLOSE, PRICE_CHG, PE_TTM, PB_TTM, TURN,
    COLUMNS, COLUMNS_TYPE,
)
from .base import AbstractETFFetcher
from utils import logger


def _to_bs_code(code: str) -> str:
    """将 A 股代码转换为 BaoStock 格式（sh.510300 / sz.159915）"""
    if code.startswith(('5', '6')):
        return f'sh.{code}'
    elif code.startswith(('1', '3')):
        return f'sz.{code}'
    else:
        raise ValueError(f"Cannot determine exchange for ETF code: {code}")


class BaoStockFetcher(AbstractETFFetcher):
    supports_tick = False
    supports_full_list = False  # 不支持自动拉取全量列表，需用户指定 codes
    needs_price_normalization = True  # BaoStock 对 ETF 不支持复权，需在 repo 层做价格归一化

    def __init__(self):
        import baostock as bs
        self._bs = bs
        result = bs.login()
        if result.error_code != '0':
            raise RuntimeError(f"BaoStock login failed: {result.error_msg}")

    def __del__(self):
        try:
            self._bs.logout()
        except Exception:
            pass

    def fetch_daily(self, code: str, name: str,
                    start_date: datetime, end_date: datetime) -> pd.DataFrame:
        bs_code = _to_bs_code(code)
        fields = 'date,open,high,low,close,preclose,volume,amount,turn,pctChg'
        # adjustflag='1' = 后复权，对应 AkShare 的 hfq
        rs = self._bs.query_history_k_data_plus(
            bs_code, fields,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            frequency='d',
            adjustflag='3',  # 不复权：BaoStock 对 ETF 三种 adjustflag 均返回相同值（实际均不复权）
        )
        if rs.error_code != '0':
            logger.error(f"BaoStock query failed for {code}: {rs.error_msg}")
            return pd.DataFrame()

        rows = []
        while rs.error_code == '0' and rs.next():
            rows.append(rs.get_row_data())
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=rs.fields)
        # BaoStock 返回全是字符串，转为数值
        for col in df.columns:
            if col != 'date':
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df.rename(columns={
            'date': DATETIME,
            'open': OPEN,
            'high': HIGH,
            'low': LOW,
            'close': CLOSE,
            'preclose': PRECLOSE,
            'volume': VOLUME,
            'amount': AMOUNT,
            'turn': TURN,
            'pctChg': PRICE_CHG,
        }, inplace=True)
        df[DATETIME] = pd.to_datetime(df[DATETIME])
        df[CODE] = code
        df[NAME] = name
        df[PE_TTM] = np.nan
        df[PB_TTM] = np.nan
        # ⚠️ BaoStock volume 单位为股（shares），无需 *100
        # 首次运行时请人工核验 volume 量级是否与 AkShare 一致
        return df[COLUMNS].astype(COLUMNS_TYPE)
