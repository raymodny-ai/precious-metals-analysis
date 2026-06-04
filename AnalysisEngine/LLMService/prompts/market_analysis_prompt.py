from typing import Dict, List
from datetime import datetime

class MarketAnalysisPromptBuilder:
    """市场分析Prompt构建器"""
    
    @staticmethod
    def build_comprehensive_analysis(
        price_data: Dict,
        news_summary: str,
        technical_indicators: Dict,
        historical_context: List[str] = None
    ) -> Dict[str, str]:
        """
        构建综合市场分析Prompt
        
        使用技巧:
        1. 结构化输出 - 明确要求JSON格式
        2. 思维链 - 要求分步骤思考
        3. Few-Shot示例 - 提供标准答案范例
        4. 上下文增强 - 注入历史数据和实时指标
        """
        
        # 系统Prompt - 定义角色和规则
        system_prompt = """你是资深贵金属市场分析师,拥有20年从业经验。

**核心能力:**
- 宏观经济政策解读 (美联储、央行政策)
- 技术面分析 (K线形态、支撑阻力位)
- 基本面研判 (供需关系、地缘政治)
- 量化指标运用 (RSI、MACD、布林带)

**分析原则:**
1. 数据驱动 - 基于实际数据而非主观臆测
2. 多维视角 - 综合宏观、技术、情绪面
3. 风险提示 - 明确指出不确定性
4. 可操作性 - 提供明确的交易建议区间

**输出格式要求:**
严格按照JSON格式输出,包含以下字段:
{
  "market_overview": "市场概况(100字以内)",
  "key_drivers": ["驱动因素1", "驱动因素2", "驱动因素3"],
  "technical_analysis": {
    "trend": "上涨/下跌/震荡",
    "support_level": 支撑位价格(数字),
    "resistance_level": 阻力位价格(数字),
    "signal_strength": "强/中/弱"
  },
  "fundamental_factors": ["基本面因素1", "基本面因素2"],
  "sentiment_score": 0-100情绪分数(数字),
  "trading_recommendation": {
    "action": "买入/持有/卖出",
    "entry_range": [最低价, 最高价],
    "stop_loss": 止损价(数字),
    "target_price": 目标价(数字),
    "confidence": "高/中/低"
  },
  "risk_warnings": ["风险提示1", "风险提示2"],
  "outlook": "未来1-2周展望(50字)"
}
"""
        
        # 构建Few-Shot示例
        few_shot_examples = """
**示例分析案例:**

输入数据:
- 黄金价格: $1950/盎司 (+1.2%)
- RSI: 68 (接近超买)
- 近期新闻: 美联储维持利率不变
- 美元指数: 103.5 (-0.3%)

输出JSON:
```json
{
"market_overview": "黄金在美联储鸽派信号刺激下突破1950阻力位,但RSI接近超买区域,短期存在回调压力。",
"key_drivers": [
"美联储暂停加息预期强化",
"美元指数走弱提供支撑",
"地缘政治不确定性上升"
],
"technical_analysis": {
"trend": "上涨",
"support_level": 1935,
"resistance_level": 1970,
"signal_strength": "中"
},
"fundamental_factors": [
"实际利率下行利好黄金",
"全球央行持续购金"
],
"sentiment_score": 72,
"trading_recommendation": {
"action": "持有",
"entry_range": [1935, 1945],
"stop_loss": 1920,
"target_price": 1985,
"confidence": "中"
},
"risk_warnings": [
"若美联储转鹰派,金价可能快速回落",
"技术面短期超买,注意回调风险"
],
"outlook": "短期震荡整固,突破1970后有望挑战2000关口"
}
```
"""
        
        # 构建当前分析任务的用户Prompt
        user_prompt = f"""
请基于以下实时数据进行贵金属市场综合分析:

**1. 价格数据 (截至 {datetime.now().strftime('%Y-%m-%d %H:%M')})**
```
{price_data}
```

**2. 技术指标**
```
{technical_indicators}
```

**3. 最新新闻摘要**
{news_summary}

**4. 历史上下文 (相似市场环境参考)**
"""
        
        # 添加历史上下文 (RAG检索结果)
        if historical_context:
            for i, context in enumerate(historical_context[:3], 1):
                user_prompt += f"\n[参考{i}] {context}\n"
        
        user_prompt += """

**分析要求:**
请按照以下步骤进行思考 (Chain-of-Thought):

**Step 1: 数据解读**
- 价格变动幅度是否显著?
- 技术指标传递什么信号?
- 新闻事件的影响方向?

**Step 2: 多维度分析**
- 宏观面: 货币政策、经济数据
- 技术面: 趋势、支撑阻力
- 情绪面: 市场热度、资金流向

**Step 3: 综合研判**
- 多空力量对比
- 关键价格区间
- 潜在风险因素

**Step 4: 交易建议**
- 操作方向和理由
- 具体价格区间
- 风险控制措施

请严格按照JSON格式输出最终分析结果。不要输出思考过程，只输出JSON。
"""
        
        return {
            "system": system_prompt,
            "user": user_prompt,
            "examples": few_shot_examples
        }
