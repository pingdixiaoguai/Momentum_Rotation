# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies (recommended: uv):**
```bash
uv sync
```

**Run backtest** (syncs data, computes factors, generates HTML reports):
```bash
python run.py
```

**Run Walk-Forward Analysis** (out-of-sample validation, generates `wfa_result.png` + `report_wfa.html`):
```bash
python wfa.py
```

**Run live signal generation** (syncs latest data, sends DingTalk notification):
```bash
python live.py
```

**Run tests:**
```bash
python -m pytest
```

**Environment setup** — create a `.env` file in the project root:
```ini
DATA_DIR="./data"
DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=..."
DINGTALK_SECRET="your_secret"
TICK_INTERVAL=0.2
```

## Architecture

This is a **factor-based momentum rotation** framework for Chinese A-share ETFs. The design separates factor computation from strategy logic, enabling mix-and-match composition.

### Data Flow

```
AkShare (remote) → infra/repo.py (sync + Parquet storage) → core/data.py (DataLoader)
                                                                      ↓
                                                         Dict[field, wide_df]
                                                    (Index=Date, Columns=ETFCode)
                                                                      ↓
                                               factors/*.py (Factor.calculate)
                                                                      ↓
                                              logics/*.py (logic_func: factor_values + closes → weights)
                                                                      ↓
                                              core/strategies.py (CustomStrategy.generate_target_weights)
                                                                      ↓
                                              run.py RealWorldEngine (weights → daily returns)
```

**`core/engine.py` — `RealWorldEngine`**: The backtest engine (T+1 open execution model). Used by both `run.py` and `wfa.py`.

**`wfa.py`**: Walk-Forward Analysis entry point. The `run_walk_forward()` function can be imported and reused; `strategy_factory` at the top of `main()` is the only section that needs changing to test a different strategy.

### Key Abstractions

**`core/base.py`** defines two ABCs:
- `Factor`: implement `calculate(**kwargs) -> pd.DataFrame` — receives the full data dict, declare only needed fields by name (e.g. `def calculate(self, close, **kwargs)`). Returns a wide DataFrame (Date × Asset).
- `Strategy`: implement `generate_target_weights(**kwargs) -> pd.DataFrame` — returns target weights (row sums ≤ 1.0).

**`core/strategies.py` — `CustomStrategy`**: The primary concrete strategy. Takes a `factors` dict (name → Factor instance), a `logic_func`, and optional `**logic_kwargs` that are forwarded to the logic function on every call.

**`logics/`** — pure functions with signature `(factor_values: Dict[str, DataFrame], closes: DataFrame, **kwargs) -> weights_DataFrame`. No class required. Keeps strategy logic decoupled from factor math.

**`core/data.py` — `DataLoader`**: Reads Parquet files and pivots them into a `dict` of wide DataFrames keyed by lowercase field name (`open`, `close`, `high`, `low`, `volume`, `amount`, `turn`, etc.). Pass `auto_sync=True` to fetch missing data via AkShare before loading.

**`infra/repo.py`**: All AkShare calls and Parquet I/O live here. Data is stored at `{DATA_DIR}/{data_type}/{code}/{year}/{year}.parquet` for daily bars, and `{DATA_DIR}/{data_type}/{code}/{year}/tick/{date}.parquet` for tick data. Incremental sync: checks local max date before downloading.

### Backtest Engine (`run.py` — `RealWorldEngine`)

The engine uses a **T+1 open execution** model to avoid look-ahead bias:
- Signal on T close → trade at T+1 open
- **Hold day**: full base return `(close_t / close_{t-1}) - 1`
- **Buy day**: only intraday return `(close - open) / open`
- **Sell day**: only overnight return `(open / prev_close) - 1`
- Transaction cost applied on position changes (`TRANSACTION_COST` from `config.py`, default 0.05%)

### Adding a New Factor

1. Create (or add to) a file in `factors/`, inherit `Factor`, implement `calculate`:
   ```python
   class MyFactor(Factor):
       def __init__(self, window=20):
           super().__init__(f"MyFactor_{window}")
           self.window = window
       def calculate(self, close: pd.DataFrame, **kwargs) -> pd.DataFrame:
           return close.rolling(self.window).mean()  # wide DataFrame
   ```
2. Export it from `factors/__init__.py`.
3. Use it in `run.py` or `live.py` by adding to a `CustomStrategy`'s `factors` dict.

### Adding a New Strategy Logic

Create a function in `logics/` and export from `logics/__init__.py`:
```python
def my_logic(factor_values, closes, top_k=1, **kwargs):
    # factor_values: {name: wide_df}
    # return: weights wide_df (same shape as closes)
```
Pass it as `logic_func=my_logic` to `CustomStrategy`, with extra params as `**logic_kwargs`.

### `castle_stg1` Risk Control Flag

In `logics/factor_rotation.py`, passing `stg_flag=["castle_stg1"]` activates special handling for the `Mom_20` factor:
1. Uses percentile rank (0–1) instead of raw score for `Mom_20`.
2. Forces all-cash on days where the best momentum across all assets ≤ −10%.

### Configuration

- **`config.py`**: `ETF_SYMBOLS` (list of ETF codes), `START_DATE`, `END_DATE`, `TRANSACTION_COST`.
- **`.env`**: `DATA_DIR` (required), DingTalk credentials, `TICK_INTERVAL`.
- `infra/__init__.py` reads `DATA_DIR` and `TICK_INTERVAL` from env at import time.

### Available Factors (`factors/`)

| Class | File | Description |
|---|---|---|
| `Momentum` | `momentum.py` | `(close_t / close_{t-N}) - 1` |
| `Momentum_castle` | `momentum_castle.py` | `(close_t / min(close[:3])) - 1` over rolling window |
| `Volatility` | `volatility.py` | Rolling std of returns |
| `IntradayVolatility` | `volatility.py` | Rolling std of `(close - open) / open` |
| `MeanReversion` | `reversion.py` | Short-term reversal signal |
| `MainLineBias` | `bias.py` | `(close / MA) - 1` |
| `Peak` | `peak.py` | Distance from rolling high |
