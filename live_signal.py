from datetime import datetime, timedelta
import config
from data_loader import get_etf_data
from notifier import send_to_dingtalk


def generate_and_send(strategy_func):
    """
    一个通用的函数，用于为下一个交易日生成信号并发送钉钉通知。
    它可以接收任何一个定义在strategies.py中的策略函数。

    :param strategy_func: 一个策略函数，接收收盘价DataFrame并返回持仓信号Series。
    """
    print(f"\n--- 使用策略 '{strategy_func.__name__}' 为下一个交易日生成信号 ---")

    # 1. 强制刷新获取最新数据
    closes, _ = get_etf_data(config.ETF_SYMBOLS, config.CACHE_FILE, force_refresh=True)
    if closes is None:
        print("获取最新数据失败，无法生成信号。")
        return

    # 2. 调用指定的策略函数获取所有历史信号
    all_signals = strategy_func(closes)
    if all_signals.empty:
        print("数据不足，无法计算有效信号。")
        return

    # 3. 提取最新的信号用于明天
    latest_signal_date = all_signals.index[-1]
    next_day_holding = all_signals.iloc[-1]

    print(f"信号基于日期: {latest_signal_date.strftime('%Y-%m-%d')}, 建议明日持仓: {next_day_holding}")

    # 4. 格式化并发送消息
    signal_for_date = latest_signal_date + timedelta(days=1)
    title = f"ETF轮动策略信号-{signal_for_date.strftime('%Y-%m-%d')}"

    holding_text = f"**满仓持有: {next_day_holding}**" if next_day_holding != 'cash' else "**空仓，持有现金**"

    markdown_message = (f"### {title}\n\n"
                        f"**策略名称:** `{strategy_func.__name__}`\n\n"
                        f"**信号生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"**信号基于数据:** {latest_signal_date.strftime('%Y-%m-%d')}\n\n"
                        f"---\n\n"
                        f"#### 明日策略建议:\n\n"
                        f"{holding_text}\n")

    send_to_dingtalk(config.DINGTALK_WEBHOOK_URL, config.DINGTALK_SECRET, title, markdown_message)