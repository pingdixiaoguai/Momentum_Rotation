from datetime import datetime

import pandas as pd
import quantstats as qs

import config
from core.data import DataLoader
from core.engine import RealWorldEngine
from core.strategies import CustomStrategy
# 导入需要的因子
from factors import Momentum, Momentum_castle, MainLineBias, Peak
# 导入抽离出来的策略逻辑
from logics import logic_bias_protection, logic_factor_rotation
from utils import logger


# ==========================================
# 主程序
# ==========================================

def main():
    # 1. 加载数据
    loader = DataLoader("2013-08-01", datetime.now().strftime("%Y-%m-%d"), auto_sync=True)
    symbols = config.ETF_SYMBOLS
    data_dict = loader.load(symbols)

    # 准备基准 (修正为 Open-to-Open 以保持公平对比)
    logger.info("Using average return of all assets as benchmark (Open-to-Open).")
    benchmark_rets = data_dict['open'].pct_change().mean(axis=1).fillna(0)
    benchmark_rets.name = "Equal_Weighted_Benchmark"

    # 2. 组装策略
    strategies = [
        CustomStrategy(
            factors={
                'mom': Momentum(20),      # 20日动量
                'bias': MainLineBias(20)  # 20日乖离率
            },
            logic_func=logic_bias_protection,   # 从 logics 模块导入
            name="Func_Bias_Filter",
            holding_period=1
        ),
        CustomStrategy(
            name="Momentum_Peak_Castle",
            # 因子定义
            factors={
                "Mom_20": Momentum_castle(25),
                "Peak_20": Peak(20)
            },
            # 逻辑函数
            logic_func=logic_factor_rotation,
            holding_period=1,
            # 这里的参数会被透传给 logic_factor_rotation
            factor_weights={"Mom_20": 1.0, "Peak_20": 1.0},
            top_k=1,
            timing_period=0,
            stg_flag=["castle_stg1"]  # 开启风控
        )
    ]

    # 3. 执行回测
    engine = RealWorldEngine()

    for strat in strategies:
        try:
            rets = engine.run(strat, **data_dict)
            rets.index = pd.to_datetime(rets.index)

            # 生成报告
            report_filename = f"report_{strat.name}.html"
            logger.info(f"Generating full HTML report for {strat.name}...")
            common_idx = rets.index.intersection(benchmark_rets.index)

            # 简单的对齐检查
            if rets[common_idx].sum() == 0:
                logger.warning(f"Strategy {strat.name} has 0 returns. Please check if data is sufficient for shift(2).")

            qs.reports.html(
                rets.loc[common_idx],
                benchmark=benchmark_rets.loc[common_idx],
                output=report_filename,
                title=f"{strat.name} Performance Report"
            )
            logger.info(f"Report successfully saved to: {report_filename}")

        except Exception as e:
            logger.error(f"Strategy {strat.name} failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()