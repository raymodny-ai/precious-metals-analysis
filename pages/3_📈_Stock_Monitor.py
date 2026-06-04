"""
股票监控Dashboard页面
监控贵金属相关股票的实时数据和走势
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from DataCollector.StockDataCollector.yfinance_client import YFinanceStockClient

st.set_page_config(
    page_title="Stock Monitor - PreciousInsight",
    page_icon="📈",
    layout="wide"
)

# 初始化会话状态
if 'selected_symbol' not in st.session_state:
    st.session_state.selected_symbol = 'GLD'

# 标题
st.title("📈 股票监控")
st.markdown("实时监控贵金属相关股票")

# 初始化客户端
@st.cache_resource
def get_stock_client():
    return YFinanceStockClient()

client = get_stock_client()

# 侧边栏 - 股票选择
with st.sidebar:
    st.header("股票筛选")
    
    # 分类选择
    category = st.selectbox(
        "选择分类",
        ["All", "ETF", "Mining", "Index"]
    )
    
    # 根据分类获取股票列表
    if category == "All":
        symbols = client.all_symbols
    elif category == "ETF":
        symbols = client.PRECIOUS_METAL_ETFS
    elif category == "Mining":
        symbols = client.MINING_STOCKS
    else:
        symbols = client.INDICES
    
    # 股票选择
    selected_symbol = st.selectbox(
        "选择股票",
        symbols,
        index=symbols.index(st.session_state.selected_symbol) if st.session_state.selected_symbol in symbols else 0
    )
    
    st.session_state.selected_symbol = selected_symbol
    
    # 刷新按钮
    if st.button("🔄 刷新数据"):
        st.cache_data.clear()
        st.rerun()

# 主要内容区域
tab1, tab2, tab3, tab4 = st.tabs(["📊 实时监控", "📈 价格走势", "🔍 相关性分析", "📰 股票新闻"])

# Tab 1: 实时监控
with tab1:
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader(f"{selected_symbol} 实时数据")
        
        # 获取实时报价
        @st.cache_data(ttl=60)
        def get_quote(symbol):
            return client.get_current_price(symbol)
        
        quote = get_quote(selected_symbol)
        
        if quote:
            # 价格指标
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            
            with metric_col1:
                st.metric(
                    "当前价格",
                    f"${quote['price']:.2f}",
                    f"{quote['change_percent']:+.2f}%"
                )
            
            with metric_col2:
                st.metric(
                    "成交量",
                    f"{quote['volume']:,.0f}" if quote['volume'] else "N/A"
                )
            
            with metric_col3:
                st.metric(
                    "市值",
                    f"${quote['market_cap']/1e9:.1f}B" if quote['market_cap'] else "N/A"
                )
            
            with metric_col4:
                st.metric(
                    "PE比率",
                    f"{quote['pe_ratio']:.2f}" if quote['pe_ratio'] else "N/A"
                )
    
    with col2:
        st.subheader("与金价相关性")
        
        @st.cache_data(ttl=3600)
        def get_correlation(symbol):
            return client.calculate_correlation_with_gold(symbol, period='3mo')
        
        corr = get_correlation(selected_symbol)
        
        if corr is not None:
            # 相关性仪表盘
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = corr,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "相关系数"},
                gauge = {
                    'axis': {'range': [-1, 1]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [-1, -0.5], 'color': "lightcoral"},
                        {'range': [-0.5, 0], 'color': "lightyellow"},
                        {'range': [0, 0.5], 'color': "lightblue"},
                        {'range': [0.5, 1], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 0.7
                    }
                }
            ))
            
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            if corr > 0.7:
                st.success("✅ 高度正相关")
            elif corr > 0.3:
                st.info("ℹ️ 中度正相关")
            elif corr < -0.3:
                st.warning("⚠️ 负相关")
            else:
                st.info("ℹ️ 弱相关")
    
    with col3:
        st.subheader("分类")
        category_badge = client.get_category(selected_symbol)
        st.markdown(f"**类型**: {category_badge}")
        
        if quote:
            st.markdown(f"**前收盘**: ${quote['previous_close']:.2f}")
            st.markdown(f"**涨跌**: ${quote['change']:+.2f}")

# Tab 2: 价格走势
with tab2:
    st.subheader("历史价格走势")
    
    # 时间周期选择
    period_col1, period_col2 = st.columns([1, 3])
    
    with period_col1:
        period = st.selectbox(
            "时间周期",
            ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            index=2
        )
    
    # 获取历史数据
    @st.cache_data(ttl=3600)
    def get_history(symbol, period):
        return client.get_historical_data(symbol, period=period)
    
    hist = get_history(selected_symbol, period)
    
    if hist is not None and not hist.empty:
        # K线图
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name=selected_symbol
        ))
        
        # 添加移动平均线
        if len(hist) >= 20:
            hist['MA20'] = hist['Close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist['MA20'],
                mode='lines',
                name='MA20',
                line=dict(color='orange', width=1)
            ))
        
        if len(hist) >= 50:
            hist['MA50'] = hist['Close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist['MA50'],
                mode='lines',
                name='MA50',
                line=dict(color='blue', width=1)
            ))
        
        fig.update_layout(
            title=f"{selected_symbol} 价格走势",
            yaxis_title="价格 (USD)",
            xaxis_title="日期",
            height=500,
            xaxis_rangeslider_visible=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 成交量图
        fig_volume = go.Figure()
        
        fig_volume.add_trace(go.Bar(
            x=hist.index,
            y=hist['Volume'],
            name='成交量',
            marker_color='rgba(100, 149, 237, 0.5)'
        ))
        
        fig_volume.update_layout(
            title="成交量",
            yaxis_title="成交量",
            height=200
        )
        
        st.plotly_chart(fig_volume, use_container_width=True)

# Tab 3: 相关性分析
with tab3:
    st.subheader("股票相关性矩阵")
    
    # 选择要分析的股票
    analysis_symbols = st.multiselect(
        "选择股票（最多10只）",
        client.all_symbols,
        default=['GLD', 'SLV', 'NEM', 'GOLD', 'GDX'][:5]
    )
    
    if len(analysis_symbols) >= 2:
        with st.spinner("计算相关性..."):
            # 获取数据并计算相关性
            @st.cache_data(ttl=3600)
            def calculate_correlation_matrix(symbols):
                dfs = []
                for symbol in symbols:
                    df = client.get_historical_data(symbol, period='3mo')
                    if df is not None and not df.empty:
                        dfs.append(df[['Close']].rename(columns={'Close': symbol}))
                
                if len(dfs) < 2:
                    return None
                
                # 合并数据
                merged = dfs[0]
                for df in dfs[1:]:
                    merged = merged.join(df, how='inner')
                
                # 计算相关性
                return merged.corr()
            
            corr_matrix = calculate_correlation_matrix(analysis_symbols)
            
            if corr_matrix is not None:
                # 热力图
                fig = px.imshow(
                    corr_matrix,
                    labels=dict(color="相关系数"),
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    color_continuous_scale='RdBu_r',
                    aspect="auto"
                )
                
                fig.update_layout(
                    title="相关性热力图",
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 显示相关性数值
                st.dataframe(
                    corr_matrix.style.background_gradient(cmap='RdBu_r', vmin=-1, vmax=1),
                    use_container_width=True
                )
    else:
        st.info("请选择至少2只股票进行相关性分析")

# Tab 4: 股票新闻
with tab4:
    st.subheader(f"{selected_symbol} 相关新闻")
    
    @st.cache_data(ttl=1800)
    def get_stock_news(symbol):
        # 这里使用yfinance的新闻功能
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        news = ticker.news
        return news[:10] if news else []
    
    news_items = get_stock_news(selected_symbol)
    
    if news_items:
        for item in news_items:
            with st.expander(f"📰 {item.get('title', 'No title')}"):
                st.markdown(f"**来源**: {item.get('publisher', 'Unknown')}")
                
                if 'providerPublishTime' in item:
                    pub_time = datetime.fromtimestamp(item['providerPublishTime'])
                    st.markdown(f"**时间**: {pub_time.strftime('%Y-%m-%d %H:%M')}")
                
                if 'link' in item:
                    st.markdown(f"[阅读全文]({item['link']})")
    else:
        st.info("暂无新闻数据")

# 页脚
st.markdown("---")
st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
