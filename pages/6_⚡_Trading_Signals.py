# pages/6_⚡_Trading_Signals.py

"""
交易信号实时监控页面

功能:
- 多策略信号监控
- 信号历史记录
- 信号强度可视化
- 实时更新
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AnalysisEngine.InsightAgent.signal_generator import *
from AnalysisEngine.InsightAgent.indicators import *

st.set_page_config(
    page_title="交易信号",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ 交易信号监控")
st.markdown("---")

# 侧边栏
st.sidebar.header("监控设置")

# 标的选择
symbols = st.sidebar.multiselect(
    "选择监控标的",
    ['GLD', 'SLV', 'GDX', 'GDXJ', 'IAU', 'PPLT', 'PALL'],
    default=['GLD', 'SLV', 'GDX']
)

# 策略选择
strategies_enabled = {
    '趋势跟踪': st.sidebar.checkbox("趋势跟踪策略", value=True),
    '均值回归': st.sidebar.checkbox("均值回归策略", value=True),
    '突破策略': st.sidebar.checkbox("突破策略", value=False)
}

# 信号过滤
min_strength = st.sidebar.slider("最小信号强度", 0.0, 1.0, 0.3, 0.1)

# 自动刷新
auto_refresh = st.sidebar.checkbox("自动刷新 (30秒)", value=False)
if auto_refresh:
    st.sidebar.info("⏰ 将在30秒后刷新")

# 生成模拟数据
@st.cache_data(ttl=30)
def generate_mock_data(symbol, days=100):
    np.random.seed(hash(symbol) % 100 + int(datetime.now().timestamp()) % 10)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    base_price = {'GLD': 180, 'SLV': 24, 'GDX': 30, 'GDXJ': 35, 'IAU': 38, 'PPLT': 90, 'PALL': 150}.get(symbol, 100)
    close = base_price + np.cumsum(np.random.randn(days) * 2)
    high = close + np.random.rand(days) * 3
    low = close - np.random.rand(days) * 3
    volume = np.random.randint(1000000, 10000000, days)
    
    return pd.DataFrame({
        'close': close, 'high': high, 'low': low, 'volume': volume
    }, index=dates)

# 生成信号
def generate_signals_for_symbol(symbol):
    data = generate_mock_data(symbol)
    
    signals = []
    
    # 趋势跟踪
    if strategies_enabled['趋势跟踪']:
        trend_strategy = TrendFollowingStrategy(fast_period=10, slow_period=30)
        trend_signal = trend_strategy.generate_signal(data)
        if trend_signal.strength >= min_strength:
            signals.append(trend_signal)
    
    # 均值回归
    if strategies_enabled['均值回归']:
        mean_rev_strategy = MeanReversionStrategy(bb_period=20, rsi_period=14)
        mean_rev_signal = mean_rev_strategy.generate_signal(data)
        if mean_rev_signal.strength >= min_strength:
            signals.append(mean_rev_signal)
    
    # 多策略共识
    if len(signals) >= 2:
        multi_gen = MultiStrategySignalGenerator([
            TrendFollowingStrategy(),
            MeanReversionStrategy()
        ])
        consensus, _ = multi_gen.generate_consensus_signal(data)
        if consensus.strength >= min_strength:
            signals.append(consensus)
    
    return signals

# 主内容
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📊 当前信号")
    
    # 收集所有信号
    all_signals = []
    for symbol in symbols:
        signals = generate_signals_for_symbol(symbol)
        for signal in signals:
            all_signals.append({
                '标的': symbol,
                '策略': signal.strategy_name,
                '信号': signal.signal_type.value,
                '强度': signal.strength,
                '价格': signal.price,
                '理由': signal.reasoning
            })
    
    if all_signals:
        signals_df = pd.DataFrame(all_signals)
        
        # 信号类型着色
        def color_signal(val):
            if 'buy' in val.lower():
                return 'background-color: #90EE90'
            elif 'sell' in val.lower():
                return 'background-color: #FFB6C1'
            else:
                return 'background-color: #D3D3D3'
        
        st.dataframe(
            signals_df.style.applymap(color_signal, subset=['信号']).format({
                '强度': '{:.2f}',
                '价格': '${:.2f}'
            }),
            use_container_width=True,
            height=400
        )
        
        # 信号统计
        st.subheader("📈 信号统计")
        signal_counts = signals_df['信号'].value_counts()
        
        fig_pie = px.pie(
            values=signal_counts.values,
            names=signal_counts.index,
            title='信号分布',
            color=signal_counts.index,
            color_discrete_map={
                'buy': '#90EE90',
                'strong_buy': '#00FF00',
                'sell': '#FFB6C1',
                'strong_sell': '#FF0000',
                'hold': '#D3D3D3'
            }
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    else:
        st.info("🔍 当前无符合条件的信号")

with col2:
    st.header("🎯 信号强度")
    
    if all_signals:
        # 按标的分组显示强度
        for symbol in symbols:
            symbol_signals = [s for s in all_signals if s['标的'] == symbol]
            if symbol_signals:
                st.subheader(symbol)
                
                for sig in symbol_signals:
                    signal_emoji = "📈" if 'buy' in sig['信号'] else "📉" if 'sell' in sig['信号'] else "➡️"
                    
                    st.metric(
                        f"{signal_emoji} {sig['策略']}",
                        sig['信号'].upper(),
                        f"强度: {sig['强度']:.2f}"
                    )
                
                st.markdown("---")

# 信号历史
st.header("📜 信号历史")

# 模拟历史信号
@st.cache_data
def generate_signal_history(days=30):
    history = []
    for i in range(days):
        date = datetime.now() - timedelta(days=days-i)
        for symbol in ['GLD', 'SLV', 'GDX']:
            if np.random.rand() > 0.7:  # 30%概率有信号
                signal_type = np.random.choice(['buy', 'sell', 'hold'])
                history.append({
                    '日期': date.strftime('%Y-%m-%d'),
                    '标的': symbol,
                    '信号': signal_type,
                    '强度': np.random.uniform(0.3, 1.0),
                    '价格': np.random.uniform(20, 200)
                })
    return pd.DataFrame(history)

history_df = generate_signal_history()

# 时间序列图
fig_timeline = px.scatter(
    history_df,
    x='日期',
    y='标的',
    size='强度',
    color='信号',
    hover_data=['价格', '强度'],
    title='信号时间线',
    color_discrete_map={
        'buy': 'green',
        'sell': 'red',
        'hold': 'gray'
    }
)
fig_timeline.update_layout(height=300)
st.plotly_chart(fig_timeline, use_container_width=True)

# 详细历史表格
with st.expander("查看详细历史"):
    st.dataframe(
        history_df.sort_values('日期', ascending=False).style.format({
            '强度': '{:.2f}',
            '价格': '${:.2f}'
        }),
        use_container_width=True
    )

# 实时技术指标快照
st.header("📊 技术指标快照")

cols = st.columns(len(symbols))
for i, symbol in enumerate(symbols):
    with cols[i]:
        st.subheader(symbol)
        data = generate_mock_data(symbol)
        
        # 计算关键指标
        rsi = MomentumIndicators.rsi(data['close'], 14).iloc[-1]
        macd, signal_line, _ = TrendIndicators.macd(data['close'])
        macd_trend = "金叉" if macd.iloc[-1] > signal_line.iloc[-1] else "死叉"
        
        st.metric("RSI(14)", f"{rsi:.1f}")
        st.metric("MACD", macd_trend)
        st.metric("当前价", f"${data['close'].iloc[-1]:.2f}")

# 页脚
st.markdown("---")
if auto_refresh:
    st.rerun()
else:
    if st.button("🔄 手动刷新"):
        st.rerun()

st.caption("💡 提示: 开启自动刷新可实时监控信号变化")
