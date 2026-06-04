from typing import List, Dict

class NewsSummaryPromptBuilder:
    """新闻摘要Prompt构建器"""
    
    @staticmethod
    def build_focused_summary(
        news_articles: List[Dict],
        focus_topics: List[str] = None
    ) -> Dict[str, str]:
        """
        构建聚焦式新闻摘要Prompt
        
        特点:
        1. 多文档压缩
        2. 关键信息提取
        3. 影响度评估
        """
        
        system_prompt = """你是专业的金融新闻分析师,擅长从大量新闻中提取关键信息。

**任务目标:**
从多篇贵金属相关新闻中提炼核心要点,评估对市场的影响。

**输出格式:**
```json
{
"executive_summary": "一句话总结(30字以内)",
"key_events": [
{
"event": "事件描述",
"impact": "正面/负面/中性",
"urgency": "高/中/低",
"affected_assets": ["GLD", "SLV"]
}
],
"market_sentiment": "乐观/谨慎/悲观",
"action_items": ["投资者应关注的事项1", "事项2"]
}
```
"""
        
        # 构建新闻内容
        news_content = ""
        for i, article in enumerate(news_articles[:10], 1):  # 限制10篇
            news_content += f"""
[新闻{i}] {article.get('title', '无标题')}
来源: {article.get('source', '未知')} | 时间: {article.get('published_at', '未知')}
内容: {article.get('content', '')[:300]}...
---
"""
        
        user_prompt = f"""
请分析以下贵金属相关新闻,提取关键信息:

{news_content}

**分析要点:**
1. 识别重大事件 (央行政策、地缘冲突、经济数据等)
2. 评估每个事件对金价/银价的影响方向
3. 判断事件的紧急程度和市场关注度
4. 提供可操作的建议

请严格按JSON格式输出。
"""
        
        return {"system": system_prompt, "user": user_prompt}
