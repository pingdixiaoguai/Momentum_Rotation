# config.py

# --- ETF与基准配置 ---
ETF_SYMBOLS_UPDATED = ["511260", "511360", "518880", "513500", "510300", "159941", "512890", "000509"]
BENCHMARK_SYMBOL = "510300"

# --- 策略窗口期配置 ---
# 原始单动量策略
MOMENTUM_WINDOW_ORIGINAL = 21
# 加权双动量策略
MOMENTUM_LONG_WINDOW = 21
MOMENTUM_REVERSAL_WINDOW = 0
TOTAL_WINDOW = MOMENTUM_LONG_WINDOW + MOMENTUM_REVERSAL_WINDOW

# --- 文件路径配置 ---
OUTPUT_HTML_FILE = "strategy_dual_momentum_report.html"
CACHE_FILE = "etf_data_cache_expanded.csv"

# --- 钉钉机器人配置 ---
# !!重要!! 请将下面替换成你自己的Webhook地址和密钥
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=aa6e2d0c9d3d1af143d6add20064ed2ed2af8a46e82c41cf722924e3e6302a9f"
DINGTALK_SECRET = "SEC27397ae3d84b0b1ca313d40cc36d72dc8c929ca1962c9b31b7e99b924c864798"