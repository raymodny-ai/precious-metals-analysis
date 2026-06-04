"""
通知异步任务
"""
from celery_app import celery_app
from celery.utils.log import get_task_logger

# 导入预警管理器
from NotificationSystem.stock_alert_manager import StockAlertManager

logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def check_stock_alerts(self):
    """检查股票预警规则"""
    try:
        logger.info("Checking stock alerts")
        manager = StockAlertManager()
        
        # 加载规则（这里假设规则已配置或从数据库加载）
        # manager.load_rules_from_db() 
        # 为了演示，我们添加一些默认规则
        from NotificationSystem.stock_alert_manager import PriceBreakoutRule, PercentChangeRule
        
        # 如果没有规则，添加一些默认的
        if not manager.rules:
            manager.add_rule(PercentChangeRule('default_gld_move', 'GLD', 2.0))
            manager.add_rule(PercentChangeRule('default_slv_move', 'SLV', 3.0))
        
        # 检查规则
        alerts = manager.check_all_rules()
        
        if alerts:
            logger.info(f"Triggered {len(alerts)} alerts")
            # 发送通知的任务已在manager内部处理，或者可以在这里单独调用发送任务
            
        return {"status": "success", "alerts_triggered": len(alerts)}
        
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")
        # 不重试，因为这是定时任务，下次会再运行
        return {"status": "error", "message": str(e)}

@celery_app.task
def send_email_notification(recipient: str, subject: str, body: str):
    """发送邮件通知（异步）"""
    try:
        # 这里调用实际的邮件发送逻辑
        # email_service.send(...)
        logger.info(f"Sending email to {recipient}: {subject}")
        return {"status": "sent"}
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return {"status": "failed"}
