import os
import time as time_module
import pandas as pd
from utils import logger, Klt, DataType
from utils.const import *
from cachetools import TTLCache, cached
from . import ROOT_DATA_DIR, TICK_INTERVAL
from .fetchers import get_fetcher
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from cachetools import TTLCache, cached
from datetime import datetime, timedelta, date, time
from tqdm import tqdm
import akshare as ak
import numpy as np


def get_all_index_df() -> pd.DataFrame:
    index_stock_info = ak.index_stock_info()
    index_stock_info.rename(columns={'index_code': CODE, 'display_name': NAME}, inplace=True)
    return index_stock_info[[CODE, NAME]]


def get_all_stock_df() -> pd.DataFrame:
    stock_qoute = ak.stock_zh_a_spot_em()
    stock_qoute.rename(columns={'代码': CODE, '名称': NAME}, inplace=True)
    return stock_qoute[[CODE, NAME]]


def get_data_dir(dataType: DataType) -> Path:
    return ROOT_DATA_DIR / dataType.value


def _execute_with_retry(func: Callable, context: Dict, retry_times: int = 0, silent: bool = True) -> Any:
    retried = -1
    while (retried < retry_times):
        try:
            return func(**context)
        except Exception as e:
            logger.error(f'func={func.__name__},context={context},Error:{e}')
            if (retry_times > 0):
                retried += 1
            time_module.sleep(TICK_INTERVAL)

    if (silent):
        logger.error(f'Failed to execute func={func},context={context}.')
        return None
    else:
        raise Exception(f'Failed to execute func={func},context={context}.')


def _get_latest_trade_date_baostock() -> date:
    """使用 BaoStock 获取最新交易日（DATA_FETCHER=baostock 时使用）"""
    import baostock as bs
    result = bs.login()
    if result.error_code != '0':
        raise RuntimeError(f"BaoStock login failed: {result.error_msg}")
    try:
        today = date.today()
        start = (today - timedelta(days=10)).strftime('%Y-%m-%d')
        end = today.strftime('%Y-%m-%d')
        rs = bs.query_trade_dates(start_date=start, end_date=end)
        trade_dates = []
        while rs.error_code == '0' and rs.next():
            row = rs.get_row_data()
            if row[1] == '1':  # is_trading_day
                trade_dates.append(row[0])
        return date.fromisoformat(max(trade_dates)) if trade_dates else today
    finally:
        bs.logout()


@cached(TTLCache(maxsize=2, ttl=60 * 60 * 3))
def get_latest_trade_date() -> date:
    if os.getenv("DATA_FETCHER", "akshare").lower() == "baostock":
        return _get_latest_trade_date_baostock()
    context = {'symbol': '小金属', 'period': '60'}
    df = _execute_with_retry(ak.stock_board_industry_hist_min_em, context, 3)
    trade_time = datetime.strptime(df['日期时间'].max(), '%Y-%m-%d %H:%M')
    return date(trade_time.year, trade_time.month, trade_time.day)


def save_date(df: pd.DataFrame, data_dir: Path, is_tick: bool):
    """
    保存数据到 Parquet 文件
    修复：增加空值过滤和年份强制取整，防止出现 '2026.0' 这样的文件夹
    """
    if (df.empty): return

    # 1. 确保日期列没有 NaT (脏数据会导致年份变成 float)
    df = df.dropna(subset=[DATETIME])
    if df.empty: return

    # 2. 去重，保留最新的
    df = df.drop_duplicates(subset=[DATETIME, CODE], keep='last')

    code_df = df.groupby(df[CODE])
    for code, code_group in code_df:
        # 注意：这里如果 Series 含有浮点数，dt.year 可能是 float
        grouped_df = code_group.groupby(df[DATETIME].dt.year)

        for year, group in grouped_df:
            # --- 修复核心：强制转 int 再转 str，避免 '2026.0' ---
            try:
                year_str = str(int(year))
            except Exception:
                # 兜底：如果 year 真是无法转换的怪东西，直接跳过
                logger.warning(f"Invalid year detected for {code}: {year}, skipping...")
                continue
            # -----------------------------------------------

            if is_tick:
                index_year_dir = data_dir / code / year_str / 'tick'
                index_year_dir.mkdir(parents=True, exist_ok=True)
                day_grouped_df = group.groupby(df[DATETIME].dt.date)
                for day, day_group in day_grouped_df:
                    day_str = day.strftime('%Y-%m-%d')
                    table = pa.Table.from_pandas(day_group, preserve_index=False)
                    pq.write_table(table, index_year_dir / f'{day_str}.parquet')
            else:
                index_year_dir = data_dir / code / year_str
                index_year_dir.mkdir(parents=True, exist_ok=True)
                data_path = index_year_dir / f'{year_str}.parquet'

                dfs = []
                if data_path.exists():
                    try:
                        temp_table = pq.read_table(data_path)
                        dfs.append(temp_table.to_pandas())
                    except Exception as e:
                        logger.error(f"Failed to read existing parquet {data_path}: {e}")

                dfs.append(group)

                # 合并并再次去重
                full_df = pd.concat(dfs, ignore_index=True, sort=False)
                full_df = full_df.drop_duplicates(subset=[DATETIME, CODE], keep='last')

                table = pa.Table.from_pandas(full_df, preserve_index=False)
                pq.write_table(table, data_path)


def sync_latest_stock_data(codes: List[str] = [], include_tick: bool = True) -> None:
    beg_date = datetime.combine(get_latest_trade_date(), time())
    end_date = beg_date + timedelta(days=1)
    codes = list(set(codes))

    stock_root_dir = get_data_dir(DataType.STOCK)
    stock_root_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f'Start to synchronize stock data')
    latest_df = _execute_with_retry(ak.stock_zh_a_spot_em, {})
    stock_columns_map = {'代码': CODE, '名称': NAME, '今开': OPEN, '昨收': PRECLOSE, '最新价': CLOSE, '最高': HIGH,
                         '最低': LOW, '成交量': VOLUME, '成交额': AMOUNT, '涨跌幅': PRICE_CHG, '换手率': TURN,
                         '市盈率-动态': PE_TTM, '市净率': PB_TTM}
    latest_df.rename(columns=stock_columns_map, inplace=True)
    latest_df[DATETIME] = beg_date
    latest_df[VOLUME] *= 100
    latest_df = latest_df[COLUMNS]
    latest_df.astype(COLUMNS_TYPE)
    stock_df = latest_df[~latest_df[CLOSE].isna()]
    if (len(codes) != 0):
        stock_df = stock_df[stock_df[CODE].isin(codes)]
    save_date(stock_df, stock_root_dir, False)
    logger.info(f'Finish synchronizing stock data')

    if not include_tick: return
    logger.info(f'Start to synchronize stock tick data')
    # 降序排列，使用000001作为当天同步的标识
    stock_df = stock_df.sort_values(by=CODE, ascending=False)
    for _, row in tqdm(stock_df.iterrows(), total=stock_df.shape[0]):
        code = row[CODE]
        name = row[NAME]
        context = {'symbol': code, 'start_date': beg_date.strftime('%Y-%m-%d %H:%M:%S'),
                   'end_date': end_date.strftime('%Y-%m-%d %H:%M:%S'), 'period': '1', 'adjust': 'qfq'}
        df = _execute_with_retry(ak.stock_zh_a_hist_min_em, context, retry_times=3)
        if (df is None or df.empty):
            logger.info(f'No data for {code}')
            continue
        df.rename(columns={'时间': DATETIME, '开盘': OPEN, '收盘': CLOSE, '最高': HIGH, '最低': LOW, '成交量': VOLUME,
                           '成交额': AMOUNT, '换手率': TURN}, inplace=True)
        df[CODE] = code
        df[NAME] = name
        df[DATETIME] = pd.to_datetime(df[DATETIME])
        df[VOLUME] *= 100
        df = df[TICK_COLUMNS]
        save_date(df, stock_root_dir, True)
        time_module.sleep(TICK_INTERVAL)
    logger.info(f'Finish synchronizing stock tick data')


def sync_latest_index_data(include_tick: bool = True) -> None:
    beg_date = datetime.combine(get_latest_trade_date(), time())
    end_date = beg_date + timedelta(days=1)
    index_root_dir = get_data_dir(DataType.INDEX)
    symbols = ["沪深重要指数", "上证系列指数", "深证系列指数", "指数成份", "中证系列指数"]

    logger.info(f'Start to synchronize indexes data')
    dfs = []
    for symbol in tqdm(symbols):
        df = ak.stock_zh_index_spot_em(symbol=symbol)
        if (df is not None):
            df.rename(
                columns={'代码': CODE, '名称': NAME, '今开': OPEN, '昨收': PRECLOSE, '最新价': CLOSE, '最高': HIGH,
                         '最低': LOW, '成交量': VOLUME, '成交额': AMOUNT, '涨跌幅': PRICE_CHG}, inplace=True)
            df[DATETIME] = beg_date
            df[DATETIME] = pd.to_datetime(df[DATETIME])
            df[TURN] = np.nan
            df[PE_TTM] = np.nan
            df[PB_TTM] = np.nan
            df[VOLUME] *= 100
            df = df[COLUMNS]
            df = df.astype(COLUMNS_TYPE)
            dfs.append(df)
    all_index = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    all_index = all_index.drop_duplicates(subset=[DATETIME, CODE])
    all_index = all_index[~all_index[CLOSE].isna()]
    save_date(all_index, index_root_dir, False)
    logger.info(f'Finish synchronizing indexes data')

    if not include_tick: return
    logger.info(f'Start to synchronize indexes tick data')
    tick_index = all_index[all_index[CODE] == '000001']
    for _, row in tqdm(tick_index.iterrows(), total=tick_index.shape[0]):
        code = row[CODE]
        name = row[NAME]
        context = {'symbol': code, 'start_date': beg_date.strftime('%Y-%m-%d %H:%M:%S'),
                   'end_date': end_date.strftime('%Y-%m-%d %H:%M:%S'), 'period': '1'}
        df = _execute_with_retry(ak.index_zh_a_hist_min_em, context)
        if (df is None or df.empty):
            logger.info(f'No data for {code}')
            continue
        df.rename(columns={'时间': DATETIME, '开盘': OPEN, '收盘': CLOSE, '最高': HIGH, '最低': LOW, '成交量': VOLUME,
                           '成交额': AMOUNT}, inplace=True)
        df[CODE] = code
        df[NAME] = name
        df[DATETIME] = pd.to_datetime(df[DATETIME])
        df[VOLUME] *= 100
        df = df[TICK_COLUMNS]
        save_date(df, index_root_dir, True)
        time_module.sleep(TICK_INTERVAL)
    logger.info(f'Finish synchronizing indexes tick data')


def sync_latest_industry_data(codes: List[str] = [], include_tick: bool = True) -> None:
    codes = list(set(codes))
    industries = ak.stock_board_industry_name_em()[['板块名称', '板块代码']]
    industries.rename(columns={'板块名称': NAME, '板块代码': CODE}, inplace=True)
    if (len(codes) > 0):
        industries = industries[industries[CODE].isin(codes)]
    index_root_dir = get_data_dir(DataType.INDUSTRY_INDEX)

    beg_date = datetime.combine(get_latest_trade_date(), time())
    end_date = beg_date + timedelta(days=1)
    dfs = []
    logger.info(f'Start to synchronize industry indexes data')
    for _, row in tqdm(industries.iterrows(), total=industries.shape[0]):
        code = row[CODE]
        name = row[NAME]
        context = {'symbol': name, 'period': '日k', 'start_date': beg_date.strftime('%Y%m%d'),
                   'end_date': end_date.strftime('%Y%m%d'), 'adjust': ''}
        df = _execute_with_retry(ak.stock_board_industry_hist_em, context, 3)
        df.rename(columns={'日期': DATETIME, '开盘': OPEN, '收盘': CLOSE, '最高': HIGH, '最低': LOW, '成交量': VOLUME,
                           '成交额': AMOUNT, '涨跌幅': PRICE_CHG, '换手率': TURN}, inplace=True)
        df[DATETIME] = pd.to_datetime(df[DATETIME])
        df[CODE] = code
        df[NAME] = name
        df[VOLUME] *= 100
        df[PE_TTM] = np.nan
        df[PB_TTM] = np.nan
        df[PRECLOSE] = np.nan
        df = df[COLUMNS]
        df = df.astype(COLUMNS_TYPE)
        dfs.append(df)
    save_date(pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(), index_root_dir, False)
    logger.info(f'Finish synchronizing industry indexes data')

    if not include_tick: return
    dfs = []
    logger.info(f'Start to synchronize industry indexes tick data')
    for _, row in tqdm(industries.iterrows(), total=industries.shape[0]):
        code = row[CODE]
        name = row[NAME]
        context = {'symbol': name, 'period': '1'}
        df = _execute_with_retry(ak.stock_board_industry_hist_min_em, context, 3)
        df.rename(
            columns={'日期时间': DATETIME, '开盘': OPEN, '收盘': CLOSE, '最高': HIGH, '最低': LOW, '成交量': VOLUME,
                     '成交额': AMOUNT}, inplace=True)
        df[DATETIME] = pd.to_datetime(df[DATETIME])
        df[CODE] = code
        df[NAME] = name
        df[VOLUME] *= 100
        df = df[TICK_COLUMNS]
        dfs.append(df)
        time_module.sleep(TICK_INTERVAL)
    save_date(pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(), index_root_dir, True)
    logger.info(f'Finish synchronizing industry indexes tick data')


def sync_latest_etf_data(codes: List[str] = [],
                         include_tick: bool = True,
                         beg_date: datetime = datetime.combine(get_latest_trade_date(), time()),
                         end_date: datetime = datetime.combine(get_latest_trade_date(), time()) + timedelta(days=1)
                         ) -> None:
    codes = list(set(codes))
    etf_root_dir = get_data_dir(DataType.ETF)
    fetcher = get_fetcher()

    # --- 优化：仅在未指定 codes 时拉取全量列表 ---
    target_df = pd.DataFrame()

    if len(codes) == 0:
        if not fetcher.supports_full_list:
            logger.error(
                f"{fetcher.__class__.__name__} does not support auto-fetching the full ETF list. "
                "Please specify 'codes' explicitly in sync_latest_etf_data()."
            )
            return
        # Case A: 用户未指定代码 -> 拉取全量列表
        try:
            logger.info("Fetching full ETF list from AkShare (no codes provided)...")
            etf_info = ak.fund_etf_spot_em()
            etf_info = etf_info[['代码', '名称']]
            etf_info.rename(columns={'名称': NAME, '代码': CODE}, inplace=True)
            etf_info[CODE] = etf_info[CODE].astype(str).str.strip()
            target_df = etf_info
        except Exception as e:
            logger.error(f"Failed to fetch ETF list: {e}")
            return
    else:
        # Case B: 用户指定了代码 -> 跳过全量列表拉取，直接构建，尝试从本地恢复名称
        logger.info(f"Using provided ETF codes: {codes} (Skipping full list fetch)")
        data_list = []
        for code in codes:
            code = str(code).strip()
            name = code  # 默认名字为代码，之后尝试从本地恢复

            # 尝试从本地 Parquet 文件读取真实名称 (Name)
            try:
                target_code_dir = etf_root_dir / code
                if target_code_dir.exists():
                    # 找到最近的年份文件夹
                    years = [y for y in os.listdir(target_code_dir) if y.isdigit()]
                    if years:
                        max_year = max(years, key=int)
                        daily_file = target_code_dir / max_year / f"{max_year}.parquet"
                        if daily_file.exists():
                            # 快速读取 Name 列（只读一行即可）
                            table = pq.read_table(daily_file, columns=[NAME])
                            if table.num_rows > 0:
                                name_val = table.column(NAME)[0].as_py()
                                if name_val:
                                    name = name_val
            except Exception:
                pass  # 如果读取失败，就继续使用 code 作为 name

            data_list.append({CODE: code, NAME: name})

        target_df = pd.DataFrame(data_list)

    # 3. 开始遍历同步
    # 移除 dfs 列表，改为 loop 内直接 save
    logger.info(f'Start to synchronize ETF data (Count: {len(target_df)})')

    for _, row in tqdm(target_df.iterrows(), total=target_df.shape[0]):
        code = row[CODE]
        name = row[NAME]

        # --- 优化：每只 ETF 单独处理，互不影响 ---
        try:
            # 默认下载范围
            fetch_start = beg_date

            # 1. 检查本地已有数据的最新日期 (实现真正的增量更新)
            local_latest_date = None
            try:
                target_code_dir = etf_root_dir / code
                if target_code_dir.exists():
                    # 寻找年份最大的文件夹
                    years = [y for y in os.listdir(target_code_dir) if y.isdigit()]
                    if years:
                        max_year = max(years, key=int)
                        # 读取该年 daily parquet
                        daily_file = target_code_dir / max_year / f"{max_year}.parquet"
                        if daily_file.exists():
                            # 快速读取 datetime 列的最大值
                            table = pq.read_table(daily_file, columns=[DATETIME])
                            if table.num_rows > 0:
                                max_ts = table.column(DATETIME).to_pandas().max()
                                # 转换为 python datetime
                                if pd.notna(max_ts):
                                    local_latest_date = max_ts.to_pydatetime()
            except Exception as check_err:
                # 检查出错不影响下载，降级为全量
                logger.warning(f"Failed to check local history for {code}: {check_err}")

            # 2. 动态调整下载开始时间
            if local_latest_date:
                # 如果本地最新日期 >= 请求开始日期，说明前面都已经有了
                if local_latest_date >= fetch_start:
                    # 从本地最新的下一天开始下
                    fetch_start = local_latest_date + timedelta(days=1)

            # 3. 判断是否需要下载
            if fetch_start > end_date:
                logger.info(f"Skipping {code}: Local data ({local_latest_date.date()}) covers request.")
                continue

            logger.info(f"Syncing {code} from {fetch_start.date()} to {end_date.date()}...")

            df = fetcher.fetch_daily(code, name, fetch_start, end_date)

            if not df.empty:
                save_date(df, etf_root_dir, False)
            else:
                logger.warning(f"No daily data fetched for {code}")

        except Exception as e:
            logger.error(f"Failed to sync ETF {code}: {e}")
            continue  # 关键：出错后继续下一个，不中断

    logger.info(f'Finish synchronizing etf data')

    if not include_tick: return

    if not fetcher.supports_tick:
        logger.info(f'Skipping ETF tick sync ({fetcher.__class__.__name__} does not support tick data)')
        return

    logger.info(f'Start to synchronize etf tick data')
    for _, row in tqdm(target_df.iterrows(), total=target_df.shape[0]):
        code = row[CODE]
        name = row[NAME]

        try:
            target_tick_file = etf_root_dir / code / str(
                beg_date.year) / 'tick' / f'{beg_date.strftime("%Y-%m-%d")}.parquet'
            if target_tick_file.exists():
                continue

            df = fetcher.fetch_tick(code, name, beg_date)
            if not df.empty:
                save_date(df, etf_root_dir, True)

            time_module.sleep(TICK_INTERVAL)
        except Exception as e:
            logger.error(f"Failed to sync ETF tick {code}: {e}")
            continue

    logger.info(f'Finish synchronizing etf tick data')


def sync_latest_all_data(include_tick: bool = True) -> None:
    logger.info(f'Start to synchronize the data.')
    sync_latest_industry_data(include_tick=include_tick)
    sync_latest_index_data(include_tick=include_tick)
    sync_latest_stock_data(include_tick=include_tick)
    sync_latest_etf_data(include_tick=include_tick)
    logger.info(f'Complete synchronizing the data.')


def read_data_range(code: str,
                    trade_beg: datetime,
                    trade_end: datetime,
                    data_type: DataType,
                    klt: Klt) -> pd.DataFrame:
    """查询时间范围内的k线图数据,(trade_beg,trade_end]

    Args:
        code: 代码
        trade_beg (str): %Y-%m-%d
        trade_end (str): %Y-%m-%d

    Raises:
        RuntimeError: _description_

    Returns:
        pd.DataFrame: _description_
    """
    """读取指定日期范围数据（自动合并季度文件）"""
    dataset_path = ROOT_DATA_DIR / data_type.dir_code / code
    start_dt = pd.to_datetime(trade_beg)
    end_dt = pd.to_datetime(trade_end)

    # 自动发现相关年份
    years = range(start_dt.year, end_dt.year + 1)

    if (klt == Klt.MIN):
        data_paths = []
        date_range = pd.date_range(start=trade_beg, end=trade_end).to_list()
        for date in date_range:
            data_path = dataset_path / str(date.year) / 'tick' / (date.strftime("%Y-%m-%d") + '.parquet')
            if (not data_path.exists()):
                continue
            data_paths.append(data_path)
        if (len(data_paths) > 0):
            dataset = pq.ParquetDataset(
                data_paths,
                filters=[
                    (DATETIME, '>', start_dt),
                    (DATETIME, '<=', end_dt)
                ]
            )
            return dataset.read().to_pandas().astype(TICK_COLUMNS_TYPE)
        else:
            return pd.DataFrame()
    elif (klt == Klt.DAY):
        dfs = []
        for year in years:
            data_path = dataset_path / str(year)
            if (not data_path.exists()):
                continue
            dataset = pq.ParquetDataset(
                data_path,
                filters=[
                    (DATETIME, '>', start_dt),
                    (DATETIME, '<=', end_dt)
                ],
                ignore_prefixes=['tick']  # 排除tick分时数据
            )
            dfs.append(dataset.read().to_pandas())
        return pd.concat(dfs, ignore_index=True).astype(COLUMNS_TYPE) if dfs else pd.DataFrame()
    else:
        raise Exception(f'unsupported klt={klt}')


def get_latest_sync_date() -> date:
    """find_latest_sync_date
    """
    stock_dir = get_data_dir(DataType.STOCK) / '000001'
    if (not stock_dir.exists()): return date.fromisoformat('2000-01-01')
    dirs = [d for d in os.listdir(stock_dir) if os.path.isdir(os.path.join(stock_dir, d))]

    # 按字母顺序排序并获取最大值
    if dirs:
        year = max(dirs)
        tick_dir = stock_dir / year / 'tick'
        ticks = os.listdir(tick_dir)
        if ticks:
            return date.fromisoformat(max(ticks).split('.')[0])
        else:
            return date.fromisoformat(year + '-01-01')
    else:
        return date.fromisoformat('2000-01-01')


@cached(TTLCache(maxsize=1, ttl=60 * 60 * 3))
def find_trade_date() -> pd.DataFrame:
    """查找交易日期

    Returns:
        pd.DataFrame:
        trade_date
        0     1990-12-19
        1     1990-12-20
        2     1990-12-21
        3     1990-12-24
        4     1990-12-25
        ...          ...
        8550  2025-12-25
        8551  2025-12-26
        8552  2025-12-29
        8553  2025-12-30
    """
    df = ak.tool_trade_date_hist_sina()
    return df.sort_values('trade_date').reset_index(drop=True)


def find_last_trade_date(trade_date_str: str) -> date:
    df = find_trade_date()
    trade_date = date.fromisoformat(trade_date_str)
    previous_dates = df[df['trade_date'] < trade_date]
    return previous_dates['trade_date'].max()


if __name__ == '__main__':
    sync_latest_all_data()