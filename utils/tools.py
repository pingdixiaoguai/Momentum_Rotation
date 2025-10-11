from typing import List, Callable,Any,Dict
from . import logger, error_logger

BatchExecuteCallBack = Callable[[List[Any], Dict], int]

def _batch_execute(input:List[Any], func:BatchExecuteCallBack, context:Dict={},batch_size:int=500, retry_times:int=3) -> int:
    total_cnt = len(input)
    logger.info(f'total_cnt={total_cnt},batch_size={batch_size}')
    if (batch_size <= 0):
        return func(input, context)
    else:
        batches = total_cnt // batch_size
        result_cnt = 0
        for i in range(batches):
            start_idx = i * batch_size
            end_idx = min( (i+1) * batch_size, total_cnt)
            retry_time = 0
            batch_input = input[start_idx:end_idx]
            context['batch_idx'] = i
            logger.info(f'batch={i}')
            while (retry_time < retry_times):
                try:
                    result_cnt = result_cnt + func(batch_input,context)
                    break
                except Exception as e:
                    retry_time = retry_time + 1
                    error_logger.error(f"Failed to batch_trans,batch={i}, caused by {e}", exc_info=True)
            if (retry_time == retry_times):
                error_logger.error(f"Retry time over max time, batch input={batch_input}")

        return result_cnt
