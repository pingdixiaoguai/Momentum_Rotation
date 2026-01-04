import pandas as pd
import numpy as np
from core.base import Factor

class Momentum(Factor):
    """
    经典动量因子 (Momentum)
    计算公式: (Close_t / Close_{t-N}) - 1
    """
    def __init__(self, window: int = 20):
        # 这里的 name 会在回测报告中显示
        super().__init__(f"Mom_{window}d")
        self.window = window

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        :param close: 收盘价宽表 (Index=Date, Columns=Assets)
        """
        # 逻辑：过去 N 天的收益率
        # print(type(close), '\n', close.head())
        # print(close[1000:1200])

        # 应用滚动归一化
        # close = close.apply(self.rolling_zscore)
        # close = close.apply(lambda col: self.rolling_rank(col, window=120))

        # print(close['2022-01-01':'2022-03-01'])
        # print("统计描述:", close.describe())

        # 警惕冲高回落的动量
        res = close.pct_change(self.window)
        # res = res[:30]
        print(res.head(30))

        over_peak = pd.DataFrame(index=res.index, columns=res.columns)

        # 对每个code列应用rolling窗口计算
        for code in res.columns:
            # 使用rolling窗口，窗口大小为20（包含当前行）
            # 然后对每个窗口应用自定义函数
            rolled_values = res[code].rolling(window=20, min_periods=20).apply(self.cal_over_peak, raw=False)
            over_peak[code] = rolled_values

        print(over_peak.head(50))

        return res
    
    def cal_over_peak(self, series):
        if len(series) < 2:
            print(len(series))
            return np.nan  # 数据不足20行时返回NaN
        return 1

    def rolling_zscore(self, series, window=120):
        # 计算滚动均值和标准差
        rolling_mean = series.rolling(window=window, min_periods=1).mean()
        rolling_std = series.rolling(window=window, min_periods=1).std()
        
        # 计算z-score
        zscore = (series - rolling_mean) / rolling_std
        
        # 处理标准差为0的情况
        zscore = zscore.replace([np.inf, -np.inf], 0).fillna(0)
        
        return zscore

    def rolling_rank(self, series, window=120):
        # 创建结果序列
        result = pd.Series(index=series.index, dtype=float)
        
        # 对每个位置计算排名
        for i in range(len(series)):
            # 确定窗口
            window_start = max(0, i - window + 1)
            window_data = series.iloc[window_start:i+1]
            
            # 计算排名
            ranks = window_data.rank(method='average')
            
            # 存储当前值的排名
            result.iloc[i] = ranks.iloc[-1]
        
        return result






import config
from core.data import DataLoader
if __name__ == "__main__":
    loader = DataLoader("2013-08-01", "2025-12-31", auto_sync=False)
    data_dict = loader.load(config.ETF_SYMBOLS)
    closes = data_dict['close']
    Momentum(20).calculate(closes)