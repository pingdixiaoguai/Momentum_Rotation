from datetime import datetime, timedelta
import time  # 导入 time 模块
import config
from data_loader import get_etf_data
from notifier import send_to_dingtalk, send_at_all_nudge


def generate_and_send(strategy_func):
    """
    为下一个交易日生成信号，并分两步发送钉钉通知：
    1. 发送详细的Markdown消息。
    2. 发送一条简单的 @所有人 提醒消息。
    """
    print(f"\n--- 使用策略 '{strategy_func.__name__}' 为下一个交易日生成信号 ---")

    # 1. 获取最新数据
    closes, _ = get_etf_data(config.ETF_SYMBOLS, config.CACHE_FILE, force_refresh=True)
    if closes is None: return

    # 2. 调用策略函数获取信号
    all_signals = strategy_func(closes)
    if all_signals.empty: return

    # 3. 提取最新信号
    latest_signal_date = all_signals.index[-1]
    next_day_holding = all_signals.iloc[-1]

    print(f"信号基于日期: {latest_signal_date.strftime('%Y-%m-%d')}, 建议明日持仓: {next_day_holding}")

    # 4. 准备 Markdown 消息内容
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

    # 5. 执行两步发送
    # 第一步：发送漂亮的Markdown消息
    print("正在发送详细的Markdown策略信号...")
    send_to_dingtalk(
        config.DINGTALK_WEBHOOK_URL,
        config.DINGTALK_SECRET,
        title,
        markdown_message,
        is_at_all=False  # 确保这里是False
    )

    # 短暂延时，避免消息太快
    time.sleep(1)

    # 第二步：发送 @所有人 的提醒
    send_at_all_nudge(
        config.DINGTALK_WEBHOOK_URL,
        config.DINGTALK_SECRET
    )