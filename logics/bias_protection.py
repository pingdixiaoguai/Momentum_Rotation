import pandas as pd
from typing import Dict


def logic_bias_protection(factors: Dict[str, pd.DataFrame], closes: pd.DataFrame) -> pd.DataFrame:
    """
    【逻辑函数 B】: 乖离率风控

    规则:
    1. 必须是动量最强 (Top 1) 的品种。
    2. 该品种的乖离率不能处于破位区 (Bias >= -5%)。
    3. 如果是 Top 1 但破位了，则空仓。
    """
    mom = factors['mom']
    bias = factors['bias']

    # 1. 进攻逻辑: 动量第一
    rank = mom.rank(axis=1, ascending=False)
    is_top1 = (rank == 1)

    # 2. 风控逻辑: 乖离率必须大于 -5% (-0.05)
    is_safe = (bias >= -0.05)

    # 3. 最终信号: 既要是Top1，又要是安全的
    # Python 的 & 运算符对应 Pandas 的 "element-wise AND"
    final_signal = is_top1 & is_safe

    # 4. 转换为权重
    weights = final_signal.astype(float)
    # 如果某天 Top1 的标的没有通过 safe 检查，final_signal 全为 False，
    # sum 为 0，权重结果也就为 0 (自动空仓)
    weights = weights.div(weights.sum(axis=1).replace(0, 1), axis=0)

    return weights