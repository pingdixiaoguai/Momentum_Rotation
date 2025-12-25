import config
from data_loader import get_etf_data
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MultipleLocator

closes, opens, volumes = get_etf_data(config.ETF_SYMBOLS, config.CACHE_FILE, force_refresh=False)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# 确保索引是datetime类型
if not isinstance(closes.index, pd.DatetimeIndex):
    closes.index = pd.to_datetime(closes.index)

# 股票列表
stocks = ["510300", "518880", "513100", "159915"]
stock_names = {
    "510300": "CSI 300 ETF",
    "518880": "Gold ETF", 
    "513100": "Nasdaq ETF",
    "159915": "ChiNext ETF"
}
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

# 创建输出目录
output_dir = "stock_charts"
os.makedirs(output_dir, exist_ok=True)
print(f"Charts will be saved in: {output_dir}/")

# 为每支股票创建独立的图表
for i, stock in enumerate(stocks):
    if stock not in closes.columns:
        print(f"Warning: {stock} not found in dataframe")
        continue
    
    # 获取股票数据，去除NaN值
    stock_data = closes[stock].dropna()
    
    if len(stock_data) < 2:
        print(f"Warning: Insufficient data for {stock}")
        continue
    
    print(f"\nProcessing {stock}...")
    
    # 创建独立的figure
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # 绘制主价格线
    main_line = ax.plot(stock_data.index, stock_data.values, 
                       color=colors[i], linewidth=2.5, alpha=0.9, 
                       label=f'{stock}', zorder=3)
    
    # 计算并绘制移动平均线（20日）
    window = min(20, len(stock_data))
    ma_data = stock_data.rolling(window=window, min_periods=1).mean()
    ax.plot(ma_data.index, ma_data.values, 
           color='gray', linewidth=1.5, linestyle='--', alpha=0.7,
           label=f'{window}-day MA', zorder=2)
    
    # 填充价格区域
    ax.fill_between(stock_data.index, stock_data.values, 
                   alpha=0.2, color=colors[i], zorder=1)
    
    # 设置标题和坐标轴标签
    stock_title = stock_names.get(stock, f"ETF {stock}")
    ax.set_title(f'{stock_title} - Price Trend Analysis', 
                fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Date', fontsize=14, labelpad=12)
    ax.set_ylabel('Price (CNY)', fontsize=14, labelpad=12)
    
    # 设置x轴格式 - 智能选择刻度间隔
    date_range = stock_data.index.max() - stock_data.index.min()
    
    if date_range.days <= 180:  # 半年以内
        # 每月显示主要刻度
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        # 每周显示次要刻度
        ax.xaxis.set_minor_locator(mdates.WeekLocator())
        
    elif date_range.days <= 730:  # 两年以内
        # 每季度显示主要刻度
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1,4,7,10]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        # 每月显示次要刻度
        ax.xaxis.set_minor_locator(mdates.MonthLocator())
        
    else:  # 超过两年
        # 每年显示主要刻度
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        # 每季度显示次要刻度
        ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[1,4,7,10]))
    
    # 旋转x轴标签
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 设置网格线
    ax.grid(True, which='major', linestyle='-', linewidth=0.8, alpha=0.7, color='#CCCCCC')
    ax.grid(True, which='minor', linestyle=':', linewidth=0.5, alpha=0.4, color='#DDDDDD')
    
    # 设置坐标轴背景
    ax.set_facecolor('#f8f9fa')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 计算统计信息
    initial_price = stock_data.iloc[0]
    current_price = stock_data.iloc[-1]
    price_change_pct = ((current_price / initial_price) - 1) * 100
    volatility = stock_data.pct_change().std() * np.sqrt(252) * 100  # 年化波动率
    max_price = stock_data.max()
    min_price = stock_data.min()
    avg_price = stock_data.mean()
    median_price = stock_data.median()
    
    # 计算技术指标
    # 计算RSI（相对强弱指数）
    def calculate_rsi(prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    if len(stock_data) >= 30:
        rsi = calculate_rsi(stock_data)
        current_rsi = rsi.iloc[-1]
    else:
        current_rsi = None
    
    # 创建详细的统计信息表格
    stats_data = [
        ["Initial Price", f"{initial_price:.2f}"],
        ["Current Price", f"{current_price:.2f}"],
        ["Total Return", f"{price_change_pct:+.2f}%"],
        ["Annual Volatility", f"{volatility:.2f}%"],
        ["Maximum Price", f"{max_price:.2f}"],
        ["Minimum Price", f"{min_price:.2f}"],
        ["Average Price", f"{avg_price:.2f}"],
        ["Median Price", f"{median_price:.2f}"],
    ]
    
    if current_rsi is not None:
        stats_data.append(["Current RSI(14)", f"{current_rsi:.1f}"])
    
    # 将统计信息添加到图表
    stats_text = "Performance Metrics:\n"
    stats_text += "-" * 40 + "\n"
    for label, value in stats_data:
        stats_text += f"{label:20} {value:>10}\n"
    
    # 将统计框放在左上角
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
           fontsize=10, verticalalignment='top', horizontalalignment='left',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.95, 
                    edgecolor=colors[i], linewidth=1.5),
           fontfamily='monospace')
    
    # 添加交易量信息（如果可用）
    volume_text = f"Data Period: {stock_data.index[0]:%Y-%m-%d} to {stock_data.index[-1]:%Y-%m-%d}\n"
    volume_text += f"Trading Days: {len(stock_data):,}"
    
    ax.text(0.02, 0.02, volume_text, transform=ax.transAxes,
           fontsize=9, verticalalignment='bottom', horizontalalignment='left',
           bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.7))
    
    # 添加关键水平线
    # 支撑线（最近20日最低点）
    support_level = stock_data.rolling(window=min(20, len(stock_data))).min().iloc[-1]
    # 阻力线（最近20日最高点）
    resistance_level = stock_data.rolling(window=min(20, len(stock_data))).max().iloc[-1]
    
    ax.axhline(y=support_level, color='green', linestyle='--', alpha=0.5, linewidth=1)
    ax.axhline(y=resistance_level, color='red', linestyle='--', alpha=0.5, linewidth=1)
    
    ax.text(stock_data.index[-1], support_level, f' Support: {support_level:.2f}',
           fontsize=8, verticalalignment='bottom', horizontalalignment='right',
           color='green', alpha=0.7)
    
    ax.text(stock_data.index[-1], resistance_level, f' Resistance: {resistance_level:.2f}',
           fontsize=8, verticalalignment='bottom', horizontalalignment='right',
           color='red', alpha=0.7)
    
    # 添加图例
    ax.legend(loc='upper left', fontsize=11, framealpha=0.9, 
              fancybox=True, shadow=True)
    
    # 自动调整y轴范围，留出一些空间
    y_min, y_max = stock_data.min(), stock_data.max()
    y_range = y_max - y_min
    padding = y_range * 0.08
    ax.set_ylim(y_min - padding, y_max + padding)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存为多种格式
    filename_base = f"{stock}_price_chart"
    
    # PNG格式（高分辨率）
    png_path = f"{output_dir}/{filename_base}.png"
    plt.savefig(png_path, dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    print(f"  Saved as PNG: {png_path}")

    # 显示图表
    # plt.show()
    
    # 关闭当前图表，准备下一个
    # plt.close(fig)

print(f"\n{'='*50}")
print("All charts have been generated successfully!")
print(f"Check the '{output_dir}' directory for output files.")
print(f"{'='*50}")