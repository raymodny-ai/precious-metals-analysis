# 市场分析提示词模板

market_analysis_template = """你是一位资深的贵金属市场分析师。基于以下市场数据，提供专业的市场分析：

## 价格数据
- 黄金价格：${gold_price}，24小时涨跌：{gold_change}%
- 白银价格：${silver_price}，24小时涨跌：{silver_change}%

## 技术指标
- RSI：{rsi}
- MACD：{macd}
- 布林带位置：{bb_position}

## 市场情绪
- 新闻情绪：{news_sentiment}
- 社交媒体情绪：{social_sentiment}

## 宏观数据
- 美元指数：{dxy}
- 10年期国债收益率：{yield_10y}%
- VIX指数：{vix}

请提供：
1. 简要市场概况（50字内）
2. 技术分析解读
3. 情绪分析
4. 短期趋势预测（1-3天）
5. 关键价位和建议

分析（使用中文）："""

# 新闻摘要模板
news_summary_template = """请阅读以下{count}篇关于贵金属市场的新闻，生成一份综合摘要：

{news_list}

要求：
1. 提取所有新闻的核心观点
2. 识别共同趋势和矛盾观点
3. 突出关键事件和数据
4. 不超过300字

摘要："""

# 风险评估模板
risk_assessment_template = """作为风险管理专家，评估当前贵金属投资的风险：

## 当前持仓（假设）
- 黄金ETF (GLD): {gld_position}股
- 白银ETF (SLV): {slv_position}股
- 矿业股: {mining_stocks}

## 市场状况
- 黄金价格：${gold_price}
- 技术指标：RSI {rsi}, MACD {macd}
- 市场情绪：{sentiment}
- 波动率：{volatility}

## 近期事件
{recent_events}

请提供：
1. 风险等级（低/中/高）
2. 主要风险因素（3-5项）
3. 对冲建议
4. 建议仓位调整

风险评估："""

# 交易信号模板
trading_signals_template = """基于以下技术和基本面数据，生成交易信号：

## 技术指标
- RSI: {rsi}（超买线70，超卖线30）
- MACD: {macd}，信号线: {signal}
- 布林带: 价格{bb_position}
- 移动平均: MA20 ${ma20}, MA50 ${ma50}

## 基本面
- 美联储政策：{fed_policy}
- 通胀预期：{inflation}
- 黄金ETF流入流出：{etf_flow}

## 历史相似场景
{similar_scenarios}

请生成：
1. 交易信号（强烈买入/买入/观望/卖出/强烈卖出）
2. 信号强度（1-10分）
3. 入场点位
4. 止损点位
5. 止盈点位
6. 持有期建议

信号："""

# 股票-贵金属关联分析模板
correlation_analysis_template = """分析以下股票与贵金属价格的关联关系：

## 股票信息
- 股票代码：{symbol}
- 公司名称：{company_name}
- 行业：{sector}
- 当前价格：${current_price}

## 相关性数据
- 与GLD相关系数：{gld_correlation}
- 与SLV相关系数：{slv_correlation}
- 30天 Beta：{beta_30d}
- 90天 Beta：{beta_90d}

## 价格走势对比
- 股票30天涨跌：{stock_change_30d}%
- GLD30天涨跌：{gold_change_30d}%
- 背离程度：{divergence}%

请分析：
1. 相关性解读（为什么会有这样的相关性？）
2. 当前背离是否正常
3. 是否存在套利机会
4. 基于相关性的交易建议

分析："""

# 预测验证模板
prediction_verification_template = """验证之前的预测准确性：

## 预测（{prediction_date}作出）
{original_prediction}

## 实际结果（当前{current_date}）
- 实际价格：${actual_price}
- 预测价格：${predicted_price}
- 误差：{error_percent}%
- 趋势方向：{direction_correct}

请分析：
1. 预测准确性评分（0-100）
2. 预测失误的原因
3. 未预见的因素
4. 模型改进建议

验证报告："""
