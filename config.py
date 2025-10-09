# config.py
from datetime import date

# --- ETF与基准配置 ---
ETF_SYMBOLS = ["510300", "518880", "513100", "159915"]
BENCHMARK_SYMBOL = "510300"

# --- 策略窗口期配置 ---
MOMENTUM_WINDOW = 20

# --- 交易费率配置 ---
TRANSACTION_COST = 0.5 / 10000

# --- 回测时间配置 ---
START_DATE = "2017-01-01"
END_DATE = date.today().strftime('%Y-%m-%d')

# --- 文件路径配置 ---
OUTPUT_HTML_FILE = "report.html"
CACHE_FILE = "etf_data.csv"

# --- 钉钉机器人配置 ---
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=aa6e2d0c9d3d1af143d6add20064ed2ed2af8a46e82c41cf722924e3e6302a9f"
DINGTALK_SECRET = "SEC27397ae3d84b0b1ca313d40cc36d72dc8c929ca1962c9b31b7e99b924c864798"