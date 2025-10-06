# main.py

from datetime import datetime, timedelta
import config
from data_loader import get_etf_data
from strategy import calculate_scores, get_dual_momentum_signal
from notifier import send_to_dingtalk
from backtester import run_strategy_comparison


def generate_and_send_live_signal():
    """
    为下一个交易日生成信号并发送钉钉通知。
    """
    print("\n开始为下一个交易日生成信号...")
    # 1. 强制刷新获取最新数据
    closes, opens = get_etf_data(config.ETF_SYMBOLS_UPDATED, config.CACHE_FILE, force_refresh=True)
    if closes is None:
        print("获取最新数据失败，无法生成信号。")
        return

    # 2. 计算最新的分数
    daily_returns = closes.pct_change().dropna()
    combined_scores, reversal_scores = calculate_scores(daily_returns, config.ETF_SYMBOLS_UPDATED)

    if combined_scores.empty:
        print("数据不足，无法计算有效分数。")
        return

    latest_signal_date = combined_scores.index[-1]
    print(f"信号基于日期: {latest_signal_date.strftime('%Y-%m-%d')}")

    # 3. 获取最新信号
    latest_combined = combined_scores.loc[latest_signal_date]
    latest_reversal = reversal_scores.loc[latest_signal_date]
    etf1, weight1, etf2, weight2 = get_dual_momentum_signal(latest_combined, latest_reversal)

    # 4. 格式化并发送消息
    signal_for_date = latest_signal_date + timedelta(days=1)
    title = f"ETF轮动策略信号-{signal_for_date.strftime('%Y-%m-%d')}"
    markdown_message = f"### {title}\n\n" \
                       f"**信号生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" \
                       f"**信号基于数据:** {latest_signal_date.strftime('%Y-%m-%d')}\n\n" \
                       f"---\n\n" \
                       f"#### 策略建议持仓:\n\n" \
                       f"- **持有ETF 1:** {etf1}\n" \
                       f"  - **建议仓位:** {weight1:.2%}\n\n" \
                       f"- **持有ETF 2:** {etf2}\n" \
                       f"  - **建议仓位:** {weight2:.2%}\n"

    send_to_dingtalk(config.DINGTALK_WEBHOOK_URL, config.DINGTALK_SECRET, title, markdown_message)


def run_backtest():
    """
    运行完整的回测。
    """
    print("开始执行历史回测...")
    all_symbols = list(set(config.ETF_SYMBOLS_UPDATED + [config.BENCHMARK_SYMBOL]))
    closes, opens = get_etf_data(all_symbols, config.CACHE_FILE, force_refresh=False)
    if closes is None:
        print("获取数据失败，回测终止。")
        return
    run_strategy_comparison(config.ETF_SYMBOLS_UPDATED, config.BENCHMARK_SYMBOL, closes, opens)


# --- 主程序入口 ---
if __name__ == '__main__':
    # --- 选项1：运行完整的回测对比 ---
    # run_backtest()

    # --- 选项2：生成并发送明日的交易信号 ---
    generate_and_send_live_signal()