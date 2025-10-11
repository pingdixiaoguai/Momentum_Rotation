# ======================================================================
#                            主程序入口
# ======================================================================
#
#   - 回测: 运行 backtester.py 中的 Backtester 类
#   - 信号: 运行 live_signal.py 中的 generate_and_send 函数
#
# ======================================================================

# --- 导入所需模块 ---
import config
from data_loader import get_etf_data
from backtester import Backtester
from live_signal import generate_and_send
# --- 从 strategies.py 导入我们想使用的所有策略 ---
from strategies.risk_managed_momentum_strategy import risk_managed_momentum_strategy
from strategies.pure_momentum_strategy import pure_momentum_strategy

# --- 在这里选择要执行的模式 ---
MODE = "backtest"  # 'backtest' 或 'signal'

if __name__ == '__main__':

    if MODE == 'backtest':
        print("--- 模式一：执行历史回测 ---")
        closes, opens = get_etf_data(config.ETF_SYMBOLS, config.CACHE_FILE, force_refresh=False)
        if closes is not None:
            # 1. 初始化回测引擎
            bt = Backtester()

            # 2. 选择一个策略函数并运行回测
            # !!! 您可以在这里轻松切换不同的策略进行回测 !!!
            bt.run(closes, opens, strategy_func=risk_managed_momentum_strategy)
            # bt.run(closes, opens, strategy_func=pure_momentum_strategy)

    elif MODE == 'signal':
        print("--- 模式二：生成并发送明日信号 ---")

        # 1. 选择要用于发送信号的策略函数
        # !!! 确保这里的策略和您最终决定的回测策略一致 !!!
        generate_and_send(strategy_func=risk_managed_momentum_strategy)
        # generate_and_send(strategy_func=pure_momentum_strategy)

    else:
        print(f"错误：未知的模式 '{MODE}'。请选择 'backtest' 或 'signal'。")