import pandas as pd
import quantstats as qs
import matplotlib.pyplot as plt
import config
from core.data import DataLoader
from core.strategies import FactorRotationStrategy
from utils import logger  # 导入 logger

# --- 模块化导入因子 ---
# 得益于 factors/__init__.py，我们可以直接从 factors 包导入
from factors import Momentum, Volatility, IntradayVolatility, MeanReversion


class SimpleEngine:
    def run(self, strategy, **data_dict):
        logger.info(f"Running strategy: {strategy.name}...")

        # 1. 准备基础数据
        if 'close' not in data_dict: raise ValueError("Engine needs 'close' price.")
        opens = data_dict.get('open', data_dict['close'])

        # 2. 获取目标权重 (核心逻辑)
        # 策略内部会调用各个因子的 calculate(**data_dict)
        target_weights = strategy.generate_target_weights(**data_dict)

        # Shift 1: 今天的信号 -> 明天的持仓
        holdings = target_weights.shift(1).fillna(0)

        # 3. 计算净值
        asset_rets = opens.pct_change().fillna(0)
        strategy_rets = (holdings * asset_rets).sum(axis=1)

        # 4. 扣费
        cost = config.TRANSACTION_COST if hasattr(config, 'TRANSACTION_COST') else 0.0005
        turnover = (holdings - holdings.shift(1).fillna(0)).abs().sum(axis=1)
        strategy_rets = strategy_rets - (turnover * cost)

        return strategy_rets


def main():
    # 1. 加载数据
    loader = DataLoader("2013-01-01", "2025-12-30", auto_sync=True)
    # data_dict 包含 'close', 'open', 'high', 'low' 等所有可用字段
    data_dict = loader.load(config.ETF_SYMBOLS)

    # 2. 组装策略
    strategies = [
        # 策略A: 纯动量
        FactorRotationStrategy(
            factors=[(Momentum(20), 1.0)],
            top_k=1,
            timing_period=0
        ),

        # 策略B: 动量 + 低波动 (混合因子)
        FactorRotationStrategy(
            factors=[
                (Momentum(20), 1.0),  # 追涨
                (IntradayVolatility(10), -0.5),  # 杀跌 (避开波动剧烈的)
                (MeanReversion(5), -0.3)  # 避开短期涨过头的
            ],
            top_k=1,
            timing_period=60  # 均线择时
        )
    ]

    # 3. 执行回测
    engine = SimpleEngine()
    plt.figure(figsize=(12, 6))

    for strat in strategies:
        try:
            rets = engine.run(strat, **data_dict)
            sharpe = qs.stats.sharpe(rets)
            (1 + rets).cumprod().plot(label=f"{strat.name} (Sharpe={sharpe:.2f})")
        except Exception as e:
            logger.error(f"Strategy {strat.name} failed: {e}")

    plt.title("Factor Rotation: Modular Architecture Test")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("backtest_result.png")
    logger.info("Backtest finished. Check backtest_result.png")


if __name__ == "__main__":
    main()