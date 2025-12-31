import pandas as pd
import quantstats as qs
import matplotlib.pyplot as plt
import config
from core.data import DataLoader
from core.strategies import FactorRotationStrategy
from utils import logger  # 导入 logger

# --- 模块化导入因子 ---
from factors import Momentum, Volatility, IntradayVolatility, MeanReversion


class SimpleEngine:
    def run(self, strategy, **data_dict):
        logger.info(f"Running strategy: {strategy.name}...")

        # 1. 准备基础数据
        if 'close' not in data_dict: raise ValueError("Engine needs 'close' price.")
        opens = data_dict['close']

        # 2. 获取目标权重 (核心逻辑)
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
    # 注意：这里会根据 auto_sync=True 自动拉取数据
    loader = DataLoader("2013-01-01", "2025-12-30", auto_sync=False)

    # 你的ETF池子
    symbols = config.ETF_SYMBOLS

    data_dict = loader.load(symbols)

    # --- 准备基准收益 (用于报告对比) ---
    # 修改：直接使用当前资产池所有标的的平均收益作为基准 (等权基准)
    logger.info("Using average return of all assets as benchmark.")
    # axis=1 表示按行求平均，即每一天所有资产收益率的平均值
    benchmark_rets = data_dict['close'].pct_change().mean(axis=1).fillna(0)
    # 显式给 Series 命名，防止 quantstats 内部获取 name 时出错
    benchmark_rets.name = "Equal_Weighted_Benchmark"

    # 2. 组装策略 (批量回测配置)
    # 这里定义了一个列表，包含多个不同配置的策略实例。
    # 程序会依次运行它们，这样您可以方便地对比不同参数或因子组合的效果。
    strategies = [
        # 第 1 个策略：仅使用 20 日动量
        FactorRotationStrategy(
            factors=[(Momentum(20), 1.0)],
            top_k=1,
            timing_period=0
        )
    ]

    # 3. 执行回测并生成报告
    engine = SimpleEngine()

    for strat in strategies:
        try:
            rets = engine.run(strat, **data_dict)
            rets.index = pd.to_datetime(rets.index)  # 确保索引是 datetime 类型

            # --- 生成 HTML 报告的核心代码 ---
            report_filename = f"report_{strat.name}.html"
            logger.info(f"Generating full HTML report for {strat.name}...")

            # 必须对齐时间索引，否则 quantstats 可能会报错
            common_idx = rets.index.intersection(benchmark_rets.index)

            qs.reports.html(
                rets.loc[common_idx],
                benchmark=benchmark_rets.loc[common_idx],
                output=report_filename,
                title=f"{strat.name} Performance Report"
            )
            logger.info(f"Report successfully saved to: {report_filename}")
            # --------------------------------

        except Exception as e:
            logger.error(f"Strategy {strat.name} failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()