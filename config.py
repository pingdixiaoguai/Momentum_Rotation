import os
from datetime import date

# 资产池配置
ETF_SYMBOLS = ["510300", "518880", "513100", "159915"]   
# 沪深300, 黄金, 纳指, 创业板

# 回测配置
START_DATE = "2013-01-01"
END_DATE = date.today().strftime('%Y-%m-%d')
TRANSACTION_COST = 0.0005 # 万分之五

# 钉钉配置 (建议使用环境变量，不要硬编码在代码里)
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK", "")
DINGTALK_SECRET = os.getenv("DINGTALK_SECRET", "")