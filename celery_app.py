"""
Celery配置和应用实例
用于处理异步任务（数据采集、分析、通知）
"""
from celery import Celery
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取Redis URL
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# 初始化Celery应用
celery_app = Celery(
    'PreciousInsight',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'tasks.data_collection_tasks',
        'tasks.analysis_tasks',
        'tasks.notification_tasks'
    ]
)

# 配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # 任务路由
    task_routes={
        'tasks.data_collection_tasks.*': {'queue': 'data_collection'},
        'tasks.analysis_tasks.*': {'queue': 'analysis'},
        'tasks.notification_tasks.*': {'queue': 'notifications'},
    },
    # 定时任务配置 (Beat)
    beat_schedule={
        'update-stock-prices-every-5-mins': {
            'task': 'tasks.data_collection_tasks.update_stock_prices',
            'schedule': 300.0,  # 5分钟
        },
        'daily-market-analysis': {
            'task': 'tasks.analysis_tasks.daily_market_analysis',
            'schedule': 86400.0, # 24小时 (实际应配置crontab)
        },
        'check-alerts-every-minute': {
            'task': 'tasks.notification_tasks.check_stock_alerts',
            'schedule': 60.0,   # 1分钟
        },
    }
)

if __name__ == '__main__':
    celery_app.start()
