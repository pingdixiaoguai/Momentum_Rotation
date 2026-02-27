"""
Walk-Forward Analysis (WFA) — 样本外测试工具

策略:  锚定式（Anchored）
       训练窗口从数据起点不断扩大，每年在全新的样本外数据上评估策略，
       将所有样本外收益拼接成最终的"真实"净值曲线。

用法:
    python wfa.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import quantstats as qs
from tabulate import tabulate

import config
from core.data import DataLoader
from core.engine import RealWorldEngine
from core.strategies import CustomStrategy
from factors import Momentum_castle, Peak
from logics import logic_factor_rotation
from utils import logger


# ─────────────────────────────────────────────────────────────────────────────
# 1. WFA 核心函数
# ─────────────────────────────────────────────────────────────────────────────

def run_walk_forward(
    data_dict: Dict[str, pd.DataFrame],
    strategy_factory: Callable[[], CustomStrategy],
    test_years: int = 1,
    warmup_bars: int = 60,
    test_start_year: Optional[int] = None,
) -> Tuple[pd.Series, pd.DataFrame]:
    """
    锚定式 Walk-Forward Analysis.

    每个测试窗口的数据划分：
      - 训练期  = [数据起点, 测试期第一天) —— 只用来"见证"数据，不参与收益
      - 评估数据 = 最后 warmup_bars 根训练数据 + 完整测试期
      - 只保留测试期的收益，warmup 部分仅用于因子预热

    Args:
        data_dict:        DataLoader 返回的完整宽表数据字典
        strategy_factory: 无参可调用，每次调用返回一个新的 CustomStrategy 实例
        test_years:       每个测试窗口时长（年），默认 1
        warmup_bars:      因子预热期 K 线数，需 >= 最大因子窗口（默认 60）
        test_start_year:  第一个测试期的起始年份
                          （默认：数据起始年 + 3，确保有足够训练数据）

    Returns:
        oos_returns: 样本外日收益率 Series（按时间顺序拼接）
        summary:     每个测试期的统计摘要 DataFrame
    """
    close     = data_dict['close']
    all_dates = close.index

    first_year = all_dates[0].year
    last_year  = all_dates[-1].year

    if test_start_year is None:
        test_start_year = first_year + 3

    engine   = RealWorldEngine()
    all_oos: List[pd.Series] = []
    rows:    List[dict]      = []

    test_year = test_start_year
    while test_year <= last_year:
        test_end_year = test_year + test_years - 1

        # 用布尔掩码定位训练期和测试期
        train_mask = all_dates.year < test_year
        test_mask  = (all_dates.year >= test_year) & (all_dates.year <= test_end_year)

        n_train = int(train_mask.sum())
        n_test  = int(test_mask.sum())

        if n_test == 0:
            test_year += test_years
            continue

        if n_train < warmup_bars:
            logger.warning(
                f"[WFA] Skip {test_year}: 训练数据不足 "
                f"({n_train} bars < warmup_bars={warmup_bars})"
            )
            test_year += test_years
            continue

        # 评估数据 = 最后 warmup_bars 根训练数据 + 完整测试期
        # 用整数切片，避免任何 deprecated pandas API
        warmup_start = n_train - warmup_bars
        eval_end     = n_train + n_test
        eval_data    = {k: v.iloc[warmup_start:eval_end] for k, v in data_dict.items()}
        test_dates   = all_dates[test_mask]

        label = str(test_year) if test_years == 1 else f"{test_year}~{test_end_year}"
        logger.info(
            f"[WFA] 测试期 {label}: "
            f"训练截至 {all_dates[n_train - 1].date()}, "
            f"测试 {n_test} 个交易日"
        )

        strategy = strategy_factory()
        try:
            rets     = engine.run(strategy, **eval_data)
            oos_rets = rets.loc[test_dates]
            all_oos.append(oos_rets)

            rows.append({
                'Period':    label,
                'Days':      n_test,
                'Total Ret': qs.stats.comp(oos_rets),
                'CAGR':      qs.stats.cagr(oos_rets),
                'Sharpe':    qs.stats.sharpe(oos_rets),
                'Max DD':    qs.stats.max_drawdown(oos_rets),
                'Win Rate':  (oos_rets > 0).mean(),
            })

        except Exception as e:
            logger.error(f"[WFA] 测试期 {label} 失败: {e}", exc_info=True)

        test_year += test_years

    if not all_oos:
        raise ValueError(
            "[WFA] 没有生成任何样本外结果，请检查 data_dict 的时间范围和 test_start_year。"
        )

    oos_returns = pd.concat(all_oos)
    summary     = pd.DataFrame(rows)
    return oos_returns, summary


# ─────────────────────────────────────────────────────────────────────────────
# 2. 结果展示
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(
    summary: pd.DataFrame,
    oos_rets: pd.Series,
    full_rets: pd.Series,
    strategy_name: str = "Strategy",
) -> None:
    """打印逐期摘要，并与全量回测对比"""
    disp = summary.copy()
    for col in ['Total Ret', 'CAGR', 'Max DD', 'Win Rate']:
        disp[col] = disp[col].map('{:.2%}'.format)
    disp['Sharpe'] = disp['Sharpe'].map('{:.2f}'.format)
    disp['Days']   = disp['Days'].map(str)

    print(f"\n{'='*68}")
    print(f"  Walk-Forward Analysis  ·  {strategy_name}")
    print(f"{'='*68}")
    print(tabulate(
        disp.values.tolist(),
        headers=disp.columns.tolist(),
        tablefmt='simple',
        stralign='right',
    ))

    # 汇总对比行
    full_oos = full_rets.reindex(oos_rets.index).fillna(0)
    print(f"\n{'─'*68}")
    for label, rets in [("OOS Total", oos_rets), ("Full BT (same period)", full_oos)]:
        print(
            f"  {label:<24}"
            f"  CAGR {qs.stats.cagr(rets):.2%}"
            f"  Sharpe {qs.stats.sharpe(rets):.2f}"
            f"  MaxDD {qs.stats.max_drawdown(rets):.2%}"
            f"  WinRate {(rets > 0).mean():.1%}"
        )
    print()


def plot_wfa_results(
    oos_rets: pd.Series,
    full_rets: pd.Series,
    benchmark_rets: pd.Series,
    strategy_name: str = "Strategy",
    output_path: str = "wfa_result.png",
) -> None:
    """绘制 WFA 样本外曲线 vs 全量回测 vs 基准的对比图"""
    idx     = oos_rets.index
    oos_eq  = (1 + oos_rets).cumprod()
    full_eq = (1 + full_rets.reindex(idx).fillna(0)).cumprod()
    bm_eq   = (1 + benchmark_rets.reindex(idx).fillna(0)).cumprod()

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(idx, oos_eq.values,  color='#e74c3c', linewidth=2.0,
            label='WFA Out-of-Sample')
    ax.plot(idx, full_eq.values, color='#3498db', linewidth=1.5,
            linestyle='--', alpha=0.8, label='Full Backtest (same period)')
    ax.plot(idx, bm_eq.values,   color='#95a5a6', linewidth=1.5,
            linestyle=':',  alpha=0.8, label='Benchmark (Equal Weight)')

    # 标记每个测试期的起点（除第一个外）
    years_seen = set()
    for dt in idx:
        yr = dt.year
        if yr not in years_seen:
            years_seen.add(yr)
            if len(years_seen) > 1:
                ax.axvline(x=dt, color='gray', linestyle=':', linewidth=0.8, alpha=0.4)
                ax.annotate(
                    str(yr),
                    xy=(dt, oos_eq.loc[dt]),
                    xytext=(4, 4), textcoords='offset points',
                    fontsize=7, color='gray',
                )

    ax.set_title(f'Walk-Forward Analysis — {strategy_name}', fontsize=14, pad=12)
    ax.set_ylabel('Cumulative Return (Base = 1)', fontsize=11)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.legend(fontsize=10)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    logger.info(f"[WFA] 图表已保存 → {output_path}")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# 3. 主程序
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # 1. 加载完整历史数据
    loader    = DataLoader("2013-08-01", datetime.now().strftime("%Y-%m-%d"), auto_sync=True)
    data_dict = loader.load(config.ETF_SYMBOLS)

    # 2. 基准（等权组合，Open-to-Open）
    benchmark_rets = data_dict['open'].pct_change().mean(axis=1).fillna(0)
    benchmark_rets.name = "Equal_Weighted_Benchmark"

    # 3. 被测策略（与 live.py 保持一致）
    # ── 如需测试其他策略，修改这里即可 ──────────────────────────────
    STRATEGY_NAME = "Momentum_Peak_Castle"

    def strategy_factory() -> CustomStrategy:
        return CustomStrategy(
            name=STRATEGY_NAME,
            factors={
                "Mom_20": Momentum_castle(25),
                "Peak_20": Peak(20),
            },
            logic_func=logic_factor_rotation,
            holding_period=1,
            factor_weights={"Mom_20": 1.0, "Peak_20": 1.0},
            top_k=1,
            timing_period=0,
            stg_flag=["castle_stg1"],
        )
    # ────────────────────────────────────────────────────────────────

    # 4. 运行 WFA
    # test_start_year=2016：确保第一个测试期之前有 ~2.5 年训练数据 (2013-08 ~ 2015-12)
    oos_rets, summary = run_walk_forward(
        data_dict        = data_dict,
        strategy_factory = strategy_factory,
        test_years       = 1,
        warmup_bars      = 60,
        test_start_year  = 2016,
    )
    oos_rets.index = pd.to_datetime(oos_rets.index)

    # 5. 全量回测（用于对比，范围与 OOS 相同）
    engine    = RealWorldEngine()
    full_rets = engine.run(strategy_factory(), **data_dict)
    full_rets.index = pd.to_datetime(full_rets.index)

    # 6. 打印摘要表格
    print_summary(summary, oos_rets, full_rets, STRATEGY_NAME)

    # 7. 绘制对比图
    plot_wfa_results(oos_rets, full_rets, benchmark_rets, STRATEGY_NAME)

    # 8. 生成 QuantStats HTML 报告
    common_idx = oos_rets.index.intersection(benchmark_rets.index)
    qs.reports.html(
        oos_rets.loc[common_idx],
        benchmark=benchmark_rets.loc[common_idx],
        output="report_wfa.html",
        title=f"WFA Out-of-Sample — {STRATEGY_NAME}",
    )
    logger.info("[WFA] HTML 报告已保存 → report_wfa.html")


if __name__ == "__main__":
    main()
