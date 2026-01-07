import os
from datetime import date
# 引入 dotenv 用于加载 .env 文件
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
load_dotenv()

# 资产池配置
ETF_SYMBOLS = ["510300", "518880", "513100", "159915"] 
# 沪深300, 黄金, 纳指, 创业板

# 回测配置
START_DATE = "2013-01-01"
END_DATE = date.today().strftime('%Y-%m-%d')
TRANSACTION_COST = 0.0005 # 万分之五

# 钉钉配置 (从环境变量中读取，如果没有则默认为空字符串)
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK", "")
DINGTALK_SECRET = os.getenv("DINGTALK_SECRET", "")