from datetime import datetime

import pandas as pd
import quantstats as qs

import config
from core.data import DataLoader
from core.strategies import CustomStrategy
# 导入需要的因子
from factors import Momentum, MainLineBias, Peak
# 导入抽离出来的策略逻辑
from logics import logic_bias_protection, logic_factor_rotation
from utils import logger


# ==========================================
# 1. 回测引擎
# ==========================================

class SimpleEngine:
    def run(self, strategy, **data_dict):
        logger.info(f"Running strategy: {strategy.name}...")

        if 'close' not in data_dict: raise ValueError("Engine needs 'close' price.")
        opens = data_dict['close']

        # 获取目标权重
        target_weights = strategy.generate_target_weights(**data_dict)

        # Shift 1: 今天的信号 -> 明天的持仓
        holdings = target_weights.shift(1).fillna(0)

        # 计算净值
        asset_rets = opens.pct_change().fillna(0)
        strategy_rets = (holdings * asset_rets).sum(axis=1)

        # 扣费
        cost = config.TRANSACTION_COST if hasattr(config, 'TRANSACTION_COST') else 0.0005
        turnover = (holdings - holdings.shift(1).fillna(0)).abs().sum(axis=1)
        strategy_rets = strategy_rets - (turnover * cost)

        return strategy_rets


# ==========================================
# 2. 主程序
# ==========================================

def main():
    # 1. 加载数据
    loader = DataLoader("2013-08-01", datetime.now().strftime("%Y-%m-%d"), auto_sync=True)
    symbols = config.ETF_SYMBOLS
    data_dict = loader.load(symbols)

    # 准备基准
    logger.info("Using average return of all assets as benchmark.")
    benchmark_rets = data_dict['close'].pct_change().mean(axis=1).fillna(0)
    benchmark_rets.name = "Equal_Weighted_Benchmark"

    # 2. 组装策略
    strategies = [
        # --- 策略 A: 灵活的加权轮动 (动量 + 波动率) ---
        CustomStrategy(
            factors={
                'mom': Momentum(20),      # 20日动量
                'bias': MainLineBias(20)  # 20日乖离率
            },
            logic_func=logic_bias_protection, # 从 logics 模块导入
            name="Func_Bias"
        ),

        # --- 策略 B: 灵活的乖离率风控 ---
        CustomStrategy(
            factors={
                'mom': Momentum(20),      # 20日动量
                'bias': MainLineBias(20)  # 20日乖离率
            },
            logic_func=logic_bias_protection,   # 从 logics 模块导入
            name="Func_Bias_Filter",
            holding_period=5
        ),

        CustomStrategy(
            name="Momentum_Peak_Castle",
            # 因子定义
            factors={
                "Mom_20": Momentum(20),
                "Peak_20": Peak(20)
            },
            # 逻辑函数
            logic_func=logic_factor_rotation,
            # 这里的参数会被透传给 logic_factor_rotation
            factor_weights={"Mom_20": 1.0, "Peak_20": 1.0},
            top_k=1,
            timing_period=0,
            stg_flag=["castle_stg1"]  # 开启风控
        )
    ]

    # 3. 执行回测
    engine = SimpleEngine()

    for strat in strategies:
        try:
            rets = engine.run(strat, **data_dict)
            rets.index = pd.to_datetime(rets.index)

            # 生成报告
            report_filename = f"report_{strat.name}.html"
            logger.info(f"Generating full HTML report for {strat.name}...")
            common_idx = rets.index.intersection(benchmark_rets.index)

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