import pandas as pd
import numpy as np


def risk_managed_momentum_strategy(closes: pd.DataFrame,
                                             momentum_window: int = 20,
                                             reversal_window: int = 5) -> pd.Series:
    """
    优化后的动量轮动策略。

    逻辑：
    1. 长期动量：寻找过去N天涨幅最好的。
    2. 短期反转（惩罚）：惩罚近期涨幅过大（可能透支）的标的。
    3. 合成得分：Rank(动量) - Rank(短期反转)。
    4. 择时：只有当选中标的的动量为正时才持有。
    """
    print("应用策略: 动量轮动 (Rank加权优化版)")

    # 1. 计算动量 (Momentum)
    # 使用 pct_change 计算 N 日动量
    mom_raw = closes.pct_change(periods=momentum_window)

    # 2. 计算反转/短期过热因子 (Reversal/Overheat)
    # 这里我们定义反转为“最近一小段时间的涨幅”，通常动量策略希望避开短期涨太猛的
    # 使用较短的窗口，例如 5日 或 10日，或者沿用原代码逻辑(Log return rolling mean)
    log_ret = np.log(closes / closes.shift(1))
    rev_raw = log_ret.rolling(window=momentum_window).mean()

    # --- 核心优化：截面标准化 (Cross-sectional Normalization) ---
    # 我们不使用硬阈值过滤异常值，而是使用 Ranking (排名) 或 Z-Score。
    # 这样可以保证每天都在横向对比不同ETF的相对强弱，而不是和历史对比。

    # axis=1 表示在每天的截面上，对所有ETF进行排名 (0到1之间)
    mom_rank = mom_raw.rank(axis=1, pct=True)
    rev_rank = rev_raw.rank(axis=1, pct=True)

    # 3. 合成因子得分
    # 逻辑：我们要 动量排名高 (High Mom) 且 短期没涨过头 (Low Rev) 的
    # 权重可以调整，这里给予动量更高权重，反转作为修正
    # 原代码权重: Mom=1, Rev=5。这里因为用了Rank，量纲一致，我们调整为 1:1 或 1:0.5 试试
    combined_score = 1.0 * mom_rank - 0.5 * rev_rank

    # --- 修复警告的关键步骤 ---
    # 去除由于 Rolling Window 导致的初始空值行
    # how='all' 表示只有当这一行的所有ETF都是NaN时才删除
    combined_score = combined_score.dropna(how='all')

    # 4. 生成持仓信号
    best_asset = combined_score.idxmax(axis=1)

    # 5. 现金过滤器 (择时)
    # 规则：虽然它是第一名，但如果它本身的绝对动量是负的（处于下跌趋势），则空仓。
    # 这里我们不用 Rank，必须用原始动量值来判断是否大于0

    # 创建一个空的 Series 存储结果
    holdings = pd.Series(index=closes.index, data='cash')

    # 向量化生成信号 (比 for 循环快得多)
    # 方法：使用 lookup 或者 apply (apply略慢但逻辑清晰，这里用索引匹配法)

    # 获取每一天 best_asset 对应的 原始动量值
    # 这是一个稍微复杂的向量化操作，为了清晰，我们使用一个掩码

    for date in combined_score.index:
        try:
            target = best_asset.loc[date]
            if pd.isna(target):
                continue

            # 检查该标的当天的原始动量是否 > 0
            if mom_raw.at[date, target] > 0:
                holdings.loc[date] = target
            else:
                holdings.loc[date] = 'cash'
        except KeyError:
            continue

    return holdings
