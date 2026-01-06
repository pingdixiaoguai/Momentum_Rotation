from datetime import datetime, timedelta
import config
from core.data import DataLoader
from core.strategies import CustomStrategy
from logics import logic_bias_protection
from utils import logger
from notifier import send_to_dingtalk, send_at_all_nudge

# 导入因子
from factors import Momentum, MainLineBias


def get_production_strategy():
    """
    定义生产环境使用的【唯一】策略。
    建议确保这里的配置与 run.py 中回测表现最好的参数一致。
    """
    strategy = CustomStrategy(
            factors={
                'mom': Momentum(20),      # 20日动量
                'bias': MainLineBias(20)  # 20日乖离率
            },
            logic_func=logic_bias_protection,   # 从 logics 模块导入
            name="Func_Bias_Filter",
            holding_period=5
        )
    return strategy


def run_live_signal():
    logger.info("Starting Live Signal Generation...")

    # 1. 动态计算数据窗口
    # 我们需要过去 365 天的数据来确保长周期因子（如年线、半年线）能计算出来
    # 结束日期设为今天
    today = datetime.now()
    start_date = today - timedelta(days=365)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")

    # 2. 强制同步最新行情
    # auto_sync=True 保证脚本运行时先去爬取今天的最新收盘价
    try:
        loader = DataLoader(start_str, end_str, auto_sync=True)
        data_dict = loader.load(config.ETF_SYMBOLS)
    except Exception as e:
        msg = f"数据同步失败: {str(e)}"
        logger.error(msg)
        send_to_dingtalk(config.DINGTALK_WEBHOOK, config.DINGTALK_SECRET, "策略报警", msg)
        return

    # 3. 初始化策略并计算
    strategy = get_production_strategy()

    try:
        # 获取所有历史日期的权重
        weights_df = strategy.generate_target_weights(**data_dict)
    except Exception as e:
        msg = f"因子计算失败: {str(e)}"
        logger.error(msg, exc_info=True)
        send_to_dingtalk(config.DINGTALK_WEBHOOK, config.DINGTALK_SECRET, "策略报警", msg)
        return

    if weights_df.empty:
        logger.warning("No weights generated.")
        return

    # 4. 提取【最新一天】的信号
    # 注意：generate_target_weights 返回的是"目标持仓"。
    # 如果 data_dict 包含了今天(T日)的收盘价，那么最后一行就是"明天(T+1)应持有的仓位"。
    last_date = weights_df.index[-1]
    last_weights = weights_df.iloc[-1]

    # 过滤出持仓标的
    holdings = last_weights[last_weights > 0]

    # 5. 格式化消息
    if holdings.empty:
        pos_str = "**空仓 (Cash)**"
    else:
        items = [f"`{code}` ({w:.0%})" for code, w in holdings.items()]
        pos_str = f"**持有**: {' '.join(items)}"

    # 6. 发送通知
    title = f"信号: {strategy.name}"
    text = (
        f"### {title}\n\n"
        f"**信号日期**: {last_date.strftime('%Y-%m-%d')}\n"
        f"*(基于当日收盘价计算，建议次日开盘调仓)*\n\n"
        f"{pos_str}\n\n"
        f"---\n"
        f"*AutoBot Execution at {datetime.now().strftime('%H:%M:%S')}*"
    )

    logger.info(f"Signal generated: {last_date.date()} -> {pos_str}")

    # 发送Markdown卡片
    send_to_dingtalk(config.DINGTALK_WEBHOOK, config.DINGTALK_SECRET, title, text)
    # 强提醒
    send_at_all_nudge(config.DINGTALK_WEBHOOK, config.DINGTALK_SECRET)


if __name__ == "__main__":
    run_live_signal()