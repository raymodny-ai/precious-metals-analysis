import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="PreciousInsight", layout="wide", page_icon="💰")

# Sidebar
with st.sidebar:
    st.title("💰 PreciousInsight")
    st.markdown("实时监控贵金属市场")
    page = st.radio("导航", ["仪表盘", "新闻分析", "趋势预测", "报告"])

# Main page
if page == "仪表盘":
    st.header("贵金属市场仪表盘")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("黄金价格", "$2,050.00", "+1.2%")
    with col2:
        st.metric("白银价格", "$24.50", "-0.8%")
    with col3:
        st.metric("白金价格", "$950.00", "+0.3%")
    with col4:
        st.metric("钯金价格", "$1,100.00", "+2.1%")
    
    # Price chart
    st.subheader("价格趋势")
    
    # Sample data
    dates = pd.date_range(start='2024-01-01', end='2024-11-27', freq='D')
    gold_prices = [2000 + i*0.5 for i in range(len(dates))]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=gold_prices, mode='lines', name='Gold'))
    fig.update_layout(title='黄金价格走势 (USD/oz)', xaxis_title='日期', yaxis_title='价格')
    st.plotly_chart(fig, use_container_width=True)
    
    # News feed
    st.subheader("最新新闻")
    st.info("🟢 正面 | Federal Reserve signals potential rate cuts - Gold surges")
    st.warning("⚪ 中性 | Mining production remains stable in Q4")
    st.error("🔴 负面 | Dollar strengthens on strong employment data")

elif page == "新闻分析":
    st.header("新闻情感分析")
    st.write("新闻情感分析功能即将推出...")

elif page == "趋势预测":
    st.header("市场趋势预测")
    st.write("AI驱动的趋势预测功能即将推出...")

elif page == "报告":
    st.header("智能报告")
    st.write("自动生成的市场报告功能即将推出...")
    if st.button("生成今日报告"):
        st.success("报告生成中...")
