import logging
from logging import config
from enum import Enum
from tenacity import Retrying,stop_after_attempt,wait_exponential,retry_if_exception_type,before_sleep_log
# from tenacity import RetryCallState

# 加载配置文件
config.fileConfig('./logging.conf')

# 获取不同的日志记录器
logger = logging.getLogger('appLogger')
error_logger = logging.getLogger('errorLogger')
digest_logger = logging.getLogger('digestLogger')

def log_retry_attempt(retry_state):
    """每次重试时的日志记录（包含异常信息）"""
    if retry_state.outcome.failed:
        exc = retry_state.outcome.exception()
        logger.warning(
            f"{retry_state.attempt_number}th retry attempt | "
            f"exception: {type(exc).__name__}: {exc} | "
            f"waiting: {retry_state.next_action.sleep} m to retry"
        )

# 定义重试策略
silent_retryer = Retrying(
    stop=stop_after_attempt(3),                # 最多重试3次
    wait=wait_exponential(min=1, max=10),      # 指数退避
    # retry=retry_if_exception_type(ValueError), # 只重试特定异常
    before_sleep=log_retry_attempt,  # 重试前记录日志
    reraise=False,                               # 最终抛出原始异常
    retry_error_callback=log_retry_attempt
)

class Klt(Enum):
    DAY = (101)
    MIN = (1)

class DataType(Enum):
    # 股票
    STOCK = ('stocks')
    # 指数
    INDEX = ('indexes')
    # 东财行业指数
    INDUSTRY_INDEX = ('industry_indexes')
    # etf基金
    ETF = ('etf')

    def __init__(self,dir_code):
        self.dir_code = dir_code

from .decorators import (
    log,
)

from .tools import (
    BatchExecuteCallBack,
    _batch_execute
)

__all__ = ['log','digest_logger', 'logger', 'error_logger','BatchExecuteCallBack','_batch_execute', 'Klt', 'DataType','log_retry_attempt']