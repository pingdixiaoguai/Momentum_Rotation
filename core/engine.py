import pandas as pd

import config
from utils import logger
from .base import Strategy


class RealWorldEngine:
    """
    真实世界回测引擎，采用 T+1 开盘执行模型。

    规则：
    - T 日收盘产生信号 → T+1 日开盘执行交易
    - 持仓日 (Hold): close_t / close_{t-1} - 1   （吃满全天）
    - 买入日 (Buy):  (close - open) / open        （只吃日内，跳空不参与）
    - 卖出日 (Sell): open / prev_close - 1        （只吃隔夜，开盘即卖）
    """

    def run(self, strategy: Strategy, **data_dict) -> pd.Series:
        logger.info(f"Running strategy: {strategy.name} ...")

        if 'open' not in data_dict or 'close' not in data_dict:
            raise ValueError("RealWorldEngine requires both 'open' and 'close' price data.")

        opens  = data_dict['open']
        closes = data_dict['close']

        # 1. T 日信号 → T+1 持仓
        weights       = strategy.generate_target_weights(**data_dict)
        positions     = weights.shift(1).fillna(0)
        prev_positions = positions.shift(1).fillna(0)

        # 2. 三种持仓状态的收益
        base_daily_rets = closes.pct_change().fillna(0)
        intraday_rets   = (closes - opens) / opens
        overnight_rets  = (opens / closes.shift(1) - 1).fillna(0)

        mask_hold = (positions == 1) & (prev_positions == 1)
        mask_buy  = (positions == 1) & (prev_positions == 0)
        mask_sell = (positions == 0) & (prev_positions == 1)

        total_ret = pd.DataFrame(0.0, index=closes.index, columns=closes.columns)
        total_ret[mask_hold] = base_daily_rets[mask_hold]
        total_ret[mask_buy]  = intraday_rets[mask_buy]
        total_ret[mask_sell] = overnight_rets[mask_sell]

        strategy_rets = total_ret.sum(axis=1)

        # 3. 扣除交易成本（仅在换仓日）
        cost     = getattr(config, 'TRANSACTION_COST', 0.0005)
        turnover = (positions - prev_positions).abs()
        strategy_rets -= (turnover * cost).sum(axis=1)

        return strategy_rets
