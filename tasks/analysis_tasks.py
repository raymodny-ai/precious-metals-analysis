"""
分析异步任务
"""
from celery_app import celery_app
from celery.utils.log import get_task_logger
from datetime import datetime

# 导入分析服务
from AnalysisEngine.LLMService.llm_service import get_llm_service
from AnalysisEngine.LLMService.base import LLMRequest, TaskType
from AnalysisEngine.LLMService.rag_system import get_rag_system

logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def analyze_market_sentiment(self, text: str, source: str):
    """分析市场情绪"""
    try:
        llm = get_llm_service()
        
        prompt = f"分析以下来自 {source} 的文本的情绪（积极/消极/中性）和关键观点：\n\n{text}"
        
        request = LLMRequest(
            task_type=TaskType.SENTIMENT,
            prompt=prompt
        )
        
        response = llm.complete(request)
        
        if response:
            return {
                "status": "success",
                "sentiment_analysis": response.content,
                "cost": response.cost
            }
        return {"status": "failed", "error": "No response"}
        
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        raise self.retry(exc=e, countdown=60)

@celery_app.task(bind=True)
def daily_market_analysis(self):
    """每日市场深度分析"""
    try:
        logger.info("Starting daily market analysis")
        
        llm = get_llm_service()
        rag = get_rag_system()
        
        # 1. 构建上下文
        context = rag.build_context("market trends gold silver stocks", max_reports=5, max_news=10)
        
        # 2. 生成分析
        prompt = f"""基于以下最新的市场数据和新闻，生成一份详细的每日贵金属市场分析报告：

{context}

报告应包含：
1. 市场概览
2. 主要驱动因素
3. 风险评估
4. 短期预测
"""
        
        request = LLMRequest(
            task_type=TaskType.ANALYSIS,
            prompt=prompt,
            system_prompt="你是首席市场分析师"
        )
        
        response = llm.complete(request)
        
        if response:
            # 3. 保存报告
            report_id = f"daily_analysis_{datetime.now().strftime('%Y%m%d')}"
            rag.add_report(
                report_id=report_id,
                content=response.content,
                metadata={'type': 'daily_analysis', 'date': datetime.now().isoformat()}
            )
            
            logger.info(f"Daily analysis completed: {report_id}")
            return {"status": "success", "report_id": report_id}
            
        return {"status": "failed"}
        
    except Exception as e:
        logger.error(f"Error in daily analysis: {e}")
        raise self.retry(exc=e, countdown=300)
