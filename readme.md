动量轮动策略框架 (Momentum Rotation Framework)
这是一个基于 Python 的现代化量化回测与实盘信号框架，经过重构后采用了因子化架构 (Factor-Based Architecture)。
本项目旨在解决传统量化代码中“策略逻辑”与“执行逻辑”耦合过重的问题。通过将因子计算与持仓管理完全分离，你现在可以像搭积木一样，通过组合不同的因子（如动量、波动率、RSI）来快速构建复杂的轮动策略。
✨ 核心特性
因子化架构: 核心逻辑解耦。编写策略只需关注“因子公式”，持仓权重由通用引擎自动计算。
极简扩展: 在 factors/library.py 中几行代码即可定义新因子，支持任意数据字段输入（如 open, high, turnover）。
高性能数据层: 基于 Parquet 的增量数据仓库 (infra 模块)，支持 DataLoader 自动同步与清洗，以宽表字典 (Dict[str, DataFrame]) 形式高效传输数据。
向量化引擎: 摒弃低效的 for 循环，采用全向量化计算，极速完成多年回测。
生产级功能: 集成钉钉群机器人通知、HTML 专业研报生成 (quantstats)。
📂 项目结构
重构后的目录结构清晰明了，消除了旧版本的冗余代码：
Momentum_Rotation/
├── core/                   # [核心架构] 系统的骨架
│   ├── base.py             # 定义 Factor 和 Strategy 抽象基类
│   ├── data.py             # 统一数据加载器 (封装了 infra)
│   └── strategies.py       # 通用轮动策略逻辑 (排序、加权、择时)
├── factors/                # [因子库] 你的军火库
│   └── library.py          # 在这里编写 Momentum, Volatility 等因子
├── infra/                  # [数据底层] 负责 Parquet 读写与 Akshare 同步
├── utils/                  # [工具] 通用函数
├── run.py                  # [入口] 唯一的上帝入口 (回测/实盘)
├── config.py               # [配置] 全局参数
├── notifier.py             # [通知] 钉钉消息发送
├── .env                    # [私密] 存放 Token 和 Secret
└── pyproject.toml          # [依赖] 项目依赖管理


🚀 快速开始
1. 环境准备
本项目推荐使用 uv 进行依赖管理（比 pip 快得多）。
# 初始化环境并同步依赖
uv sync


或者使用传统的 pip：
pip install -r requirements.txt
# (注: 如果没有 requirements.txt，请根据 pyproject.toml 安装)


2. 配置文件
为了保护隐私，钉钉机器人的密钥不再硬编码。请在项目根目录创建一个 .env 文件：
# .env 文件
DINGTALK_WEBHOOK=[https://oapi.dingtalk.com/robot/send?access_token=你的Token](https://oapi.dingtalk.com/robot/send?access_token=你的Token)
DINGTALK_SECRET=你的加签密钥


3. 运行回测
一切就绪后，直接运行统一入口脚本：
python run.py


程序将自动：
检查并同步最新的 ETF 数据。
计算配置在 run.py 中的所有策略因子。
生成回测净值曲线、夏普比率等指标。
保存对比图表 backtest_result.png。
🛠️ 开发指南
如何添加一个新因子？
你只需要在 factors/library.py 中继承 Factor 类并实现 calculate 方法。
示例：添加一个“日内波动率”因子
# factors/library.py

class IntradayVolatility(Factor):
    def __init__(self, window: int = 14):
        super().__init__(f"IntradayVol_{window}")
        self.window = window
    
    # 使用 **kwargs 自动接收 high 和 low 数据
    # 只要数据源里有这两列，这里就能直接用
    def calculate(self, high, low, **kwargs):
        daily_range = (high - low) / low
        # 返回滚动均值
        return daily_range.rolling(self.window).mean()


如何构建新策略？
在 run.py 中，你不需要写新的策略类，只需要配置 FactorRotationStrategy：
# run.py

strategies = [
    # 策略示例：低波动动量策略
    FactorRotationStrategy(
        factors=[
            (Momentum(20), 1.0),         # 动量因子，权重 1.0 (越高越好)
            (IntradayVolatility(14), -0.5) # 波动因子，权重 -0.5 (越低越好)
        ],
        top_k=1, # 每日持有排名前 1 的标的
        timing_period=60 # 可选：必须站上 60 日均线才持有
    )
]


📊 数据说明
数据存放在 infra/data 目录下，格式为 Parquet。
core/data.py 中的 DataLoader 会自动处理数据的读取、对齐和清洗，并返回一个包含所有字段的字典：
data['close']: 收盘价宽表
data['open']: 开盘价宽表
data['high']: 最高价宽表
... 以及任何底层数据源包含的字段
Happy Quant Trading! 📈
