import pandas as pd
import numpy as np
from .base import Strategy, Factor
from typing import List, Tuple


class FactorRotationStrategy(Strategy):
    """
    通用因子轮动策略
    """

    def __init__(self,
                 factors: List[Tuple[Factor, float, str]],
                 top_k: int = 1,
                 timing_period: int = 0,
                 name: str = None,
                 stg_flag: List[str] = []):

        if name is None:
            name = f"Rotation_Top{top_k}"

        super().__init__(name)
        self.factors = factors
        self.top_k = top_k
        self.timing_period = timing_period
        self.stg_flag = stg_flag

    def generate_target_weights(self, **kwargs) -> pd.DataFrame:
        castle_stg1 = False
        if "castle_stg1" in self.stg_flag:
            castle_stg1 = True
            print("[strategies] castle_stg1 = True")

        castle_stg2 = False
        if "castle_stg2" in self.stg_flag:
            castle_stg2 = True
            print("[strategies] castle_stg2 = True")

        # 必须要有收盘价用于对齐索引
        if 'close' not in kwargs:
            raise ValueError("Strategy requires 'close' price data.")

        closes = kwargs['close']
        
        # 1. 计算合成因子得分
        combined_score = pd.DataFrame(0.0, index=closes.index, columns=closes.columns)

        for factor, weight, mom_name in self.factors:
            print(mom_name, weight)
            # !!! 关键点：直接把所有数据传给因子，因子自己挑 !!!
            raw_score = factor.calculate(**kwargs)
            print("raw_score of :" + mom_name, raw_score['2024-09-20':'2024-10-15'])

            if castle_stg1 and mom_name == "Mom_20":
                # 创建布尔掩码：哪些行的最大值小于0
                row_max = raw_score.max(axis=1)
                mask = row_max <= -0.1
                # print(mask)
                print("[strategies] len(mask):", mask.sum(), "len(raw_score):", len(raw_score))

                # 截面标准化 (Rank化)
                rank_score = raw_score.rank(axis=1, pct=True)
                # rank_score.loc[mask] = 0
            else:
            #     # 截面标准化 (Rank化)
            #     rank_score = raw_score.rank(axis=1, pct=True)
                rank_score = raw_score
            print("rank_score of :" + mom_name, rank_score['2024-09-20':'2024-10-15'])

            # if castle_stg2:
            #     combined_score += rank_score * weight * 0.5
            # else:
            combined_score += rank_score * weight

            print("combined_score: after " + mom_name, combined_score['2024-09-20':'2024-10-15'])

        combined_score = combined_score.dropna(how='all')

        # 2. 生成持仓信号 (Top K)
        daily_rank = combined_score.rank(axis=1, ascending=False, method='min')
        # print("daily_rank:", "\n", daily_rank['2022-01-01':'2022-03-01'])

        if castle_stg1:
            # 初始权重
            # row_max = daily_rank.max(axis=1)
            # mask = row_max == 1.0
            # print("[strategies] len(mask):", mask.sum(), "len(daily_rank):", len(daily_rank), "-->", round(mask.sum()/len(daily_rank)*100,2), "%")
            target_weights = (daily_rank <= self.top_k).astype(float)
            target_weights.loc[mask] = 0
            # print("[strategies] len(mask):", mask.sum())
        else:
            target_weights = (daily_rank <= self.top_k).astype(float)


        # 归一化(当持仓权重和不为1时有用)
        target_weights = target_weights.div(target_weights.sum(axis=1).replace(0, 1), axis=0)
        

        # 3. (可选) 绝对动量择时
        if self.timing_period > 0:
            ma = closes.rolling(window=self.timing_period).mean()
            # 只有价格 > 均线 才持有
            trend_filter = (closes > ma).astype(int)
            target_weights = target_weights * trend_filter

        print("target_weights:", "\n", target_weights['2024-09-20':'2024-10-15'])

        return target_weights