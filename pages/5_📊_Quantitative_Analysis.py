# pages/5_📊_Quantitative_Analysis.py

"""
量化分析页面

功能:
- 技术指标分析
- 因子评分
- 风险管理 (VaR/CVaR)
- ML预测
- 回测分析
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AnalysisEngine.InsightAgent.indicators import *
from AnalysisEngine.InsightAgent.factor_engine import FactorEngine
from AnalysisEngine.InsightAgent.risk import VaRCalculator, StressTester
from AnalysisEngine.InsightAgent.signal_generator import *
from AnalysisEngine.InsightAgent.simple_backtester import SimpleBacktester

try:
    from AnalysisEngine.InsightAgent.ml import XGBoostPredictor
    ML_AVAILABLE = True
except:
    ML_AVAILABLE = False

# 页面配置
st.set_page_config(
    page_title="量化分析",
    page_icon="📊",
    layout="wide"
)

st.title("📊 量化分析系统")
st.markdown("---")

# 侧边栏 - 数据选择
st.sidebar.header("数据设置")

# 股票选择
symbol = st.sidebar.selectbox(
    "选择标的",
    ['GLD', 'SLV', 'GDX', 'GDXJ', 'IAU'],
    index=0
)

# 时间范围
days = st.sidebar.slider("历史天数", 30, 500, 180)

# 生成模拟数据 (实际应该从数据库获取)
@st.cache_data
def generate_mock_data(symbol, days):
    """生成模拟OHLCV数据"""
    np.random.seed(hash(symbol) % 100)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # 基础价格
    base_price = {'GLD': 180, 'SLV': 24, 'GDX': 30, 'GDXJ': 35, 'IAU': 38}.get(symbol, 100)
    
    close = base_price + np.cumsum(np.random.randn(days) * 2)
    high = close + np.random.rand(days) * 3
    low = close - np.random.rand(days) * 3
    volume = np.random.randint(1000000, 10000000, days)
    
    df = pd.DataFrame({
        'close': close,
        'high': high,
        'low': low,
        'volume': volume
    }, index=dates)
    
    return df

# 获取数据
data = generate_mock_data(symbol, days)

# 主内容区 - 标签页
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 技术指标",
    "🎯 因子分析",
    "🛡️ 风险管理",
    "🤖 ML预测",
    "📊 回测分析"
])

# ==================== Tab 1: 技术指标 ====================
with tab1:
    st.header("技术指标分析")
    
    # 指标选择
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("指标选择")
        show_ma = st.checkbox("移动平均线", value=True)
        show_bb = st.checkbox("布林带", value=True)
        show_rsi = st.checkbox("RSI", value=True)
        show_macd = st.checkbox("MACD", value=True)
    
    with col2:
        # 主图: 价格 + 均线 + 布林带
        fig_price = go.Figure()
        
        # K线图
        fig_price.add_trace(go.Candlestick(
            x=data.index,
            open=data['close'],  # 简化,用close代替open
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name='Price'
        ))
        
        # 移动平均线
        if show_ma:
            sma20 = TrendIndicators.moving_average(data['close'], 20, 'SMA')
            sma50 = TrendIndicators.moving_average(data['close'], 50, 'SMA')
            
            fig_price.add_trace(go.Scatter(
                x=data.index, y=sma20,
                name='SMA20', line=dict(color='orange', width=1)
            ))
            fig_price.add_trace(go.Scatter(
                x=data.index, y=sma50,
                name='SMA50', line=dict(color='blue', width=1)
            ))
        
        # 布林带
        if show_bb:
            upper_bb, middle_bb, lower_bb = TrendIndicators.bollinger_bands(data['close'])
            
            fig_price.add_trace(go.Scatter(
                x=data.index, y=upper_bb,
                name='BB Upper', line=dict(color='gray', width=1, dash='dash')
            ))
            fig_price.add_trace(go.Scatter(
                x=data.index, y=lower_bb,
                name='BB Lower', line=dict(color='gray', width=1, dash='dash'),
                fill='tonexty', fillcolor='rgba(128,128,128,0.1)'
            ))
        
        fig_price.update_layout(
            title=f'{symbol} 价格走势',
            xaxis_title='Date',
            yaxis_title='Price ($)',
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_price, use_container_width=True)
    
    # RSI指标
    if show_rsi:
        rsi = MomentumIndicators.rsi(data['close'], 14)
        
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=data.index, y=rsi, name='RSI', line=dict(color='purple')))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="超买")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="超卖")
        
        fig_rsi.update_layout(title='RSI指标', height=200, yaxis_title='RSI')
        st.plotly_chart(fig_rsi, use_container_width=True)
    
    # MACD指标
    if show_macd:
        macd_line, signal_line, histogram = TrendIndicators.macd(data['close'])
        
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=data.index, y=macd_line, name='MACD', line=dict(color='blue')))
        fig_macd.add_trace(go.Scatter(x=data.index, y=signal_line, name='Signal', line=dict(color='orange')))
        fig_macd.add_trace(go.Bar(x=data.index, y=histogram, name='Histogram'))
        
        fig_macd.update_layout(title='MACD指标', height=200, yaxis_title='MACD')
        st.plotly_chart(fig_macd, use_container_width=True)
    
    # 当前指标值
    st.subheader("当前指标值")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        current_rsi = rsi.iloc[-1] if show_rsi else None
        if current_rsi:
            st.metric("RSI(14)", f"{current_rsi:.2f}", 
                     delta="超买" if current_rsi > 70 else "超卖" if current_rsi < 30 else "中性")
    
    with col2:
        atr = VolatilityIndicators.atr(data['high'], data['low'], data['close'], 14)
        st.metric("ATR(14)", f"${atr.iloc[-1]:.2f}")
    
    with col3:
        hv = VolatilityIndicators.historical_volatility(data['close'], 30)
        st.metric("波动率(30d)", f"{hv.iloc[-1]*100:.1f}%")
    
    with col4:
        returns_1m = data['close'].pct_change(21).iloc[-1]
        st.metric("1月收益", f"{returns_1m*100:.1f}%")

# ==================== Tab 2: 因子分析 ====================
with tab2:
    st.header("多因子评分")
    
    try:
        # 计算因子
        engine = FactorEngine()
        factors = engine.calculate_all_factors(data)
        normalized = engine.normalize_factors(factors, method='z_score')
        composite_score = engine.calculate_composite_score(normalized)
        
        # 综合评分
        st.subheader(f"综合因子评分: {composite_score.iloc[-1]:.3f}")
        
        # 因子得分柱状图
        latest_factors = normalized.iloc[-1].sort_values()
        
        fig_factors = px.bar(
            x=latest_factors.values,
            y=latest_factors.index,
            orientation='h',
            title='各因子标准化得分',
            labels={'x': 'Z-Score', 'y': '因子'}
        )
        fig_factors.update_layout(height=400)
        st.plotly_chart(fig_factors, use_container_width=True)
        
        # 因子详情
        st.subheader("因子详情")
        factor_df = normalized.iloc[-1:].T
        factor_df.columns = ['当前值']
        st.dataframe(factor_df.style.background_gradient(cmap='RdYlGn', axis=0))
        
    except Exception as e:
        st.error(f"因子计算失败: {e}")

# ==================== Tab 3: 风险管理 ====================
with tab3:
    st.header("风险管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("VaR / CVaR分析")
        
        # 计算VaR
        returns = data['close'].pct_change().dropna()
        var_calc = VaRCalculator(confidence_level=0.95)
        
        hist_var = var_calc.historical_var(returns)
        param_var = var_calc.parametric_var(returns, distribution='normal')
        mc_var = var_calc.monte_carlo_var(returns, n_simulations=5000)
        
        # VaR对比
        var_comparison = pd.DataFrame({
            '方法': ['历史模拟法', '参数法', '蒙特卡洛'],
            'VaR(95%)': [hist_var.var_value, param_var.var_value, mc_var.var_value],
            'CVaR(95%)': [hist_var.cvar_value, param_var.cvar_value, mc_var.cvar_value]
        })
        
        st.dataframe(var_comparison.style.format({
            'VaR(95%)': '{:.2%}',
            'CVaR(95%)': '{:.2%}'
        }))
        
        # VaR指标卡片
        st.metric(
            "1日VaR (95%置信度)",
            f"{hist_var.var_value:.2%}",
            help="95%置信度下,1日最大损失"
        )
        st.metric(
            "CVaR (条件VaR)",
            f"{hist_var.cvar_value:.2%}",
            help="超过VaR时的平均损失"
        )
    
    with col2:
        st.subheader("压力测试")
        
        # 模拟组合
        portfolio = {symbol: 100}
        prices = {symbol: data['close'].iloc[-1]}
        
        stress_tester = StressTester()
        stress_results = stress_tester.run_all_scenarios(portfolio, prices)
        
        # 压力测试结果
        st.dataframe(stress_results[[
            'scenario_name', 'description', 'loss_pct', 'probability'
        ]].style.format({
            'loss_pct': '{:.2%}',
            'probability': '{:.2%}'
        }).background_gradient(subset=['loss_pct'], cmap='RdYlGn_r'))
        
        # 最坏场景
        worst = stress_tester.get_worst_scenario(portfolio, prices)
        st.warning(f"**最坏场景**: {worst['description']}\n\n"
                  f"预期损失: {worst['expected_loss_pct']:.2%}")

# ==================== Tab 4: ML预测 ====================
with tab4:
    st.header("机器学习预测")
    
    if ML_AVAILABLE:
        try:
            with st.spinner("训练XGBoost模型..."):
                predictor = XGBoostPredictor(n_estimators=50, max_depth=3)
                train_results = predictor.train(data, test_size=0.2, forecast_horizon=1)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("模型性能")
                st.metric("训练集准确率", f"{train_results['train_accuracy']:.1%}")
                st.metric("测试集准确率", f"{train_results['test_accuracy']:.1%}")
                
                # 预测
                direction = predictor.predict(data)
                probability = predictor.predict_proba(data)
                
                prediction_text = "📈 上涨" if direction == 1 else "📉 下跌"
                st.success(f"**明日预测**: {prediction_text}  \n概率: {probability:.1%}")
            
            with col2:
                st.subheader("特征重要性")
                importance = predictor.get_feature_importance().head(10)
               
                fig_importance = px.bar(
                    x=importance.values,
                    y=importance.index,
                    orientation='h',
                    title='Top 10 特征重要性'
                )
                st.plotly_chart(fig_importance, use_container_width=True)
                
        except Exception as e:
            st.error(f"ML预测失败: {e}")
    else:
        st.warning("XGBoost未安装。请运行: `pip install xgboost`")

# ==================== Tab 5: 回测分析 ====================
with tab5:
    st.header("策略回测")
    
    # 策略选择
    strategy_type = st.selectbox(
        "选择策略",
        ["趋势跟踪", "均值回归", "多策略融合"]
    )
    
    with st.spinner("运行回测..."):
        backtester = SimpleBacktester(initial_capital=100000)
        
        if strategy_type == "趋势跟踪":
            strategy = TrendFollowingStrategy(fast_period=10, slow_period=30)
        elif strategy_type == "均值回归":
            strategy = MeanReversionStrategy(bb_period=20, rsi_period=14)
        else:
            trend_strategy = TrendFollowingStrategy()
            mean_strategy = MeanReversionStrategy()
            multi_gen = MultiStrategySignalGenerator([trend_strategy, mean_strategy])
            strategy = lambda d: multi_gen.generate_consensus_signal(d)[0]
        
        if callable(strategy):
            signal_func = strategy
        else:
            signal_func = lambda d: strategy.generate_signal(d, 0)
        
        results = backtester.run_backtest(data, signal_func)
    
    # 性能指标
    col1, col2, col3, col4 = st.columns(4)
    summary = results['summary']
    
    with col1:
        st.metric("总收益", f"{summary['total_return']:.1%}")
    with col2:
        st.metric("年化收益", f"{summary['annual_return']:.1%}")
    with col3:
        st.metric("Sharpe比率", f"{summary['sharpe_ratio']:.2f}")
    with col4:
        st.metric("最大回撤", f"{summary['max_drawdown']:.1%}")
    
    col5, col6 = st.columns(2)
    with col5:
        st.metric("总交易次数", summary['total_trades'])
    with col6:
        st.metric("胜率", f"{summary['win_rate']:.1%}")
    
    # 权益曲线
    equity_curve = results['equity_curve']
    
    fig_equity = go.Figure()
    fig_equity.add_trace(go.Scatter(
        x=equity_curve.index,
        y=equity_curve['total'],
        name='组合价值',
        line=dict(color='green', width=2)
    ))
    fig_equity.add_hline(
        y=100000,
        line_dash="dash",
        line_color="gray",
        annotation_text="起始资金"
    )
    
    fig_equity.update_layout(
        title='权益曲线',
        xaxis_title='日期',
        yaxis_title='组合价值 ($)',
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_equity, use_container_width=True)
    
    # 交易记录
    if results['trades']:
        st.subheader("交易记录")
        trades_df = pd.DataFrame(results['trades'])
        st.dataframe(trades_df)

# 页脚
st.markdown("---")
st.caption("💡 提示: 以上数据为模拟数据。实际使用时需连接真实数据源。")
