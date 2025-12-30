# Momentum Rotation Strategy Framework (动量轮动策略框架)

这是一个基于 Python 的现代化量化回测与实盘信号框架。本项目采用**因子化架构 (Factor-Based Architecture)**，将策略逻辑与执行逻辑解耦，旨在解决传统量化代码耦合度高、扩展困难的问题。

通过本框架，你可以像搭积木一样，利用 `Momentum`（动量）、`Volatility`（波动率）等因子快速构建并回测复杂的轮动策略。

## ✨ 核心特性

* **🧱 因子化架构**: 核心逻辑完全解耦。编写策略只需关注“因子公式”（继承 `Factor` 类），持仓权重由通用引擎自动计算。
* **🚀 极简扩展**: 在 `factors/` 目录下即可定义新因子，支持任意数据字段输入（如 `open`, `high`, `turnover`）。
* **💾 高性能数据层**:
    * 基于 **AkShare** 获取实时/历史数据。
    * 使用 **Parquet** 格式进行本地增量存储，读取速度极快。
    * `DataLoader` 自动处理数据的同步、清洗与对齐，直接返回宽表字典。
* **⚡ 向量化引擎**: 摒弃低效的 `for` 循环，采用 Pandas 全向量化计算，极速完成多年回测。
* **🔔 生产级功能**: 集成 **钉钉 (DingTalk)** 群机器人通知，支持策略信号自动推送；集成 **QuantStats** 生成专业的 HTML 回测研报。

## 📂 项目结构

```text
Momentum_Rotation/
├── core/                   # [核心架构] 系统的骨架
│   ├── base.py             # 定义 Factor 和 Strategy 抽象基类
│   ├── data.py             # 统一数据加载器 (封装了 infra，提供宽表数据)
│   └── strategies.py       # 通用轮动策略逻辑 (排序、加权、择时)
├── factors/                # [因子库] 你的军火库
│   ├── momentum.py         # 动量因子实现
│   ├── volatility.py       # 波动率因子实现
│   ├── reversion.py        # 均值回归因子实现
│   └── __init__.py         # 因子包导出管理
├── infra/                  # [数据底层] 负责 Parquet 读写与 Akshare 数据同步
├── utils/                  # [工具] 通用函数、日志配置、重试机制
├── run.py                  # [入口] 唯一的上帝入口 (回测/实盘)
├── config.py               # [配置] 全局回测参数 (标的池、时间等)
├── notifier.py             # [通知] 钉钉消息发送模块
├── .env                    # [私密] 存放 Token、Secret 和数据路径
├── logging.conf            # [日志] 日志格式配置文件
└── pyproject.toml          # [依赖] 项目依赖管理

```

## 🚀 快速开始

### 1. 环境准备

本项目推荐使用 `uv` 进行现代化的依赖管理，或者使用传统的 `pip`。要求 Python版本 `>= 3.11`。

**使用 uv (推荐):**

```bash
uv sync

```

**使用 pip:**

```bash
# 如果没有 requirements.txt，请参考 pyproject.toml 安装依赖
pip install akshare pandas quantstats requests tenacity pyarrow python-dotenv cachetools notebook

```

### 2. 配置文件 (.env)

为了保护隐私及灵活配置，请在项目根目录创建一个 `.env` 文件，配置数据存储路径及钉钉机器人密钥：

```ini
# .env 文件内容示例

# [必填] 数据存储目录 (程序会自动创建子目录)
DATA_DIR="./data"

# [可选] 钉钉机器人配置 (若不需要通知可留空)
DINGTALK_WEBHOOK="[https://oapi.dingtalk.com/robot/send?access_token=你的Token](https://oapi.dingtalk.com/robot/send?access_token=你的Token)"
DINGTALK_SECRET="你的加签密钥"

# [可选] 数据同步请求间隔 (秒)
TICK_INTERVAL=0.2

```

### 3. 运行回测

一切就绪后，运行统一入口脚本：

```bash
python run.py

```

程序将自动执行以下步骤：

1. **数据同步**: 检查并从 AkShare 同步 `config.py` 中配置的 ETF 最新数据到本地 `data` 目录。
2. **因子计算**: 计算配置在 `run.py` 中的所有策略因子（如 20日动量、日内波动率等）。
3. **策略回测**: 生成回测净值曲线、夏普比率等指标。
4. **结果输出**:
* 在控制台打印回测日志。
* 保存对比图表为 `backtest_result.png`。



## 🛠️ 开发指南

### 如何添加一个新因子？

你只需要在 `factors/` 目录下新建文件（或在现有文件中）继承 `Factor` 类并实现 `calculate` 方法。

**示例：添加一个“RSI”因子**

```python
# factors/technical.py
import pandas as pd
from core.base import Factor

class RSI(Factor):
    def __init__(self, window: int = 14):
        super().__init__(f"RSI_{window}")
        self.window = window
    
    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        # 简单的 RSI 计算逻辑
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

```

### 如何构建新策略？

在 `run.py` 中，你不需要修改底层代码，只需通过配置 `FactorRotationStrategy` 组合不同的因子：

```python
# run.py 中的 strategies 列表

strategies = [
    # 策略示例：低波动动量策略 (Low Volatility Momentum)
    FactorRotationStrategy(
        factors=[
            (Momentum(20), 1.0),            # 动量因子，权重 1.0 (正向)
            (IntradayVolatility(14), -0.5), # 波动因子，权重 -0.5 (反向，越低越好)
            (MeanReversion(5), -0.3)        # 反转因子，权重 -0.3 (剔除短期涨幅过大的)
        ],
        top_k=1,         # 每日持有排名前 1 的标的
        timing_period=60 # [可选] 均线择时：只有价格 > 60日均线才持有
    )
]

```

### 如何修改回测标的？

编辑 `config.py` 文件：

```python
# config.py
ETF_SYMBOLS = ["510300", "518880", "513100", "159915"] # 修改为你感兴趣的代码
START_DATE = "2018-01-01" # 修改回测开始时间

```

## 📊 数据说明

* 数据通过 `infra` 模块自动管理，格式为 **Parquet**。
* 支持的数据字段包括：`open`, `high`, `low`, `close`, `volume`, `amount`, `turn` (换手率) 等。
* `DataLoader` 会自动处理数据的**复权**（AkShare 默认返回前复权数据）和**对齐**（填充缺失值）。