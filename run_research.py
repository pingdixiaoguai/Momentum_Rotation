from data import ParquetDataProvider
from strategies import PureMomentumStrategy, RiskManagedMomentumStrategy
from engine import BacktestEngine, ReportGenerator
import config
import pandas as pd
import quantstats as qs  # 引入 quantstats 库用于计算指标


def run_comparison_test():
    """
    批量回测脚本：基于 Parquet 数据系统
    """
    # ---------------------------------------------------------
    # 1. 准备数据 (使用新的 ParquetDataProvider)
    # ---------------------------------------------------------
    # 定义我们要回测的资产池
    symbols = config.ETF_SYMBOLS

    # 实例化数据提供者
    # auto_sync=True 会在回测开始前尝试调用 akshare 更新数据
    # 如果你觉得慢，可以设为 False，只用本地现有数据
    data_provider = ParquetDataProvider(
        start_date="2020-01-01",
        end_date="2024-12-30",
        auto_sync=False
    )

    # 加载数据
    closes, opens, volumes = data_provider.load_data(symbols)

    # ---------------------------------------------------------
    # 2. 定义回测引擎
    # ---------------------------------------------------------
    engine = BacktestEngine(
        start_date="2021-01-01",
        end_date="2024-12-30",
        benchmark="510300"
    )

    # ---------------------------------------------------------
    # 3. 定义策略池
    # ---------------------------------------------------------
    test_strategies = [
        # 对照组：简单的动量策略
        PureMomentumStrategy(window=20),

        # 实验组：不同参数的风险管理动量策略
        RiskManagedMomentumStrategy(momentum_window=20, reversal_window=5),
        RiskManagedMomentumStrategy(momentum_window=25, reversal_window=10),
    ]

    results = []

    # ---------------------------------------------------------
    # 4. 执行回测
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"开始批量回测 | 资产数: {len(symbols)} | 策略数: {len(test_strategies)}")
    print("=" * 80)

    for strat in test_strategies:
        # 动态生成唯一的策略名称后缀，方便在图表中区分
        suffix = ""
        if hasattr(strat, 'window'):
            suffix = f"_w{strat.window}"
        elif hasattr(strat, 'momentum_window'):
            suffix = f"_m{strat.momentum_window}_r{strat.reversal_window}"

        original_name = strat.name
        strat.__class__.__name__ = f"{original_name}{suffix}"  # 临时修改类名用于报告

        # 运行回测
        result = engine.run(strat, closes, opens)
        results.append(result)

        # 恢复类名
        strat.__class__.__name__ = original_name

        # ---------------------------------------------------------
        # 使用 quantstats 计算专业指标
        # ---------------------------------------------------------
        # Quantstats 提供了非常丰富的统计函数，无需手动计算
        cagr = qs.stats.cagr(result.returns)
        sharpe = qs.stats.sharpe(result.returns)
        max_dd = qs.stats.max_drawdown(result.returns)
        volatility = qs.stats.volatility(result.returns)

        print(
            f"策略: {result.strategy_name:<35} | 年化收益(CAGR): {cagr * 100:6.2f}% | 最大回撤: {max_dd * 100:6.2f}% | 夏普: {sharpe:.2f} | 波动率: {volatility * 100:.2f}%")

    # ---------------------------------------------------------
    # 5. 可视化分析
    # ---------------------------------------------------------
    print("\n[Analysis] Generating comparison chart...")
    import matplotlib.pyplot as plt
    import matplotlib
    # 尝试设置中文字体，避免乱码 (根据系统情况调整)
    matplotlib.rcParams['axes.unicode_minus'] = False
    try:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
    except:
        pass

    plt.figure(figsize=(14, 7))

    # 绘制各策略曲线
    for res in results:
        cum_ret = (1 + res.returns).cumprod()
        plt.plot(cum_ret.index, cum_ret.values, label=f"{res.strategy_name} ({cum_ret.iloc[-1]:.2f})")

    # 绘制基准曲线
    if results:
        bench_cum = (1 + results[0].benchmark_returns).cumprod()
        plt.plot(bench_cum.index, bench_cum.values, 'k--', linewidth=2, label='Benchmark (510300)', alpha=0.6)

    plt.title("Momentum Strategy Comparison (Parquet Data Source)")
    plt.ylabel("Normalized Value")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("strategy_comparison.png", dpi=300)
    print("[Analysis] Chart saved to 'strategy_comparison.png'")

    # 为最佳策略生成 HTML 报告
    if results:
        # 使用累计收益最高的作为最佳策略
        best_result = max(results, key=lambda x: (1 + x.returns).cumprod().iloc[-1])
        ReportGenerator.show_html(best_result)


if __name__ == "__main__":
    run_comparison_test()