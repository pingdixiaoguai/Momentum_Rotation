from datetime import datetime

import pandas as pd
import quantstats as qs

import config
from core.data import DataLoader
from core.strategies import CustomStrategy
# 导入需要的因子
from factors import Momentum, Momentum_castle, MainLineBias, Peak
# 导入抽离出来的策略逻辑
from logics import logic_bias_protection, logic_factor_rotation
from utils import logger


# ==========================================
# 1. 回测引擎 (已修正未来函数)
# ==========================================

class RealWorldEngine:
    def run(self, strategy, **data_dict):
        logger.info(f"Running strategy: {strategy.name} (RealWorld Mode)...")

        if 'open' not in data_dict or 'close' not in data_dict:
            raise ValueError("RealWorldEngine needs both 'open' and 'close' prices.")

        opens = data_dict['open']
        closes = data_dict['close']

        # 1. 获取信号 (Signal T)
        # 信号是在 T日 收盘产生的
        weights = strategy.generate_target_weights(**data_dict)

        # 2. 计算持仓 (Position T+1)
        # T日收盘的信号，决定了 T+1日 全天的持仓
        # 我们将在 T+1日 开盘执行交易
        positions = weights.shift(1).fillna(0)

        # 3. 计算前一日持仓 (Position T)
        # 用来判断今天是买入、卖出还是继续持有
        prev_positions = positions.shift(1).fillna(0)

        # ==================================
        # 核心收益计算逻辑 (向量化处理)
        # ==================================

        # A. 基础收益 (Base Return): 假设一直持有 (Close - PrevClose) / PrevClose
        # 这是最普通的涨跌幅
        base_daily_rets = closes.pct_change().fillna(0)

        # B. 买入日修正 (Buy Day Correction):
        # 我们是在 T+1 Open 买入的，所以 T+1 当天我们只能获得 (Close - Open) / Open
        # 而 base_daily_rets 算的是 (Close - PrevClose) / PrevClose
        # 所以我们需要把“隔夜跳空”那一段收益减掉（或者替换掉）

        # 计算“日内收益” (Open -> Close)
        intraday_rets = (closes - opens) / opens

        # 计算“隔夜收益” (PrevClose -> Open)
        # overnight_rets = (opens - closes.shift(1)) / closes.shift(1)

        # C. 卖出日修正 (Sell Day Correction):
        # 我们在 T+1 Open 卖出了，所以当天我们只能获得 (Open - PrevClose) / PrevClose
        # 即“隔夜收益”
        overnight_rets = (opens / closes.shift(1) - 1).fillna(0)

        # --- 组合最终收益 ---
        strategy_rets = pd.Series(0.0, index=closes.index)

        # 这里的逻辑稍微复杂，为了性能我们分情况处理：

        # 情况1: 今日持仓，昨日也持仓 (Holding) -> 吃满全天 (base_daily_rets)
        mask_hold = (positions == 1) & (prev_positions == 1)

        # 情况2: 今日持仓，昨日空仓 (New Buy) -> 只吃日内 (intraday_rets)
        mask_buy = (positions == 1) & (prev_positions == 0)

        # 情况3: 今日空仓，昨日持仓 (Sell) -> 只吃隔夜 (overnight_rets)
        mask_sell = (positions == 0) & (prev_positions == 1)

        # 简单加权 (暂只支持单标的轮动，即 0 或 1)
        # 如果是多标的组合，需要对每一列分别计算再求和

        # 逐列计算 (针对多资产)
        total_ret = pd.DataFrame(0.0, index=closes.index, columns=closes.columns)

        total_ret[mask_hold] = base_daily_rets[mask_hold]
        total_ret[mask_buy] = intraday_rets[mask_buy]
        total_ret[mask_sell] = overnight_rets[mask_sell]

        # 汇总所有资产的收益
        strategy_rets = total_ret.sum(axis=1)

        # 扣费 (仅在交易日扣费)
        # 交易发生当且仅当持仓发生变化 (Buy or Sell)
        cost = config.TRANSACTION_COST if hasattr(config, 'TRANSACTION_COST') else 0.0005
        turnover = (positions - prev_positions).abs()
        total_cost = (turnover * cost).sum(axis=1)

        strategy_rets = strategy_rets - total_cost

        return strategy_rets


# ==========================================
# 2. 主程序
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
        # --- 策略 : 灵活的乖离率风控 ---
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