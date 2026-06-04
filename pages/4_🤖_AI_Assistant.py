"""
AI助手页面 (增强版)
使用LLM + 量化分析进行智能问答和市场分析
"""
import streamlit as st
import sys
import os
from datetime import datetime
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from AnalysisEngine.LLMService.llm_service import get_llm_service
from AnalysisEngine.LLMService.rag_system import get_rag_system
from AnalysisEngine.LLMService.base import LLMRequest, TaskType

# 导入量化分析模块
from AnalysisEngine.InsightAgent.indicators import *
from AnalysisEngine.InsightAgent.risk import VaRCalculator, StressTester
from AnalysisEngine.InsightAgent.signal_generator import *

try:
    from AnalysisEngine.InsightAgent.ml import XGBoostPredictor
    ML_AVAILABLE = True
except:
    ML_AVAILABLE = False

st.set_page_config(
    page_title="AI Assistant - PreciousInsight",
    page_icon="🤖",
    layout="wide"
)

# 初始化LLM服务
@st.cache_resource
def init_llm():
    return get_llm_service()

@st.cache_resource
def init_rag():
    return get_rag_system()

# 生成模拟数据 (实际应从数据库获取)
@st.cache_data(ttl=600)
def get_market_data(symbol='GLD', days=180):
    np.random.seed(hash(symbol) % 100)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    base_price = {'GLD': 180, 'SLV': 24, 'GDX': 30}.get(symbol, 100)
    close = base_price + np.cumsum(np.random.randn(days) * 2)
    high = close + np.random.rand(days) * 3
    low = close - np.random.rand(days) * 3
    volume = np.random.randint(1000000, 10000000, days)
    return pd.DataFrame({
        'close': close, 'high': high, 'low': low, 'volume': volume
    }, index=dates)

# 生成量化分析上下文
def generate_quant_context(symbol='GLD'):
    """生成技术指标和风险分析作为LLM上下文"""
    try:
        data = get_market_data(symbol)
        close = data['close']
        
        # 技术指标
        rsi = MomentumIndicators.rsi(close, 14).iloc[-1]
        macd, signal, _ = TrendIndicators.macd(close)
        macd_trend = "金叉" if macd.iloc[-1] > signal.iloc[-1] else "死叉"
        
        upper_bb, middle_bb, lower_bb = TrendIndicators.bollinger_bands(close)
        bb_position = (close.iloc[-1] - lower_bb.iloc[-1]) / (upper_bb.iloc[-1] - lower_bb.iloc[-1])
        
        # 风险指标
        returns = close.pct_change().dropna()
        var_calc = VaRCalculator(confidence_level=0.95)
        var_result = var_calc.historical_var(returns)
        
        # 交易信号
        trend_strategy = TrendFollowingStrategy()
        signal = trend_strategy.generate_signal(data)
        
        # ML预测 (如果可用)
        ml_prediction = ""
        if ML_AVAILABLE:
            try:
                predictor = XGBoostPredictor(n_estimators=50, max_depth=3)
                predictor.train(data, test_size=0.2)
                direction = predictor.predict(data)
                probability = predictor.predict_proba(data)
                ml_prediction = f"\n- ML预测: {'上涨' if direction == 1 else '下跌'} (置信度: {probability:.1%})"
            except:
                pass
        
        context = f"""
【{symbol} 量化分析】
=== 技术指标 ===
- 当前价格: ${close.iloc[-1]:.2f}
- RSI(14): {rsi:.1f} ({'超买' if rsi > 70 else '超卖' if rsi < 30 else '中性'})
- MACD: {macd_trend}
- 布林带位置: {bb_position:.1%} ({'接近上轨' if bb_position > 0.8 else '接近下轨' if bb_position < 0.2 else '中性'})

=== 风险指标 ===
- VaR(95%): {var_result.var_value:.2%} (1日最大损失)
- CVaR: {var_result.cvar_value:.2%} (极端损失)

=== 交易信号 ===
- 趋势策略: {signal.signal_type.value.upper()} (强度: {signal.strength:.2f})
- 理由: {signal.reasoning}{ml_prediction}
"""
        return context
    except Exception as e:
        return f"量化分析上下文生成失败: {e}"

llm = init_llm()
rag = init_rag()

# 初始化会话状态
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'use_rag' not in st.session_state:
    st.session_state.use_rag = True

# 标题
st.title("🤖 AI 分析助手")
st.markdown("基于LLM的智能市场分析和问答系统")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置")
    
    # RAG开关
    use_rag = st.checkbox(
        "启用历史上下文检索 (RAG)",
        value=st.session_state.use_rag,
        help="使用历史报告和新闻增强回答质量"
    )
    st.session_state.use_rag = use_rag
    
    # 量化分析开关
    if 'use_quant' not in st.session_state:
        st.session_state.use_quant = True
    
    use_quant = st.checkbox(
        "启用量化分析 (Quant) ⚡",
        value=st.session_state.use_quant,
        help="集成技术指标、风险分析和ML预测"
    )
    st.session_state.use_quant = use_quant
    
    # 任务类型选择
    task_type_map = {
        "问答": TaskType.QA,
        "市场分析": TaskType.ANALYSIS,
        "新闻摘要": TaskType.SUMMARIZATION,
        "预测分析": TaskType.PREDICTION
    }
    
    task_type_name = st.selectbox(
        "分析类型",
        list(task_type_map.keys()),
        index=0
    )
    
    task_type = task_type_map[task_type_name]
    
    # 显示统计
    st.markdown("---")
    st.subheader("📊 使用统计")
    
    stats = llm.get_stats()
    
    st.metric("总请求数", stats['total_requests'])
    st.metric("总成本", f"${stats['total_cost']:.2f}")
    
    if stats['total_requests'] > 0:
        st.metric("缓存命中率", f"{stats['cache_hit_rate']:.1%}")
    
    # RAG统计
    if st.session_state.use_rag:
        rag_stats = rag.get_stats()
        if rag_stats.get('enabled'):
            st.markdown("**RAG向量库:**")
            st.text(f"报告: {rag_stats.get('reports_count', 0)}")
            st.text(f"新闻: {rag_stats.get('news_count', 0)}")
    
    # 清空对话按钮
    if st.button("🗑️ 清空对话历史"):
        st.session_state.messages = []
        st.rerun()

# 主要内容区域
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 对话")
    
    # 显示对话历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # 显示元数据
            if message["role"] == "assistant" and "metadata" in message:
                with st.expander("详细信息"):
                    metadata = message["metadata"]
                    st.text(f"模型: {metadata.get('model', 'N/A')}")
                    st.text(f"提供商: {metadata.get('provider', 'N/A')}")
                    st.text(f"Token: {metadata.get('tokens', 'N/A')}")
                    st.text(f"成本: ${metadata.get('cost', 0):.4f}")
                    st.text(f"延迟: {metadata.get('latency', 0):.2f}s")
                    st.text(f"缓存: {'是' if metadata.get('cached') else '否'}")
    
    # 聊天输入
    if prompt := st.chat_input("输入您的问题..."):
        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 生成回复
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                # 构建请求
                enhanced_prompt = prompt
                context_parts = []
                
                # 如果启用量化分析，添加技术指标上下文
                if st.session_state.use_quant:
                    # 检测是否提到特定标的
                    symbol = 'GLD'
                    if 'SLV' in prompt.upper() or '白银' in prompt:
                        symbol = 'SLV'
                    elif 'GDX' in prompt.upper() or '矿业' in prompt:
                        symbol = 'GDX'
                    
                    quant_context = generate_quant_context(symbol)
                    context_parts.append(quant_context)
                
                # 如果启用RAG，添加历史上下文
                if st.session_state.use_rag and rag.enabled:
                    rag_context = rag.build_context(prompt, max_reports=2, max_news=3)
                    if rag_context:
                        context_parts.append(f"【历史资讯】\n{rag_context}")
                
                # 合并所有上下文
                if context_parts:
                    combined_context = "\n\n".join(context_parts)
                    enhanced_prompt = f"""参考以下信息：

{combined_context}

用户问题：{prompt}

请基于以上信息提供专业分析，结合技术指标和市场背景给出见解。"""
                
                # 创建LLM请求
                request = LLMRequest(
                    task_type=task_type,
                    prompt=enhanced_prompt,
                    system_prompt="你是一位资深的贵金属市场分析师，精通黄金、白银等贵金属市场。请用专业、准确、简洁的中文回答问题。"
                )
                
                # 调用LLM
                response = llm.complete(request)
                
                if response:
                    st.markdown(response.content)
                    
                    # 保存助手回复
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.content,
                        "metadata": {
                            "model": response.model,
                            "provider": response.provider.value,
                            "tokens": response.tokens_used,
                            "cost": response.cost,
                            "latency": response.latency,
                            "cached": response.cached
                        }
                    })
                else:
                    st.error("抱歉，生成回复时出现错误")

with col2:
    st.subheader("💡 快速提问")
    
    # 预设问题
    quick_questions = [
        "当前黄金价格走势如何？",
        "影响金价的主要因素有哪些？",
        "GLD和实物黄金有什么区别？",
        "白银的工业需求如何？",
        "美联储政策对贵金属的影响？",
        "现在适合投资黄金吗？",
        "贵金属矿业股有投资价值吗？",
        "如何应对金价波动风险？"
    ]
    
    for question in quick_questions:
        if st.button(question, key=question, use_container_width=True):
            # 模拟输入
            st.session_state.messages.append({"role": "user", "content": question})
            st.rerun()
    
    st.markdown("---")
    
    # 分析工具
    st.subheader("🔧 分析工具")
    
    # 新闻摘要
    with st.expander("📰 新闻摘要"):
        news_text = st.text_area(
            "粘贴新闻文本",
            height=100,
            placeholder="粘贴需要摘要的新闻内容..."
        )
        
        if st.button("生成摘要"):
            if news_text:
                with st.spinner("生成中..."):
                    summary = llm.summarize(news_text, max_length=200)
                    if summary:
                        st.success("摘要生成完成：")
                        st.write(summary)
            else:
                st.warning("请输入新闻文本")
    
    # 数据分析
    with st.expander("📊 数据分析"):
        st.markdown("输入市场数据进行分析")
        
        gold_price = st.number_input("黄金价格", value=2050.0, step=10.0)
        change = st.number_input("24h涨跌%", value=0.5, step=0.1)
        
        if st.button("分析数据"):
            data = {
                "gold_price": gold_price,
                "change_24h": change,
                "timestamp": datetime.now().isoformat()
            }
            
            with st.spinner("分析中..."):
                analysis = llm.analyze(data, analysis_type="market")
                if analysis:
                    st.success("分析结果：")
                    st.write(analysis)

# 页脚
st.markdown("---")
st.caption("""
💡 提示：
- 启用RAG可以利用历史报告和新闻提供更准确的答案
- 选择合适的分析类型以获得最佳结果
- 使用快速提问获取常见问题的答案
""")
