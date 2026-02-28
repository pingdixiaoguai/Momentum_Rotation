# package
# __init__.py
import os,dotenv
from pathlib import Path

dotenv.load_dotenv()
ROOT_DATA_DIR = Path(str(os.getenv("DATA_DIR")))
TICK_INTERVAL = float(os.getenv("TICK_INTERVAL", "0.2"))
DATA_FETCHER = os.getenv("DATA_FETCHER", "akshare")

from .repo import (
    sync_latest_industry_data,
    sync_latest_etf_data,
    sync_latest_index_data,
    sync_latest_stock_data,
    sync_latest_all_data,
    get_latest_sync_date,
    get_latest_trade_date,
    find_last_trade_date
)
from .fetchers import get_fetcher
__all__ = ['sync_latest_industry_data','sync_latest_index_data','sync_latest_stock_data','sync_latest_all_data','get_latest_sync_date','get_latest_trade_date', 'find_last_trade_date','sync_latest_etf_data','get_fetcher','DATA_FETCHER']