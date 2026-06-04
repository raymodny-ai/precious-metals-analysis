from typing import Dict, List

class QAPromptBuilder:
    """问答Prompt构建器"""
    
    @staticmethod
    def build_contextual_qa(
        question: str,
        context_data: Dict,
        chat_history: List[Dict] = None
    ) -> Dict[str, str]:
        """
        构建上下文增强问答Prompt
        
        特点:
        1. 注入实时数据
        2. 保留对话历史
        3. 引导式推理
        """
        
        system_prompt = """你是贵金属投资助手,基于实时数据和历史信息回答用户问题。

**回答原则:**
1. 数据支撑 - 引用具体数字和来源
2. 简洁清晰 - 避免冗长和术语堆砌
3. 中立客观 - 不做过度乐观或悲观的判断
4. 风险提示 - 明确市场存在的不确定性

**输出格式:**
直接回答问题,分段组织:
- 核心答案 (1-2句话)
- 详细解释 (引用数据)
- 补充信息 (如有必要)
- 风险提示 (如有必要)
"""
        
        # 构建上下文信息
        context_str = f"""
**当前市场数据:**
- 黄金价格: ${context_data.get('gold_price', 'N/A')} ({context_data.get('gold_change', 'N/A')}%)
- 白银价格: ${context_data.get('silver_price', 'N/A')} ({context_data.get('silver_change', 'N/A')}%)
- 美元指数: {context_data.get('dxy', 'N/A')}
- 10年期美债收益率: {context_data.get('us10y', 'N/A')}%
"""
        
        # 添加对话历史
        history_str = ""
        if chat_history:
            history_str = "\n**对话历史:**\n"
            for turn in chat_history[-3:]:  # 最近3轮对话
                history_str += f"用户: {turn.get('question', '')}\n助手: {turn.get('answer', '')[:100]}...\n\n"
        
        user_prompt = f"""
{context_str}
{history_str}

**用户问题:**
{question}

请基于以上数据回答问题。
"""
        
        return {"system": system_prompt, "user": user_prompt}
