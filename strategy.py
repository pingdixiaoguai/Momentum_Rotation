from config import MOMENTUM_LONG_WINDOW, MOMENTUM_REVERSAL_WINDOW, TOTAL_WINDOW


def calculate_weighted_score(daily_returns_window):
    """自定义的滚动计算函数"""
    momentum_score = daily_returns_window.iloc[:MOMENTUM_LONG_WINDOW].sum()
    reversal_score = daily_returns_window.iloc[MOMENTUM_LONG_WINDOW:].sum()
    return momentum_score - reversal_score


def calculate_scores(daily_returns, etf_symbols):
    """
    计算策略所需的所有分数。
    返回: combined_scores (综合分), reversal_scores (反转分)
    """
    combined_scores = daily_returns[etf_symbols].rolling(
        window=TOTAL_WINDOW,
        min_periods=TOTAL_WINDOW
    ).apply(calculate_weighted_score, raw=False).dropna()

    reversal_scores = daily_returns[etf_symbols].rolling(
        window=MOMENTUM_REVERSAL_WINDOW
    ).sum().dropna()

    return combined_scores, reversal_scores


def get_dual_momentum_signal(latest_combined_scores, latest_reversal_scores):
    """
    根据最近一日的分数，生成双动量持仓和权重。
    返回: etf1, weight1, etf2, weight2
    """
    top_2_etfs = latest_combined_scores.nlargest(2)
    etf1, etf2 = top_2_etfs.index[0], top_2_etfs.index[1]

    reversal_score1 = latest_reversal_scores.at[etf1]
    reversal_score2 = latest_reversal_scores.at[etf2]

    strength1 = max(0, -reversal_score1)
    strength2 = max(0, -reversal_score2)
    total_strength = strength1 + strength2

    if total_strength > 0:
        weight1 = strength1 / total_strength
        weight2 = strength2 / total_strength
    else:
        weight1, weight2 = 0.5, 0.5

    return etf1, weight1, etf2, weight2