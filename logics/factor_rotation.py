import pandas as pd
from typing import Dict, List, Optional
from utils import logger


def logic_factor_rotation(factor_values: Dict[str, pd.DataFrame],
                          closes: pd.DataFrame,
                          factor_weights: Dict[str, float] = {},
                          top_k: int = 1,
                          stg_flag: List[str] = [],
                          timing_period: int = 0) -> pd.DataFrame:
    """
    【逻辑函数】通用因子轮动逻辑

    复刻用户原始逻辑：
    1. 默认使用因子的【原始值 (Raw Score)】进行合成（非标准化）。
    2. 仅在 castle_stg1 开启且因子为 Mom_20 时，使用 Rank(pct=True) 并计算风控掩码。
    """

    # 0. 初始化
    castle_stg1 = "castle_stg1" in stg_flag
    risk_mask = pd.Series(False, index=closes.index)

    # 1. 计算合成因子得分
    combined_score = pd.DataFrame(0.0, index=closes.index, columns=closes.columns)

    for name, raw_score in factor_values.items():
        weight = factor_weights.get(name, 1.0)  # 默认权重 1.0

        current_score = None

        # --- 特殊逻辑: castle_stg1 ---
        # 只有在开启策略标志位，且当前因子是 Mom_20 时，才进行特殊处理
        if castle_stg1 and name == "Mom_20":
            # 1. 计算风控掩码 (全市场最大动量 < -0.1)
            row_max = raw_score.max(axis=1)
            risk_mask = risk_mask | (row_max <= -0.1)

            # 2. 使用百分比排名 (0~1)
            # 对应原代码：rank_score = raw_score.rank(axis=1, pct=True)
            current_score = raw_score.rank(axis=1, pct=True)

            # logger.info(f"[{name}] Applied Rank Normalization (Castle STG1)")
        else:
            # --- 默认逻辑 ---
            # 对应原代码：else: rank_score = raw_score
            # 直接使用原始值！这会导致数值大的因子主导结果。
            current_score = raw_score
            # logger.info(f"[{name}] Used Raw Score")

        # 累加加权得分
        combined_score += current_score * weight

    # 去除全空的行（防止干扰排名）
    combined_score = combined_score.dropna(how='all')

    # 2. 生成持仓信号 (Top K)
    # rank(ascending=False) => 分数越高排名越前 (1, 2, 3...)
    daily_rank = combined_score.rank(axis=1, ascending=False, method='min')

    # 选出排名前 top_k 的标的
    target_weights = (daily_rank <= top_k).astype(float)

    # 3. 应用特殊风控 (castle_stg1)
    if castle_stg1:
        if risk_mask.sum() > 0:
            pass
            # logger.info(f"[Risk] Castle STG1 triggered on {risk_mask.sum()} days.")

        # 将触发风控的日期权重设为 0
        target_weights.loc[risk_mask, :] = 0.0

    # 4. 归一化 (确保每天总仓位为 1.0)
    target_weights = target_weights.div(target_weights.sum(axis=1).replace(0, 1), axis=0)

    # 5. (可选) 均线择时 (Absolute Momentum / Trend Filter)
    if timing_period > 0:
        ma = closes.rolling(window=timing_period).mean()
        # 只有价格 > 均线 才持有
        trend_filter = (closes > ma).astype(int)
        target_weights = target_weights * trend_filter

    return target_weights