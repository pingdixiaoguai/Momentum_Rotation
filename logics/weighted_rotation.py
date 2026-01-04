import pandas as pd
from typing import Dict


def logic_weighted_rotation(factors: Dict[str, pd.DataFrame], closes: pd.DataFrame) -> pd.DataFrame:
    """
    【逻辑函数 A】: 通用加权轮动
    演示：结合 '动量' (进攻) 和 '波动率' (防守)

    规则:
    1. 动量越高越好 (权重 +1.0)
    2. 波动越低越好 (权重 -0.5)
    3. 合成得分选 Top 1
    """
    # 1. 从字典中提取因子数据
    mom = factors['mom']
    vol = factors['vol']

    # 2. 因子标准化 (Rank化: 0.0 ~ 1.0)
    # pct=True 将数值转换为百分比排名，方便不同量纲因子合成
    mom_rank = mom.rank(axis=1, pct=True)
    vol_rank = vol.rank(axis=1, pct=True)

    # 3. 加权合成
    # 动量是正向因子，波动率是负向因子(越小越好，所以给负权重)
    combined_score = (mom_rank * 1.0) + (vol_rank * -0.5)

    # 4. 选股 (Top 1)
    # 再次排名，ascending=False 表示分数最高的排第1
    final_rank = combined_score.rank(axis=1, ascending=False)

    # 生成 bool 信号
    signal = (final_rank <= 1)

    # 5. 转换为权重
    weights = signal.astype(float)
    # 归一化 (确保每天总仓位为 1.0)
    weights = weights.div(weights.sum(axis=1).replace(0, 1), axis=0)

    return weights