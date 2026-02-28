# Momentum Rotation Strategy Framework（动量轮动策略框架）

一个基于 Python 的现代化量化回测与实盘信号框架，采用**因子化架构（Factor-Based Architecture）**，将因子计算、策略逻辑、执行引擎三层完全解耦，旨在解决传统量化代码耦合度高、扩展困难的问题。

> 像搭积木一样，用 `Momentum`、`Volatility`、`Peak` 等因子快速构建并回测复杂的轮动策略。

---

## ✨ 核心特性

- **🧱 因子化架构**：`Factor` 抽象类 + `logic_func` 纯函数完全解耦，策略由因子字典 + 逻辑函数自由组合。
- **🚀 极简扩展**：在 `factors/` 新建子类、在 `logics/` 新建函数即可，不触碰引擎代码。
- **💾 双数据源支持**：
  - **AkShare**（默认）——数据完整，支持历史回测，有封 IP 风险
  - **BaoStock**（推荐）——稳定可靠，自动对齐复权价格，无封 IP 风险
  - 基于 **Parquet** 分年存储，支持真正的增量同步
- **⚡ 向量化引擎**：T+1 开盘执行模型，无 `for` 循环，Pandas 全向量化回测。
- **📈 Walk-Forward 验证**：内置 WFA（滚动窗口前向分析），量化过拟合风险。
- **🔔 生产级通知**：集成钉钉群机器人，实盘信号自动推送；集成 QuantStats 生成专业 HTML 研报。

---

## 📂 项目结构

```text
Momentum_Rotation/
├── core/
│   ├── base.py             # Factor / Strategy 抽象基类
│   ├── data.py             # DataLoader：读取 Parquet → 宽表字典
│   ├── engine.py           # RealWorldEngine：T+1 开盘执行回测引擎
│   └── strategies.py       # CustomStrategy：通用因子轮动策略
├── factors/                # 因子库
│   ├── momentum.py         # Momentum —— (close_t / close_{t-N}) - 1
│   ├── momentum_castle.py  # Momentum_castle —— 相对滚动低点的涨幅
│   ├── volatility.py       # Volatility / IntradayVolatility
│   ├── reversion.py        # MeanReversion
│   ├── bias.py             # MainLineBias —— 乖离率
│   ├── peak.py             # Peak —— 距滚动高点的距离
│   └── __init__.py
├── logics/                 # 策略逻辑函数（纯函数，与因子解耦）
│   ├── factor_rotation.py  # logic_factor_rotation —— 多因子打分轮动
│   ├── bias_protection.py  # logic_bias_protection —— 乖离率保护
│   └── __init__.py
├── infra/
│   ├── repo.py             # Parquet 读写 + 增量同步入口
│   └── fetchers/
│       ├── base.py         # AbstractETFFetcher 抽象类
│       ├── akshare.py      # AkShare 实现（后复权 hfq）
│       ├── baostock.py     # BaoStock 实现（自动价格归一化）
│       └── __init__.py     # get_fetcher() 工厂函数
├── utils/                  # 日志、枚举、常量定义
├── run.py                  # 入口：同步数据 → 回测 → 生成 HTML 研报
├── wfa.py                  # 入口：Walk-Forward Analysis（滚动前向验证）
├── live.py                 # 入口：生产信号（同步最新数据 → 钉钉推送）
├── config.py               # 全局参数：ETF 标的池、回测时间、手续费
├── notifier.py             # 钉钉通知模块
├── .env                    # 私密配置（Token、路径、数据源）
└── pyproject.toml          # 依赖管理（推荐 uv）
```

---

## 🚀 快速开始

### 1. 安装依赖

推荐 Python `>= 3.11`，使用 `uv` 进行依赖管理：

```bash
uv sync
```

### 2. 配置 `.env`

在项目根目录创建 `.env` 文件：

```ini
# [必填] 数据存储目录
DATA_DIR="./data"

# [推荐] 数据源选择：akshare（默认，有封 IP 风险）或 baostock（稳定）
DATA_FETCHER=baostock

# [可选] 钉钉机器人配置（不需要通知可留空）
DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=你的Token"
DINGTALK_SECRET="你的加签密钥"

# [可选] 请求间隔（秒，防止频率过高）
TICK_INTERVAL=0.2
```

### 3. 运行回测

```bash
python run.py
```

执行流程：
1. **数据同步**：自动检查并增量更新 `config.py` 中的 ETF 数据到本地 Parquet
2. **因子计算**：计算 `run.py` 中配置的所有策略因子
3. **策略回测**：向量化执行，生成逐日持仓与收益序列
4. **结果输出**：每个策略单独生成 `report_{策略名}.html`（QuantStats 专业研报）

### 4. Walk-Forward 验证（防过拟合）

```bash
python wfa.py
```

输出 `wfa_result.png`（训练/验证期收益对比）和 `report_wfa.html`。

### 5. 生产信号推送

```bash
python live.py
```

同步最新数据，计算当日信号，通过钉钉发送持仓建议。

---

## 🛠️ 开发指南

### 添加新因子

在 `factors/` 目录下继承 `Factor`，实现 `calculate` 方法（只声明需要的字段）：

```python
# factors/technical.py
import pandas as pd
from core.base import Factor

class RSI(Factor):
    def __init__(self, window: int = 14):
        super().__init__(f"RSI_{window}")
        self.window = window

    def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(self.window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))  # 返回宽表：Index=Date, Columns=ETFCode
```

然后在 `factors/__init__.py` 中导出即可使用。

### 添加新策略逻辑

在 `logics/` 新建纯函数，签名固定为：

```python
def my_logic(factor_values: dict, closes: pd.DataFrame, top_k=1, **kwargs) -> pd.DataFrame:
    # factor_values: {"因子名": 宽表 DataFrame}
    # 返回权重宽表（行和 <= 1.0，0 表示空仓）
    ...
```

### 在 `run.py` 中组合策略

```python
from core.strategies import CustomStrategy
from factors import Momentum, MainLineBias
from logics import logic_bias_protection

strategies = [
    CustomStrategy(
        name="Bias_Filter",
        factors={
            'mom':  Momentum(20),
            'bias': MainLineBias(20),
        },
        logic_func=logic_bias_protection,
        holding_period=1,
        top_k=1,
    )
]
```

### 修改回测标的与时间

编辑 `config.py`：

```python
ETF_SYMBOLS = ["510300", "518880", "513100", "159915", "510210"]
START_DATE  = "2013-01-01"
END_DATE    = date.today().strftime('%Y-%m-%d')
TRANSACTION_COST = 0.0005  # 万分之五
```

---

## 📊 数据说明

### 数据源

| 参数值 | 来源 | 复权方式 | 历史覆盖 | 稳定性 |
|--------|------|----------|----------|--------|
| `akshare` | 东方财富 | 后复权（hfq） | 完整 | 有封 IP 风险 |
| `baostock` | BaoStock | 不复权（自动归一化） | 2026 年起 | 稳定 |

> **关于 BaoStock 价格归一化**：BaoStock 对 ETF 不支持复权，返回实际市价（不复权）。框架在首次拼接时会自动计算 `scale = 本地最新后复权价 / BaoStock 首行昨收`，将新数据等比缩放至与历史数据一致的价格尺度，此后每次增量同步该系数自动维持稳定，无需人工干预。

### 数据字段

Parquet 存储字段：`datetime`, `code`, `name`, `open`, `high`, `low`, `close`, `preclose`, `volume`, `amount`, `turn`（换手率）、`price_chg`（涨跌幅）等。

`DataLoader` 读取后自动 Pivot 为宽表字典，key 为字段名小写（如 `data['close']`），Index 为日期，Columns 为 ETF 代码。

### 回测引擎执行模型

采用 **T+1 开盘执行**，避免前视偏差：

| 信号日 | 执行日 | 收益计算 |
|--------|--------|----------|
| T 日收盘产生信号 | T+1 日开盘成交 | |
| 持仓日 | — | `(close_T / close_{T-1}) - 1` |
| 买入日 | T+1 | `(close_{T+1} - open_{T+1}) / open_{T+1}` |
| 卖出日 | T+1 | `(open_{T+1} / close_T) - 1` |

交易成本（`TRANSACTION_COST`，默认 0.05%）在每次换仓时从收益中扣除。

---

## 📦 主要依赖

| 库 | 用途 |
|----|------|
| `akshare` | A 股 ETF 历史数据获取 |
| `baostock` | 备用数据源（推荐生产环境使用） |
| `pandas` / `numpy` | 向量化因子计算 |
| `pyarrow` | Parquet 高性能存储 |
| `quantstats` | HTML 回测研报生成 |
| `python-dotenv` | 环境变量管理 |
| `cachetools` | 交易日缓存 |
| `tqdm` | 同步进度显示 |
