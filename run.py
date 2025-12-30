import pandas as pd
import quantstats as qs
import matplotlib.pyplot as plt
import config
from core.data import DataLoader
from core.strategies import FactorRotationStrategy
from factors.library import Momentum, Volatility, MeanReversion, IntradayVolatility


# --- 极简向量化回测引擎 ---
class SimpleEngine:
    def run(self, strategy, **data_dict):
        """
        :param strategy: 策略实例
        :param data_dict: 包含所有数据的字典 (close, open, high, low...)
        """
        print(f"Running strategy: {strategy.name}...")

        # 1. 自动提取计算收益所需的基础数据
        if 'close' not in data_dict: raise ValueError("Engine needs 'close' price.")
        # 如果没有 open，就用 close 近似
        opens = data_dict.get('open', data_dict['close'])

        # 2. 获取目标权重
        # !!! 关键：把整个数据字典传给策略，策略再传给因子 !!!
        target_weights = strategy.generate_target_weights(**data_dict)

        # Shift 1: 今天的信号指导明天
        holdings = target_weights.shift(1).fillna(0)

        # 3. 计算收益
        asset_rets = opens.pct_change().fillna(0)
        strategy_rets = (holdings * asset_rets).sum(axis=1)

        # 简单扣费 (万5)
        cost = 0.0005
        turnover = (holdings - holdings.shift(1).fillna(0)).abs().sum(axis=1)
        strategy_rets = strategy_rets - (turnover * cost)

        return strategy_rets


# --- 主程序 ---
def main():
    # 1. 准备数据 (现在返回的是一个字典)
    loader = DataLoader("2020-01-01", "2024-12-30", auto_sync=False)
    # data_dict keys: 'close', 'open', 'volume', 'high', 'low', ...
    data_dict = loader.load(config.ETF_SYMBOLS)

    # 2. 定义策略
    strategies = [
        # 策略A: 经典动量
        FactorRotationStrategy(
            factors=[(Momentum(20), 1.0)],
            top_k=1
        ),
        # 策略B: 引入日内波动 (自动用到 high/low 数据)
        # 假设逻辑：喜欢波动率小的
        FactorRotationStrategy(
            factors=[
                (Momentum(20), 1.0),
                (IntradayVolatility(14), -0.5)
            ],
            top_k=1
        )
    ]

    # 3. 运行
    engine = SimpleEngine()
    plt.figure(figsize=(12, 6))

    for strat in strategies:
        # !!! 关键：使用 ** 解包字典 !!!
        rets = engine.run(strat, **data_dict)

        sharpe = qs.stats.sharpe(rets)
        (1 + rets).cumprod().plot(label=f"{strat.name} (Sharpe={sharpe:.2f})")

    plt.legend()
    plt.title("Flexible Factor Architecture Test")
    plt.grid(True, alpha=0.3)
    plt.savefig("backtest_result.png")
    print("Done.")


if __name__ == "__main__":
    main()