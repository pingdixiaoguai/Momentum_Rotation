import pandas as pd
from typing import Dict, List, Optional


def logic_factor_rotation(factor_values: Dict[str, pd.DataFrame],
                          closes: pd.DataFrame,
                          factor_weights: Dict[str, float] = {},
                          top_k: int = 1,
                          stg_flag: List[str] = [],
                          timing_period: int = 0) -> pd.DataFrame:
    """
    【逻辑函数】通用因子轮动逻辑
    实现了原 FactorRotationStrategy 的所有功能，包括 castle_stg1 风控和均线择时。

    :param factor_values: 计算好的因子值字典 {'Mom_20': df, ...}
    :param closes: 收盘价 DataFrame
    :param factor_weights: 因子权重字典 {'Mom_20': 1.0, 'Peak_20': 0.5}
    :param top_k: 选股数量
    :param stg_flag: 策略标志位列表，如 ['castle_stg1']
    :param timing_period: 均线择时周期，0 表示不启用
    """

    # 0. 初始化
    castle_stg1 = "castle_stg1" in stg_flag
    risk_mask = pd.Series(False, index=closes.index)

    # 1. 计算合成因子得分
    combined_score = pd.DataFrame(0.0, index=closes.index, columns=closes.columns)

    for name, raw_score in factor_values.items():
        weight = factor_weights.get(name, 1.0)  # 默认权重 1.0

        # --- 特殊逻辑: castle_stg1 ---
        # 如果是 Mom_20 且开启了 castle_stg1，检测全市场最大动量
        if castle_stg1 and name == "Mom_20":
            row_max = raw_score.max(axis=1)
            # 如果某天的最大动量 <= -0.1，说明市场环境极差
            # 使用逻辑 OR 累积风险掩码 (虽然通常只有一个 Mom 因子，但为了稳健)
            risk_mask = risk_mask | (row_max <= -0.1)

        # 计算排名分 (Pct Rank)
        rank_score = raw_score.rank(axis=1, pct=True)

        # 累加加权得分
        combined_score += rank_score * weight

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
            # print(f"[Logic] Castle STG1 triggered on {risk_mask.sum()} days.")
            pass
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