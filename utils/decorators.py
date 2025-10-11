from utils import digest_logger
import time
from functools import wraps

def log(func,log_args:bool=True):
    @wraps(func)
    def log_interceptor(*args, **kwargs):
        tic = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            toc = time.time()
            if (log_args): digest_logger.info(f'{func.__name__},{toc-tic :.3f},args={args},kwargs={kwargs}')
            else:digest_logger.info(f'{func.__name__},{toc-tic :.3f}')
    return log_interceptor