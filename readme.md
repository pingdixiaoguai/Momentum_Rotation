# **动量轮动策略框架 (Momentum Rotation Strategy Framework)**

这是一个基于 Python 的量化回测与研究框架，专注于**动量轮动 (Momentum Rotation)** 类策略的开发、测试与实盘信号生成。

本项目已从早期的脚本化代码重构为模块化的工程架构，支持**基于 Parquet 的增量数据存储**、**面向对象的策略开发**以及**批量参数扫描**。

## **核心特性**

* **工程化架构**: 采用清晰的分层设计（数据层、策略层、引擎层），解耦业务逻辑与底层实现。  
* **专业数据系统**: 废弃了低效的 CSV 全量读写，集成 infra 模块，使用 **Parquet** 进行高效、增量的时间序列存储。  
* **灵活的策略接口**: 策略以类（Class）的形式存在，支持参数化配置（如 window=20 vs window=30），方便进行 Grid Search。  
* **批量回测研究**: 提供独立的 run\_research.py 入口，支持一次性运行多个策略配置并生成对比报表。  
* **可扩展性**: 核心逻辑抽象为 DataProvider 和 Strategy 接口，方便未来接入数据库或新增策略类型。

## **项目结构**

Momentum\_Rotation/  
├── core.py             \# \[核心\] 定义抽象基类 (DataProvider, Strategy, BacktestEngine)  
├── data.py             \# \[数据\] Parquet 数据适配层，负责连接 infra 与策略层  
├── engine.py           \# \[引擎\] 回测计算核心与报告生成器  
├── strategies.py       \# \[策略\] 具体的策略实现 (如 PureMomentum, RiskManagedMomentum)  
├── run\_research.py     \# \[入口\] 批量回测与研究脚本  
├── config.py           \# \[配置\] 全局参数配置  
├── infra/              \# \[底层\] 数据仓库管理 (Parquet 读写、Akshare 同步逻辑)  
├── utils/              \# \[工具\] 通用工具函数与常量定义  
└── logs/               \# \[日志\] 运行日志

## **🛠️ 快速开始**

### **1\. 环境准备**

本项目使用 pyproject.toml 管理依赖，并默认要求使用 [**uv**](https://github.com/astral-sh/uv) 进行高效的包管理和环境配置。

1. **安装 uv** (如果尚未安装):  
   pip install uv

2. 初始化与同步依赖:  
   在项目根目录下运行以下命令，uv 将根据 pyproject.toml 自动创建虚拟环境并安装所需依赖：  
   uv sync

### **2\. 数据准备**

本项目使用 infra 模块管理数据。首次运行时，您可以在 run\_research.py 中开启自动同步，或者手动调用同步脚本。

数据将存储在 data/ 或 infra 配置的目录下的 Parquet 文件中。

### **3\. 运行回测**

直接运行研究入口脚本：

python run\_research.py

该脚本会执行以下操作：

1. 通过 ParquetDataProvider 加载指定时间段的 ETF 数据。  
2. 初始化多个不同参数的策略实例（例如 20日动量 vs 30日动量）。  
3. 运行回测引擎计算净值曲线。  
4. 打印各策略的夏普比率与累计收益。  
5. 生成策略对比图表 (strategy\_comparison.png)。  
6. 为表现最好的策略生成详细的 HTML 报告 (report\_StrategyName.html)。

## **🧩 模块说明**

### **数据层 (data.py & infra/)**

* **ParquetDataProvider**: 实现了 core.DataProvider 接口。它不直接下载数据，而是调用 infra 层的接口读取本地 Parquet 文件，并将其转换为策略所需的宽表格式 (DataFrame, Index=Date, Columns=Symbols)。  
* **infra/**: 负责底层的 Akshare 数据下载、清洗、去重以及写入 Parquet 文件。支持断点续传和增量更新。

### **策略层 (strategies.py)**

所有策略均继承自 core.Strategy。

* **PureMomentumStrategy**: 纯粹的动量策略，持有过去 N 天涨幅最高的标的。  
* **RiskManagedMomentumStrategy**: 引入反转因子的改进版策略，通过 Rank 加权 (动量 \- 反转) 来规避短期过热标的。

### **引擎层 (engine.py)**

* **BacktestEngine**: 专注于资金曲线的计算。它接收宽表数据和策略信号，输出 BacktestResult。  
* **ReportGenerator**: 基于 quantstats 生成专业的 HTML 回测报告。

## **⚙️ 配置指南**

在 config.py 中修改全局配置：

\# 目标资产池 (ETF 代码)  
ETF\_SYMBOLS \= \["510300", "518880", "513100", "159915"\]

\# 默认回测时间段  
START\_DATE \= "2013-01-01"  
END\_DATE \= "2024-12-30"

\# 交易费率  
TRANSACTION\_COST \= 0.0005 

## **📝 开发指南**

**如何添加一个新策略？**

1. 在 strategies.py 中创建一个新类，继承自 Strategy。  
2. 实现 generate\_signals(self, closes, volumes) 方法，返回每日持仓信号。  
3. 在 run\_research.py 的 test\_strategies 列表中加入你的新策略实例。

\# 示例  
class MyNewStrategy(Strategy):  
    def generate\_signals(self, closes, volumes=None):  
        \# 你的逻辑...  
        return signals

## **⚠️ 注意事项**

* **数据完整性**: 首次运行建议在 run\_research.py 中设置 auto\_sync=True 以确保本地有完整数据。  
* **Parquet 依赖**: 必须安装 pyarrow 库才能读写 Parquet 文件。